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

# Сначала копируем ТОЛЬКО файл зависимостей – это кэширует слой
COPY requirements.txt ./

# Обновляем pip и ставим зависимости
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# runtime – копирование зависимостей и кода
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=5000 \
    LOG_LEVEL=INFO

# Непривилегированный пользователь
RUN groupadd --system --gid 10001 app && \
    useradd --system --uid 10001 --gid app --no-create-home app

# Копируем готовое виртуальное окружение из builder
COPY --from=builder /opt/venv /opt/venv

# Копируем код приложения
COPY domain ./domain
COPY application ./application
COPY infrastructure ./infrastructure
COPY web ./web
COPY gunicorn.conf.py ./

USER app

EXPOSE 5000

# Проверка готовности по /health
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT','5000'), timeout=2)"]

# Точка входа – gunicorn, один worker (параметры в gunicorn.conf.py)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "web.app:create_app()"]