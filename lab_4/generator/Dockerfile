FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "sqlalchemy>=2.0" "psycopg[binary]>=3.1"
COPY common /app/common
COPY generator/generate_flights.py /app/generate_flights.py
CMD ["python", "generate_flights.py"]
