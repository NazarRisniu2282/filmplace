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
i&!3c%e&de6nm6b*dv*9(nf1^9drz!9o_@0dd)*lxlr%nip%*'
# Перевірка Redis
redis:
	redis-cli ping

# Django Shell
shell:
	python manage.py shell