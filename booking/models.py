from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CustomUser(AbstractUser):
    phone_number = models.CharField(
        max_length=20, blank=True, verbose_name="Номер телефону"
    )
    birthdate = models.DateField(
        null=True, blank=True, verbose_name="Дата народження"
    )

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username


class Movie(models.Model):
    class AgeRating(models.TextChoices):
        G = "0+", "0+"
        PG12 = "12+", "12+"
        PG16 = "16+", "16+"
        R18 = "18+", "18+"

    title = models.CharField(max_length=100)
    description = models.CharField(max_length=300)
    duration = models.PositiveIntegerField(
        help_text="Тривалість у хвилинах"
    )
    rate = models.CharField(max_length=3, choices=AgeRating.choices)
    rating = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)]
    )
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return self.title


class Booking(models.Model):
    # Твої існуючі поля
    movie = models.ForeignKey('Movie', on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    showtime = models.DateTimeField()
    row = models.PositiveIntegerField()
    place = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['movie', 'showtime', 'row', 'place'],
                name='unique_booking_per_seat_and_showtime'
            )
        ]

    def __str__(self):
        return f"{self.movie.title} | {self.showtime} | Ряд {self.row}, Місце {self.place}"