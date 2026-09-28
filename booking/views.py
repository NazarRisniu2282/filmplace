from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from .models import Booking, Movie
from .serializer import (
    BookingSerializer,
    BookingCreateSerializer,
    MovieSerializer,
    RegisterSerializer,
    User,
)
from .telegram import send_telegram_notification
from .services import send_booking_confirmation_email


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


class MyTicketsListView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).order_by('-created_at')


class CreateBookingView(generics.CreateAPIView):
    serializer_class = BookingCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bookings = serializer.save()

        send_telegram_notification(bookings)
        send_booking_confirmation_email(bookings)

        response_data = BookingSerializer(bookings, many=True).data
        return Response(response_data, status=status.HTTP_201_CREATED)