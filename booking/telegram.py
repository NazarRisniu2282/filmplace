import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram_notification(bookings):
    """
    Надсилає сповіщення про нове бронювання групі квитків.
    """
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

    if not bot_token or not chat_id or not bookings:
        return

    first_booking = bookings[0]
    movie_title = first_booking.movie.title
    user = first_booking.user
    showtime_str = first_booking.showtime.strftime("%d.%m.%Y %H:%M")

    user_name = f"{user.first_name} {user.last_name}".strip() or user.username
    user_phone = getattr(user, "phone_number", "Не вказано")

    seats_info = "\n".join([f"• Ряд {b.row}, Місце {b.place}" for b in bookings])

    message = (
        f"🎬 <b>Нове бронювання квитків!</b>\n\n"
        f"🍿 <b>Фільм:</b> {movie_title}\n"
        f"👤 <b>Клієнт:</b> {user_name}\n"
        f"📞 <b>Телефон:</b> {user_phone}\n"
        f"📅 <b>Сеанс:</b> {showtime_str}\n"
        f"🎟️ <b>Кількість:</b> {len(bookings)}\n\n"
        f"📍 <b>Заброньовані місця:</b>\n{seats_info}"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Помилка надсилання у Telegram: {e}")