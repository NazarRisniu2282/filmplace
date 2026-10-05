from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Booking, CustomUser, Hall, Movie, Showtime


@admin.register(CustomUser)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "phone_number")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "phone_number")
    ordering = ("id",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (_("Додаткова інформація"), {"fields": ("phone_number", "birthdate")}),
    )


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "duration", "rate", "rating")
    list_filter = ("rate",)
    search_fields = ("title", "description")
    ordering = ("title",)


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "rows", "seats_per_row", "total_seats")
    search_fields = ("name",)

    @admin.display(description="Всього місць")
    def total_seats(self, obj):
        return obj.rows * obj.seats_per_row


@admin.register(Showtime)
class ShowtimeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "movie",
        "hall",
        "start_time",
        "price",
        "is_expired_status",
    )
    list_filter = ("hall", "start_time", "movie")
    search_fields = ("movie__title", "hall__name")
    date_hierarchy = "start_time"
    ordering = ("-start_time",)

    @admin.display(description="Статус", boolean=True)
    def is_expired_status(self, obj):
        return not obj.is_expired


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "get_movie_title",
        "get_hall_name",
        "row",
        "place",
        "is_used",
        "created_at",
    )
    list_filter = ("is_used", "showtime__hall", "showtime__movie", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "showtime__movie__title",
        "showtime__hall__name",
    )
    readonly_fields = ("created_at", "used_at")
    ordering = ("-created_at",)

    @admin.display(description="Фільм", ordering="showtime__movie__title")
    def get_movie_title(self, obj):
        return obj.showtime.movie.title

    @admin.display(description="Зал", ordering="showtime__hall__name")
    def get_hall_name(self, obj):
        return obj.showtime.hall.name