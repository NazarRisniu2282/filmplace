from rest_framework import serializers
from .models import Booking, Movie, CustomUser
from django.contrib.auth import get_user_model

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
            raise serializers.ValidationError(
                {"password": "Паролі не співпадають!"}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone_number=validated_data.get("phone_number", ""),
        )
        return user


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = "__all__"


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'movie', 'showtime', 'row', 'place', 'created_at']

    def validate(self, attrs):
        movie = attrs.get('movie')
        showtime = attrs.get('showtime')
        row = attrs.get('row')
        place = attrs.get('place')

        if Booking.objects.filter(movie=movie, showtime=showtime, row=row, place=place).exists():
            raise serializers.ValidationError({
                "non_field_errors": [f"Місце {place} у ряду {row} на цей сеанс вже заброньовано!"]
            })
        return attrs


class SeatSerializer(serializers.Serializer):
    row = serializers.IntegerField(min_value=1)
    place = serializers.IntegerField(min_value=1)


class BookingCreateSerializer(serializers.Serializer):
    """
    Масове бронювання місць на сеанс.
    """
    movie = serializers.PrimaryKeyRelatedField(queryset=Movie.objects.all())
    showtime = serializers.DateTimeField()
    seats = SeatSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        movie = attrs['movie']
        showtime = attrs['showtime']
        seats = attrs['seats']

        seat_tuples = [(s['row'], s['place']) for s in seats]
        if len(seat_tuples) != len(set(seat_tuples)):
            raise serializers.ValidationError({"seats": "У запиті вказано однакові місця!"})

        for seat in seats:
            already_booked = Booking.objects.filter(
                movie=movie,
                showtime=showtime,
                row=seat['row'],
                place=seat['place']
            ).exists()

            if already_booked:
                raise serializers.ValidationError(
                    {"seats": f"Місце {seat['place']} у ряду {seat['row']} вже зайняте на цей сеанс!"}
                )
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        movie = validated_data['movie']
        showtime = validated_data['showtime']
        seats = validated_data['seats']

        created_bookings = []
        for seat in seats:
            booking = Booking.objects.create(
                user=user,
                movie=movie,
                showtime=showtime,
                row=seat['row'],
                place=seat['place']
            )
            created_bookings.append(booking)

        return created_bookings
