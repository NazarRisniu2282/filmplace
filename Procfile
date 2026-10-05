web: gunicorn config.wsgi:application --workers 2 --threads 2 --bind 0.0.0.0:$PORT
worker: celery -A config worker --loglevel=info --concurrency=1