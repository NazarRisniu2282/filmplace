# 1. Образ uv для швидкого встановлення залежностей
FROM ghcr.io/astral-sh/uv:latest AS uv_bin

# 2. Основний образ Python
FROM python:3.12-slim

# Копіюємо uv
COPY --from=uv_bin /uv /uvx /bin/

# 3. Робоча директорія
WORKDIR /filmplace

# 4. Змінні оточення
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# 5. Копіюємо файли конфігурації та встановлюємо залежності + gunicorn
COPY pyproject.toml uv.lock* ./
RUN uv pip install --system --no-cache . gunicorn

# 6. Створюємо non-root користувача для безпеки
RUN addgroup --system appgroup && adduser --system --group appuser

# 7. Копіюємо проект та надаємо права користувачу
COPY . .
RUN chown -R appuser:appgroup /filmplace

# 8. Перемикаємося на непривілейованого користувача
USER appuser

# 9. Порт
EXPOSE 8000

# 10. Команда запуску за замовчуванням (Production WSGI)
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 2"]