from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.db import transaction
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from django.http import JsonResponse
from .tasks import send_email_task

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
    queryset = Showtime.objects.select_related("movie", "hall").all()
    serializer_class = ShowtimeSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @action(detail=True, methods=["get"], url_path="free-seats")
    def free_seats(self, request, pk=None):
        showtime = self.get_object()

        if showtime.is_expired:
            return Response(
                {"detail": "Сеанс вже минув."}, status=status.HTTP_400_BAD_REQUEST
            )

        free_seats = showtime.get_free_seats()

        return Response(
            {
                "showtime_id": showtime.id,
                "free_seats_count": len(free_seats),
                "free_seats": free_seats,
            },
            status=status.HTTP_200_OK,
        )


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Запит може робити тільки авторизований контролер
def validate_qr_token(request):
    token = request.data.get('token')
    
    if not token:
        return Response({"status": "ERROR", "message": "Токен не надано"}, status=400)

    signer = TimestampSigner()

    try:
        # 1. Розшифровуємо токен
        data = signer.unsign_object(token, max_age=86400 * 30)
        
        booking_ids = data.get("booking_ids")
        showtime_id = data.get("showtime_id")

        # 2. Атомарна перевірка та блокування рядка в базі
        with transaction.atomic():
            bookings = list(
                Booking.objects.select_for_update()
                .select_related('showtime__movie', 'showtime__hall')
                .filter(id__in=booking_ids, showtime_id=showtime_id)
            )

            if not bookings:
                return Response({
                    "status": "INVALID", 
                    "message": "Квиток не знайдено в системі"
                }, status=404)

            # 3. ПЕРЕВІРКА: Чи був квиток вже використаний?
            already_used = [b for b in bookings if b.is_used]
            if already_used:
                first_used = already_used[0]
                formatted_time = first_used.used_at.strftime("%H:%M:%S") if first_used.used_at else "раніше"
                return Response({
                    "status": "REJECTED!!!!!!!!!!",
                    "message": f"Квиток ВЖЕ ВИКОРИСТАНО о {formatted_time}!"
                }, status=400)

            # 4. ПОГАШЕННЯ: Змінюємо статус на is_used = True і зберігаємо
            now = timezone.now()
            for b in bookings:
                b.is_used = True
                b.used_at = now
                b.save(update_fields=["is_used", "used_at"]) # ЗБЕРІГАЄМО В БД!

            first_b = bookings[0]
            return Response({
                "status": "VALID",
                "message": "ПРОХІД ДОЗВОЛЕНО",
                "movie": first_b.showtime.movie.title,
                "hall": first_b.showtime.hall.name,
                "seats": [f"Ряд {b.row}, Місце {b.place}" for b in bookings]
            }, status=200)

    except SignatureExpired:
        return Response({"status": "EXPIRED", "message": "Термін дії квитка вичерпано"}, status=400)
    except BadSignature:
        return Response({"status": "INVALID", "message": "Підроблений або недійсний QR-код"}, status=400)


def my_view(request):
    # Завдання передається в Celery і виконується у фоні, не затримуючи відповідь користувачу
    send_email_task.delay('user@example.com', 'Ласкаво просимо!')
    
    return JsonResponse({'status': 'Завдання відправлено в обробку!'})