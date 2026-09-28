from django.test import TestCase
from django.core.management import call_command

from booking.management.commands.seed_movies import MOVIES
from booking.models import Movie


class SeedMoviesCommandTests(TestCase):
    def test_seeds_movies_and_can_be_run_more_than_once(self):
        call_command("seed_movies", verbosity=0)

        self.assertEqual(Movie.objects.count(), len(MOVIES))
        self.assertEqual(
            set(Movie.objects.values_list("title", flat=True)),
            {movie["title"] for movie in MOVIES},
        )

        call_command("seed_movies", verbosity=0)

        self.assertEqual(Movie.objects.count(), len(MOVIES))
