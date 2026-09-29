# syntax=docker/dockerfile:1

# Установка зависимостей
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Создаём виртуальное окружение вне рабочей директории
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Сначала копируем ТОЛЬКО файл зависимостей — это кэширует слой
COPY requirements.txt ./

# Обновляем pip и ставим зависимости
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# runtime — копирование зависимостей и кода
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Копируем готовое виртуальное окружение из builder
COPY --from=builder /opt/venv /opt/venv

# Копируем код приложения
COPY app.py ./

EXPOSE 5000

# Точка входа — gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "app:app"]