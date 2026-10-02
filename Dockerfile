# 1. Образ uv для швидкого встановлення залежностей
FROM ghcr.io/astral-sh/uv:latest AS uv_bin

# 2. Основний образ Python (ЗМІНЕНО НА 3.12)
FROM python:3.12-slim

# Копіюємо uv
COPY --from=uv_bin /uv /uvx /bin/

# 3. Робоча директорія
WORKDIR /filmplace

# 4. Змінні оточення
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# 5. Копіюємо файли конфігурації та встановлюємо залежності
COPY pyproject.toml uv.lock* ./
RUN uv pip install --system --no-cache .

# 6. Копіюємо проект
COPY . .

# 7. Порт
EXPOSE 8000

# 8. Команда запуску
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]