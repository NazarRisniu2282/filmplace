from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response

from .models import Booking, Movie, Showtime, Hall
from .serializer import (
    BookingCreateSerializer,
    BookingSerializer,
    MovieSerializer,
    RegisterSerializer,
    ShowtimeSerializer,
    User,
    HallSerializer,
)
from .services import send_booking_confirmation_email
from .telegram import send_telegram_notification


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class ShowtimeViewSet(viewsets.ModelViewSet):
    """
    ViewSet для перегляду та управління сеансами.
    Підтримує фільтрацію за параметром `?active=true` або `?movie_id=X`.
    """

    queryset = Showtime.objects.select_related("movie").all()
    serializer_class = ShowtimeSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = super().get_queryset()
        movie_id = self.request.query_params.get("movie")
        is_active = self.request.query_params.get("active")

        if movie_id:
            queryset = queryset.filter(movie_id=movie_id)


        if is_active and is_active.lower() == "true":
            queryset = queryset.filter(end_time__gt=timezone.now())

        return queryset


class MyTicketsListView(generics.ListAPIView):
    """
    Список усіх квитків поточного авторизованого користувача.
    """

    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Booking.objects.filter(user=self.request.user)
            .select_related("showtime__movie", "user")
            .order_by("-created_at")
        )


class CreateBookingView(generics.CreateAPIView):
    """
    Створення нового бронювання місць на сеанс.
    """

    serializer_class = BookingCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        bookings = serializer.save()

        try:
            send_telegram_notification(bookings)
            send_booking_confirmation_email(bookings)
        except Exception as e:
            print(f"Помилка відправки сповіщень: {e}")

        response_data = BookingSerializer(bookings, many=True).data
        return Response(response_data, status=status.HTTP_201_CREATED)


class HallViewSet(viewsets.ModelViewSet):
    queryset = Hall.objects.all()
    serializer_class = HallSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]