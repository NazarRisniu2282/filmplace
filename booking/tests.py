from datetime import timedelta
from unittest.mock import patch
from django.core import mail
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from .models import Movie, Showtime, Booking, Hall
from .telegram import send_telegram_notification
from .services import send_booking_confirmation_email

User = get_user_model()


class NotificationServicesTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="Password123!"
        )
        self.movie = Movie.objects.create(
            title="Інтерстеллар",
            duration=169,
            rate="12+",
            rating=8.6
        )
        # 1. Створюємо зал
        self.hall = Hall.objects.create(
            name="Red Hall",
            rows=10,
            seats_per_row=15
        )
        # 2. Передаємо hall у Showtime
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            hall=self.hall,
            start_time=timezone.now() + timedelta(days=1),
            price=150.00
        )
        # Створення двох заброньованих квитків
        self.booking1 = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            row=1,
            place=5
        )
        self.booking2 = Booking.objects.create(
            user=self.user,
            showtime=self.showtime,
            row=1,
            place=6
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
            self.assertEqual(args[0], "https://api.telegram.org/bottest_token/sendMessage")
            
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
            username="buyer",
            email="buyer@example.com",
            password="Password123!"
        )
        self.client.force_authenticate(user=self.user)

        self.movie = Movie.objects.create(
            title="Матриця",
            description="Sci-Fi",
            duration=136,
            rate="16+",
            rating=8.7
        )
        # 1. Створюємо зал
        self.hall = Hall.objects.create(
            name="IMAX",
            rows=12,
            seats_per_row=20
        )
        # 2. Передаємо hall у Showtime
        self.showtime = Showtime.objects.create(
            movie=self.movie,
            hall=self.hall,
            start_time=timezone.now() + timedelta(days=1),
            price=200.00
        )

    @patch("booking.views.send_telegram_notification")
    def test_create_booking_triggers_notifications(self, mock_telegram):
        """Перевіряє, що API купівлі квитків створює квитки, надсилає email та викликає telegram."""
        url = "/buy-tickets/"
        data = {
            "showtime": self.showtime.id,
            "seats": [
                {"row": 2, "place": 10},
                {"row": 2, "place": 11}
            ]
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.count(), 2)

        # 1. Перевіряємо, що телеграм-функцію було викликано
        mock_telegram.assert_called_once()

        # 2. Перевіряємо, що лист потрапив у джангівський mail.outbox
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["buyer@example.com"])
        self.assertIn("Матриця", mail.outbox[0].subject)