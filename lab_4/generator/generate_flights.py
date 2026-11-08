"""Генератор и загрузчик рейсов собственной базы (120 дней, 1500 рейсов в сутки).

Повторный запуск создаёт те же рейсы (фиксированные seed и дата начала),
а загрузка идемпотентна (ON CONFLICT DO NOTHING).
"""
import argparse
import os
from datetime import date, datetime, timedelta

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine
from sqlalchemy.dialects.postgresql import insert

from common.flightgen import generate_day

START_DATE = date(2026, 12, 1)
DAYS = 120
PER_DAY = 1500
CARRIERS = ["SU", "S7", "U6", "DP", "FV", "N4"]
SEED = "own-db-v1"

metadata = MetaData()
flights = Table(
    "flights", metadata,
    Column("carrier", String), Column("flight_number", String),
    Column("origin", String), Column("destination", String),
    Column("departure_time", DateTime), Column("arrival_time", DateTime),
    Column("price", Integer),
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://flights:flights@localhost:5432/flights"))
    ap.add_argument("--start", default=START_DATE.isoformat())
    ap.add_argument("--days", type=int, default=DAYS)
    args = ap.parse_args()
    start = date.fromisoformat(args.start)

    engine = create_engine(args.dsn)
    total = 0
    with engine.begin() as conn:
        for k in range(args.days):
            day = start + timedelta(days=k)
            rows = generate_day(day, PER_DAY, CARRIERS, SEED)
            for r in rows:                      # строки -> datetime
                r["departure_time"] = datetime.fromisoformat(r["departure_time"])
                r["arrival_time"] = datetime.fromisoformat(r["arrival_time"])
            conn.execute(insert(flights).on_conflict_do_nothing(), rows)
            total += len(rows)
    print(f"Загружено (с учётом повторов) {total} рейсов за {args.days} дней, с {start}")


if __name__ == "__main__":
    main()
