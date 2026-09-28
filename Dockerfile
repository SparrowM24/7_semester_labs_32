# ─── Раздел II: многостадийная сборка на базе python:3.11-slim ───

# Стадия 1: установка зависимостей
FROM python:3.11-slim AS builder

WORKDIR /app

# Сначала копируем только requirements.txt — для кэширования слоёв
COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Стадия 2: финальный образ
FROM python:3.11-slim AS runner

WORKDIR /app

# Забираем установленные зависимости из стадии сборки
COPY --from=builder /install /usr/local

# Копируем код приложения
COPY . .

EXPOSE 5000

# ─── Раздел II, п. 3: точка входа через gunicorn ───
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]