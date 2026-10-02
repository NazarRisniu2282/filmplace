from celery import shared_task
import time

@shared_task
def send_email_task(user_email, message):
    print(f"Лист для {user_email} успішно надіслано: {message}")
    return True