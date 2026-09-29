from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from booking.models import Hall, Movie, Showtime


HALLS = [
    {"name": "Hall 1", "rows": 10, "seats_per_row": 12},
    {"name": "Hall 2", "rows": 8, "seats_per_row": 10},
    {"name": "IMAX", "rows": 12, "seats_per_row": 14},
]


MOVIES = [
    {
        "title": "The Grand Budapest Hotel",
        "description": "A concierge and his apprentice become entangled in a painting theft and a family dispute.",
        "duration": 99,
        "rate": Movie.AgeRating.PG12,
        "rating": 8.1,
        "price": "180.00",
    },
    {
        "title": "Spirited Away",
        "description": "A young girl enters a mysterious spirit world and searches for a way to return home.",
        "duration": 125,
        "rate": Movie.AgeRating.PG12,
        "rating": 8.6,
        "price": "160.00",
    },
    {
        "title": "Interstellar",
        "description": "Explorers travel beyond Earth in search of a future for humanity.",
        "duration": 169,
        "rate": Movie.AgeRating.PG12,
        "rating": 8.7,
        "price": "220.00",
    },
    {
        "title": "The Martian",
        "description": "An astronaut stranded on Mars works to survive while a rescue mission is planned.",
        "duration": 144,
        "rate": Movie.AgeRating.PG12,
        "rating": 8.0,
        "price": "200.00",
    },
    {
        "title": "Paddington 2",
        "description": "Paddington takes on a series of odd jobs to buy a special gift for his aunt.",
        "duration": 104,
        "rate": Movie.AgeRating.G,
        "rating": 7.8,
        "price": "150.00",
    },
    {
        "title": "Knives Out",
        "description": "A detective investigates a wealthy family's secrets after a novelist's death.",
        "duration": 130,
        "rate": Movie.AgeRating.PG16,
        "rating": 7.9,
        "price": "190.00",
    },
]


class Command(BaseCommand):
    help = "Create sample movies and upcoming showtimes that do not already exist."

    def handle(self, *args, **options):
        movie_count = 0
        showtime_count = 0
        show_date = timezone.localdate() + timedelta(days=1)
        halls = [
            Hall.objects.get_or_create(name=hall_data["name"], defaults=hall_data)[0]
            for hall_data in HALLS
        ]

        for movie_index, movie_data in enumerate(MOVIES):
            movie_fields = {
                key: value for key, value in movie_data.items() if key != "price"
            }
            movie, created = Movie.objects.get_or_create(
                title=movie_data["title"], defaults=movie_fields
            )
            movie_count += created

            for session_index in range(2):
                schedule_index = movie_index * 2 + session_index
                hall = halls[schedule_index % len(halls)]
                hour = 10 + (schedule_index // len(halls)) * 3
                start_time = timezone.make_aware(
                    datetime.combine(show_date, time(hour=hour))
                )
                _, created = Showtime.objects.update_or_create(
                    movie=movie,
                    start_time=start_time,
                    defaults={"hall": hall, "price": movie_data["price"]},
                )
                showtime_count += created

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {movie_count} of {len(MOVIES)} sample movies and "
                f"{showtime_count} upcoming showtimes."
            )
        )
