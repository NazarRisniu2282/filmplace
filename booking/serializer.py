from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from .models import Booking, Movie, Showtime, Hall

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Реєстрація користувача з перевіркою збігу паролів та хешуванням.
    """

    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "password",
            "password_confirm",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Паролі не співпадають!"})

        candidate_user = User(
            username=attrs.get("username", ""),
            email=attrs.get("email", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate_user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages}) from error

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        return User.objects.create_user(**validated_data)


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = "__all__"


class HallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hall
        fields = "__all__"


class ShowtimeSerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)
    movie_id = serializers.PrimaryKeyRelatedField(
        queryset=Movie.objects.all(), source="movie", write_only=True
    )
    hall = HallSerializer(read_only=True)
    hall_id = serializers.PrimaryKeyRelatedField(
        queryset=Hall.objects.all(), source="hall", write_only=True
    )
    is_expired = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()

    total_seats = serializers.ReadOnlyField()
    booked_seats_count = serializers.ReadOnlyField()
    free_seats_count = serializers.ReadOnlyField()

    class Meta:
        model = Showtime
        fields = [
            "id",
            "movie",
            "movie_id",
            "hall",
            "hall_id",
            "start_time",
            "end_time",
            "price",
            "is_expired",
            "is_active",
            "total_seats",
            "booked_seats_count",
            "free_seats_count",
        ]


class BookingSerializer(serializers.ModelSerializer):
    """
    Серіалайзер для відображення детальної інформації про квиток.
    """

    showtime = ShowtimeSerializer(read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    is_expired = serializers.ReadOnlyField()
    status = serializers.ReadOnlyField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "user",
            "showtime",
            "row",
            "place",
            "created_at",
            "is_expired",
            "status",
        ]


class SeatSerializer(serializers.Serializer):
    row = serializers.IntegerField(min_value=1)
    place = serializers.IntegerField(min_value=1)


class BookingCreateSerializer(serializers.Serializer):
    showtime = serializers.PrimaryKeyRelatedField(
        queryset=Showtime.objects.select_related("hall").all()
    )
    seats = SeatSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        showtime = attrs["showtime"]
        seats = attrs["seats"]
        hall = showtime.hall

        # 1. Перевірка: чи сеанс не закінчився
        if showtime.is_expired:
            raise serializers.ValidationError(
                {"showtime": "Неможливо забронювати квиток на сеанс, який вже минув!"}
            )

        # 2. Перевірка: чи не виходять місця за межі розмірів залу
        invalid_seats = []
        for s in seats:
            if s["row"] > hall.rows or s["place"] > hall.seats_per_row:
                invalid_seats.append(f"Ряд {s['row']}, Місце {s['place']}")

        if invalid_seats:
            raise serializers.ValidationError(
                {
                    "seats": f"У залі '{hall.name}' немає таких місць: {', '.join(invalid_seats)}. "
                    f"Максимум рядів: {hall.rows}, місць у ряду: {hall.seats_per_row}."
                }
            )

        # 3. Перевірка: чи немає дублікатів у запиті
        seat_tuples = [(s["row"], s["place"]) for s in seats]
        if len(seat_tuples) != len(set(seat_tuples)):
            raise serializers.ValidationError(
                {"seats": "У запиті вказано дубльовані місця!"}
            )

        # 4. Перевірка: чи місця вже заброньовані в БД
        occupied_seats = set(
            Booking.objects.filter(showtime=showtime).values_list("row", "place")
        )
        already_booked = [
            f"Ряд {s['row']}, Місце {s['place']}"
            for s in seats
            if (s["row"], s["place"]) in occupied_seats
        ]

        if already_booked:
            raise serializers.ValidationError(
                {"seats": f"Наступні місця вже зайняті: {', '.join(already_booked)}"}
            )

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        showtime = validated_data["showtime"]
        seats = validated_data["seats"]
        expires_time = timezone.now() + timedelta(minutes=10)

        bookings_to_create = [
            Booking(
                user=user,
                showtime=showtime,
                row=seat["row"],
                place=seat["place"],
                expires_at=expires_time,  
            )
            for seat in seats
        ]

        try:
            with transaction.atomic():
                locked_showtime = Showtime.objects.select_for_update().get(
                    pk=showtime.pk
                )
                occupied_seats = set(
                    Booking.objects.filter(showtime=locked_showtime).values_list(
                        "row", "place"
                    )
                )
                already_booked = [
                    f"Ряд {seat['row']}, Місце {seat['place']}"
                    for seat in seats
                    if (seat["row"], seat["place"]) in occupied_seats
                ]
                if already_booked:
                    raise serializers.ValidationError(
                        {
                            "seats": f"Наступні місця вже зайняті: {', '.join(already_booked)}"
                        }
                    )

                return Booking.objects.bulk_create(bookings_to_create)
        except IntegrityError as error:
            occupied_seats = set(
                Booking.objects.filter(showtime=showtime).values_list("row", "place")
            )
            already_booked = [
                f"Ряд {seat['row']}, Місце {seat['place']}"
                for seat in seats
                if (seat["row"], seat["place"]) in occupied_seats
            ]
            if already_booked:
                raise serializers.ValidationError(
                    {
                        "seats": f"Наступні місця вже зайняті: {', '.join(already_booked)}"
                    }
                ) from error
            raise
