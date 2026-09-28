# tickets/services.py
from django.core.mail import send_mail
from django.conf import settings

def send_booking_confirmation_email(bookings):
    """
    Надсилає лист із підтвердженням бронювання для списку квитків (bookings).
    """
    if not bookings:
        return

    first_booking = bookings[0]
    user = first_booking.user
    movie_title = first_booking.movie.title
    showtime_str = first_booking.showtime.strftime("%d.%m.%Y %H:%M")

    user_name = f"{user.first_name} {user.last_name}".strip() or user.username
    user_phone = getattr(user, "phone_number", "Не вказано")

    seats_info_plain = "\n".join([f"• Ряд {b.row}, Місце {b.place}" for b in bookings])
    seats_info_html = "<br>".join([f"• Ряд {b.row}, Місце {b.place}" for b in bookings])

    subject = f'Підтвердження бронювання — {movie_title}'

    message = (
        f"Нове бронювання квитків!\n\n"
        f"Фільм: {movie_title}\n"
        f"Клієнт: {user_name}\n"
        f"Телефон: {user_phone}\n"
        f"Сеанс: {showtime_str}\n"
        f"Кількість: {len(bookings)}\n\n"
        f"Заброньовані місця:\n{seats_info_plain}"
    )

    html_message = f"""
    <h2>🎬 Нове бронювання квитків!</h2>
    <p>🍿 <b>Фільм:</b> {movie_title}</p>
    <p>👤 <b>Клієнт:</b> {user_name}</p>
    <p>📞 <b>Телефон:</b> {user_phone}</p>
    <p>📅 <b>Сеанс:</b> {showtime_str}</p>
    <p>🎟️ <b>Кількість:</b> {len(bookings)}</p>
    <p>📍 <b>Заброньовані місця:</b><br>{seats_info_html}</p>
    """

    recipient_list = [user.email]

    if user.email:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )