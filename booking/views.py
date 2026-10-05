from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from .telegram import send_telegram_notification

from .models import Booking, Hall, Movie, Showtime, CustomUser
from .serializer import (
    BookingCreateSerializer,
    BookingSerializer,
    HallSerializer,
    MovieSerializer,
    RegisterSerializer,
    ShowtimeSerializer,
)
from .tasks import send_booking_notifications_task


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all().order_by("id")
    serializer_class = MovieSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    search_fields = ["title", "description"]

    ordering_fields = ["title", "duration", "id"]
    ordering = ["id"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class ShowtimeViewSet(viewsets.ModelViewSet):
    queryset = (
        Showtime.objects.select_related("movie", "hall")
        .annotate(booked_seats_count=Count("bookings"))
        .all()
        .order_by("start_time")
    )
    serializer_class = ShowtimeSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ["movie", "hall"]

    # Пошук за назвою фільму або залу: /api/showtimes/?search=IMAX
    search_fields = ["movie__title", "hall__name"]

    # Сортування за часом сеансу та ціною: /api/showtimes/?ordering=start_time
    ordering_fields = ["start_time", "price"]
    ordering = ["start_time"]

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
            .select_related("showtime__movie", "showtime__hall", "user")
            .order_by("-created_at")
        )


class CreateBookingView(generics.CreateAPIView):
    serializer_class = BookingCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        bookings = serializer.save()
        booking_ids = [b.id for b in bookings]

        transaction.on_commit(
            lambda: send_booking_notifications_task.delay(booking_ids)
        )

        response_data = BookingSerializer(bookings, many=True).data
        return Response(response_data, status=status.HTTP_201_CREATED)


class HallViewSet(viewsets.ModelViewSet):
    queryset = Hall.objects.all()
    serializer_class = HallSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


@api_view(["POST"])
@permission_classes([IsAdminUser])
def validate_qr_token(request):
    token = request.data.get("token")

    if not token:
        return Response({"status": "ERROR", "message": "Токен не надано"}, status=400)

    signer = TimestampSigner()

    try:
        data = signer.unsign_object(token, max_age=86400 * 30)

        booking_ids = data.get("booking_ids")
        showtime_id = data.get("showtime_id")

        with transaction.atomic():
            bookings = list(
                Booking.objects.select_for_update()
                .select_related("showtime__movie", "showtime__hall")
                .filter(id__in=booking_ids, showtime_id=showtime_id)
            )

            if not bookings:
                return Response(
                    {"status": "INVALID", "message": "Квиток не знайдено в системі"},
                    status=404,
                )

            already_used = [b for b in bookings if b.is_used]
            if already_used:
                first_used = already_used[0]
                formatted_time = (
                    first_used.used_at.strftime("%H:%M:%S")
                    if first_used.used_at
                    else "раніше"
                )
                return Response(
                    {
                        "status": "REJECTED",
                        "message": f"Квиток ВЖЕ ВИКОРИСТАНО о {formatted_time}!",
                    },
                    status=400,
                )

            now = timezone.now()

            Booking.objects.filter(id__in=[b.id for b in bookings]).update(
                is_used=True, used_at=now
            )

            first_b = bookings[0]
            return Response(
                {
                    "status": "VALID",
                    "message": "ПРОХІД ДОЗВОЛЕНО",
                    "movie": first_b.showtime.movie.title,
                    "hall": first_b.showtime.hall.name,
                    "seats": [f"Ряд {b.row}, Місце {b.place}" for b in bookings],
                },
                status=200,
            )

    except SignatureExpired:
        return Response(
            {"status": "EXPIRED", "message": "Термін дії квитка вичерпано"}, status=400
        )
    except BadSignature:
        return Response(
            {"status": "INVALID", "message": "Підроблений або недійсний QR-код"},
            status=400,
        )
