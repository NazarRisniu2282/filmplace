from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, APITestCase
from django.urls import NoReverseMatch, reverse

from .models import Booking, Hall, Movie, Showtime
from .serializer import BookingCreateSerializer
from .services import send_booking_confirmation_email
from .tasks import send_email_task
from .telegram import send_telegram_notification

User = get_user_model()


class CeleryTaskUnitTests(TestCase):
    """Перевірка асинхронного виклику таски (без виконання самої логики)."""

    @patch("booking.tasks.send_email_task.delay")
    def test_send_email_task_called_async(self, mock_send_email):
        # Викликаємо таску через .delay()
        send_email_task.delay("test@example.com", "Тестове повідомлення")

        # Перевіряємо, що метод .delay() був викликаний один раз з правильними аргументами
        mock_send_email.assert_called_once_with(
            "test@example.com", "Тестове повідомлення"
        )


class CeleryTaskExecutionTests(TestCase):
    """Перевірка реального виконання таски у синхронному режимі для тестів."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_send_email_task_execution(self):
        # При CELERY_TASK_ALWAYS_EAGER=True таска виконується одразу в тілі тесту
        result = send_email_task.delay("test@example.com", "Привіт з тесту!")

        # Перевіряємо статус та результат повернення
        self.assertTrue(result.successful())
        self.assertEqual(result.result, True)


class NotificationServicesTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="Password123!"
        )
        self.movie = Movie.objects.create(
            title="Інтерстеллар", duration=169, rate="12+", rating=8.6
        )
        # 1. Створюємо зал
        self.hall = Hall.objects.create(name="Red Hall", rows=10, seats_per_row=15)
        # 2. Передаємо hall у Showtime
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            hall=self.hall,
            start_time=timezone.now() + timedelta(days=1),
            price=150.00,
        )
        # Створення двох заброньованих квитків
        self.booking1 = Booking.objects.create(
            user=self.user, showtime=self.showtime, row=1, place=5
        )
        self.booking2 = Booking.objects.create(
            user=self.user, showtime=self.showtime, row=1, place=6
        )
        self.bookings = [self.booking1, self.booking2]

    # --- ТЕСТИ EMAIL СПОВІЩЕНЬ ---

    def test_send_booking_confirmation_email_success(self):
        """Перевірка успішного формування та відправки Email."""
        send_booking_confirmation_email(self.bookings)

        # Перевіряємо, що в outbox з'явився 1 лист
        self.assertEqual(len(mail.outbox), 1)

        sent_email = mail.outbox[0]
        self.assertIn("Підтвердження бронювання — Інтерстеллар", sent_email.subject)
        self.assertEqual(sent_email.to, ["testuser@example.com"])
        self.assertIn("testuser", sent_email.body)
        self.assertIn("• Ряд 1, Місце 5", sent_email.body)
        self.assertIn("• Ряд 1, Місце 6", sent_email.body)

    def test_send_email_no_email_user(self):
        """Перевірка, що лист не відправляється, якщо в користувача немає email."""
        self.user.email = ""
        self.user.save()

        send_booking_confirmation_email(self.bookings)
        self.assertEqual(len(mail.outbox), 0)

    # --- ТЕСТИ TELEGRAM СПОВІЩЕНЬ ---

    @patch("requests.post")
    def test_send_telegram_notification_success(self, mock_post):
        """Перевірка формування та відправки HTTP-запиту в Telegram API."""
        # Мокаємо успішну відповідь від Telegram API (status 200)
        mock_post.return_value.status_code = 200

        with self.settings(TELEGRAM_BOT_TOKEN="test_token", TELEGRAM_CHAT_ID="123456"):
            send_telegram_notification(self.bookings)

            # Перевіряємо, що requests.post викликався 1 раз
            mock_post.assert_called_once()

            # Перевіряємо параметри, з якими був викликаний requests.post
            args, kwargs = mock_post.call_args
            self.assertEqual(
                args[0], "https://api.telegram.org/bottest_token/sendMessage"
            )

            payload = kwargs["json"]
            self.assertEqual(payload["chat_id"], "123456")
            self.assertIn("Інтерстеллар", payload["text"])
            self.assertIn("• Ряд 1, Місце 5", payload["text"])
            self.assertIn("testuser", payload["text"])

    @patch("requests.post")
    def test_send_telegram_notification_missing_credentials(self, mock_post):
        """Перевірка, що запит не надсилається без налаштованих токенів."""
        with self.settings(TELEGRAM_BOT_TOKEN=None, TELEGRAM_CHAT_ID=None):
            send_telegram_notification(self.bookings)
            mock_post.assert_not_called()


class CreateBookingAPIIntegrationTestCase(APITestCase):
    """Інтеграційний тест ендпоінту buy-tickets/ з перевіркою виклику сповіщень."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer", email="buyer@example.com", password="Password123!"
        )
        self.client.force_authenticate(user=self.user)

        self.movie = Movie.objects.create(
            title="Матриця", description="Sci-Fi", duration=136, rate="16+", rating=8.7
        )
        # 1. Створюємо зал
        self.hall = Hall.objects.create(name="IMAX", rows=12, seats_per_row=20)
        # 2. Передаємо hall у Showtime
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            hall=self.hall,
            start_time=timezone.now() + timedelta(days=1),
            price=200.00,
        )

    @patch("booking.views.send_booking_notifications_task.delay")
    def test_create_booking_triggers_notifications(self, mock_task):
        # Отримуємо URL за правильним іменем з urls.py
        try:
            url = reverse("buy-tickets")
        except NoReverseMatch:
            url = reverse("booking:buy-tickets")

        data = {
            "showtime": self.showtime.id,
            "seats": [
                {"row": 1, "place": 1},
            ],
        }

        # Виконуємо запит із виконанням on_commit хуків Celery
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_task.assert_called_once()

    def test_non_admin_cannot_update_showtime(self):
        response = self.client.patch(
            f"/showtimes/{self.showtime.id}/",
            {"price": "250.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.showtime.refresh_from_db()
        self.assertEqual(str(self.showtime.price), "200.00")

    def test_registration_rejects_weak_password(self):
        response = self.client.post(
            "/register/",
            {
                "username": "weak-password-user",
                "email": "weak@example.com",
                "password": "123",
                "password_confirm": "123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertFalse(User.objects.filter(username="weak-password-user").exists())

    def test_booking_rechecks_seats_before_atomic_insert(self):
        request = APIRequestFactory().post("/buy-tickets/")
        request.user = self.user
        serializer = BookingCreateSerializer(
            data={
                "showtime": self.showtime.id,
                "seats": [{"row": 3, "place": 7}],
            },
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            row=3,
            place=7,
        )

        with self.assertRaises(ValidationError):
            serializer.save()

        self.assertEqual(
            Booking.objects.filter(showtime=self.showtime, row=3, place=7).count(),
            1,
        )
