from django.core.management.base import BaseCommand

from booking.models import Movie


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
    help = "Create sample movies that do not already exist."

    def handle(self, *args, **options):
        created_count = 0
        for movie_data in MOVIES:
            _, created = Movie.objects.get_or_create(
                title=movie_data["title"], defaults=movie_data
            )
            created_count += created

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created_count} of {len(MOVIES)} sample movies."
            )
        )
