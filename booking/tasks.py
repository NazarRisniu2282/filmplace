from celery import shared_task
from django.utils import timezone

from .models import Booking
from .services import send_booking_confirmation_email
from .telegram import send_telegram_notification


@shared_task
def send_email_task(user_email, message):
    print(f"Лист для {user_email} успішно надіслано: {message}")
    return True


@shared_task
def send_booking_notifications_task(booking_ids):
    """
    Фонова задача для генерування QR, відправки Email та сповіщення в Telegram.
    """
    bookings = list(
        Booking.objects.select_related(
            "showtime__movie", "showtime__hall", "user"
        ).filter(id__in=booking_ids)
    )

    if not bookings:
        return False

    # 1. Telegram
    try:
        send_telegram_notification(bookings)
    except Exception as e:
        print(f"[Celery] Помилка відправки в Telegram: {e}")

    # 2. Email з QR-кодом
    try:
        send_booking_confirmation_email(bookings)
    except Exception as e:
        print(f"[Celery] Помилка відправки Email: {e}")

    return True


@shared_task
def cleanup_expired_bookings_task():
    """
    Периодична задача для видалення прострочених неоплачених бронювань.
    Видаляє бронювання, які не були використані/оплачені та час expires_at яких минув.
    """
    now = timezone.now()

    # Фільтруємо неоплачені/невикористані бронювання, чий час вичерпано
    # Примітка: адаптуйте прапорці (is_used, status, is_paid тощо) під вашу модель
    expired_bookings = Booking.objects.filter(expires_at__lt=now, is_used=False)

    count, _ = expired_bookings.delete()

    if count > 0:
        print(f"[Celery Beat] Успішно видалено прострочених бронювань: {count}")

    return count
