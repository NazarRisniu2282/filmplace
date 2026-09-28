from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Movie, Booking


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Розширюємо стандартний UserAdmin для підтримки наших нових полів.
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'is_staff')
    
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Додаткова інформація', {
            'fields': ('phone_number', 'birthdate'),
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Додаткова інформація', {
            'fields': ('phone_number', 'birthdate'),
        }),
    )


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    """
    Налаштування відображення фільмів.
    """
    list_display = ('title', 'rate', 'duration', 'rating', 'price')
    
    list_filter = ('rate',)
    
    search_fields = ('title', 'description')
    
    ordering = ('title',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """
    Налаштування відображення бронювань.
    """
    list_display = ('movie', 'user', 'showtime', 'row', 'place', 'created_at')
    
    list_filter = ('movie', 'showtime', 'created_at')
    
    search_fields = ('movie__title', 'user__username', 'user__email')
    
    date_hierarchy = 'showtime'
    
    raw_id_fields = ('user', 'movie')
