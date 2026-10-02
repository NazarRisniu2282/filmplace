import io
import qrcode
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.signing import TimestampSigner # Використовуємо криптографічний підпис Django
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_booking_confirmation_email(bookings):
    """
    Надсилає HTML-лист із підтвердженням бронювання та підписаним QR-кодом.
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

    booking_ids = [b.id for b in bookings]
    
    payload = {
        "showtime_id": showtime.id,
        "booking_ids": booking_ids
    }

    signer = TimestampSigner()
    signed_token = signer.sign_object(payload)

    qr_data = signed_token
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_bytes = buffer.getvalue()

    context = {
        'movie_title': movie_title,
        'user_name': user_name,
        'user_phone': user_phone,
        'showtime_str': showtime_str,
        'hall': hall,
        'bookings_count': len(bookings),
        'seats': bookings,
    }

    html_content = render_to_string('emails/booking_confirmation.html', context)
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_content, "text/html")

    mime_image = MIMEImage(qr_bytes)
    mime_image.add_header('Content-ID', '<booking_qr_code>')
    mime_image.add_header('Content-Disposition', 'inline', filename='qr_code.png')
    msg.attach(mime_image)

    msg.send(fail_silently=False)