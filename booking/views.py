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
from rest_framework.decorators import action


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
    queryset = Showtime.objects.select_related("movie", "hall").all()
    serializer_class = ShowtimeSerializer

    @action(detail=True, methods=["get"], url_path="free-seats")
    def free_seats(self, request, pk=None):
        showtime = self.get_object()
        
        if showtime.is_expired:
            return Response(
                {"detail": "Сеанс вже минув."},
                status=status.HTTP_400_BAD_REQUEST
            )

        free_seats = showtime.get_free_seats()

        return Response({
            "showtime_id": showtime.id,
            "free_seats_count": len(free_seats),
            "free_seats": free_seats
        }, status=status.HTTP_200_OK)


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