import io
import qrcode
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_booking_confirmation_email(bookings):
    """
    Надсилає HTML-лист із підтвердженням бронювання та QR-кодом.
    """
    if not bookings:
        return

    first_booking = bookings[0]
    user = first_booking.user
    
    if not user.email:
        return

    showtime = first_booking.showtime
    movie_title = showtime.movie.title
    showtime_str = showtime.start_time.strftime("%d.%m.%Y %H:%M")
    hall = showtime.hall

    user_name = f"{user.first_name} {user.last_name}".strip() or user.username
    user_phone = getattr(user, "phone_number", "Не вказано")

    subject = f"Підтвердження бронювання — {movie_title}"

    # 1. Генерація QR-коду в пам'яті
    # Формуємо дані для сканування (наприклад, ID бронювань або лінк)
    booking_ids = ", ".join([str(b.id) for b in bookings])
    qr_data = f"Booking IDs: {booking_ids} | Film: {movie_title} | User: {user_name}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_bytes = buffer.getvalue()

    # 2. Рендеринг HTML через шаблон
    context = {
        'movie_title': movie_title,
        'user_name': user_name,
        'user_phone': user_phone,
        'showtime_str': showtime_str,
        'hall': hall,
        'bookings_count': len(bookings),
        'seats': bookings,  # передаємо список об'єктів
    }

    html_content = render_to_string('emails/booking_confirmation.html', context)
    text_content = strip_tags(html_content)  # Текстова версія для старих поштових клієнтів

    # 3. Створення та відправка Email
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_content, "text/html")

    # 4. Прикріплення QR-коду як Inline зображення через CID
    mime_image = MIMEImage(qr_bytes)
    mime_image.add_header('Content-ID', '<booking_qr_code>')
    mime_image.add_header('Content-Disposition', 'inline', filename='qr_code.png')
    msg.attach(mime_image)

    # 5. Відправка
    msg.send(fail_silently=False)