from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


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
    description = models.TextField(max_length=1000)
    duration = models.PositiveIntegerField(
        help_text="Тривалість у хвилинах"
    )
    rate = models.CharField(max_length=3, choices=AgeRating.choices)
    rating = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)]
    )

    def __str__(self):
        return self.title


class Hall(models.Model):
    name = models.CharField(max_length=50, verbose_name="Назва залу")  # Наприклад: "Зал 1", "IMAX"
    rows = models.PositiveIntegerField(verbose_name="Кількість рядів")
    seats_per_row = models.PositiveIntegerField(verbose_name="Місць у ряду")

    class Meta:
        verbose_name = "Кінозал"
        verbose_name_plural = "Кінозали"

    def __str__(self):
        return f"{self.name} ({self.rows}р x {self.seats_per_row}м)"


class Showtime(models.Model):
    movie = models.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="showtimes"
    )
    hall = models.ForeignKey(
        Hall, on_delete=models.CASCADE, related_name="showtimes", verbose_name="Зал"
    )
    start_time = models.DateTimeField(verbose_name="Початок сеансу")
    end_time = models.DateTimeField(
        verbose_name="Кінець сеансу", blank=True, null=True
    )
    price = models.DecimalField(
        max_digits=8, decimal_places=2, verbose_name="Ціна квитка"
    )

    class Meta:
        ordering = ["start_time"]
        verbose_name = "Сеанс"
        verbose_name_plural = "Сеанси"

    def clean(self):
        if self.end_time and self.end_time <= self.start_time:
            raise ValidationError("Час завершення має бути пізніше часу початку.")

    def save(self, *args, **kwargs):
        if not self.end_time and self.movie and self.movie.duration:
            self.end_time = self.start_time + timedelta(minutes=self.movie.duration)
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.end_time

    @property
    def is_active(self) -> bool:
        now = timezone.now()
        return self.start_time <= now < self.end_time
    
    @property
    def total_seats(self) -> int:
        """Загальна кількість місць у залі."""
        return self.hall.rows * self.hall.seats_per_row

    @property
    def booked_seats_count(self) -> int:
        """Кількість уже заброньованих місць."""
        return self.bookings.count()

    @property
    def free_seats_count(self) -> int:
        """Кількість доступних (вільних) місць."""
        return self.total_seats - self.booked_seats_count

    def get_free_seats(self):
        """Повертає список доступних місць у форматі [{'row': 1, 'place': 1}, ...]"""
        occupied_seats = set(
            self.bookings.values_list("row", "place")
        )

        free_seats = []
        for r in range(1, self.hall.rows + 1):
            for p in range(1, self.hall.seats_per_row + 1):
                if (r, p) not in occupied_seats:
                    free_seats.append({"row": r, "place": p})

        return free_seats

    def __str__(self):
        return f"{self.movie.title} | {self.hall.name} ({self.start_time.strftime('%d.%m %H:%M')})"


class Booking(models.Model):
    showtime = models.ForeignKey(
        Showtime, on_delete=models.CASCADE, related_name="bookings"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings"
    )
    row = models.PositiveIntegerField()
    place = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="Дійсне до")
    is_used = models.BooleanField( default=False, verbose_name="used")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="Час сканування")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Бронювання"
        verbose_name_plural = "Бронювання"
        constraints = [
            models.UniqueConstraint(
                fields=["showtime", "row", "place"],
                name="unique_booking_per_seat_and_showtime",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return self.status == self.BookingStatus.PENDING and timezone.now() > self.expires_at
    

    @property
    def status(self) -> str:
        now = timezone.now()
        if now < self.showtime.start_time:
            return "Upcoming"
        elif self.showtime.start_time <= now < self.showtime.end_time:
            return "In Progress"
        return "Expired"

    def __str__(self):
        return f"{self.user} | {self.showtime.movie.title} | Ряд {self.row}, Місце {self.place} [{self.status}]"