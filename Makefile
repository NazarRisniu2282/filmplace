.PHONY: run worker shell redis

# Запуск Django сервера
run:
	python manage.py runserver

# Запуск Celery воркера
worker:
	celery -A config worker --loglevel=info

# Запуск Celery з автоперезавантаженням при зміні коду (потрібно: pip install watchfiles)
worker-watch:
	celery -A config worker --loglevel=info --watch

# Перевірка Redis
redis:
	redis-cli ping

# Django Shell
shell:
	python manage.py shell