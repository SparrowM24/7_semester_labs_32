# Стадия 1: установка зависимостей
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Стадия 2: итоговый образ (без pip-кэша и лишнего)
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY *.py .
RUN useradd --no-create-home appuser
USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
