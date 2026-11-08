"""Синхронная работа с PostgreSQL через SQLAlchemy Core (драйвер psycopg)."""
import os
from datetime import date, datetime, time, timedelta

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, select

from .routes import Flight

DATABASE_URL = os.environ.get("DATABASE_URL",
                              "postgresql+psycopg://flights:flights@localhost:5432/flights")

engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=30, pool_pre_ping=False)

metadata = MetaData()
flights_t = Table(
    "flights", metadata,
    Column("carrier", String), Column("flight_number", String),
    Column("origin", String), Column("destination", String),
    Column("departure_time", DateTime), Column("arrival_time", DateTime),
    Column("price", Integer),
)


def load_own_flights(day: date) -> list[Flight]:
    start = datetime.combine(day, time.min)
    stmt = select(flights_t).where(flights_t.c.departure_time >= start,
                                   flights_t.c.departure_time < start + timedelta(days=1))
    # соединение удерживается только на время запроса
    with engine.connect() as conn:
        rows = conn.execute(stmt).all()
    return [Flight(r.carrier, r.flight_number, r.origin.strip(), r.destination.strip(),
                   r.departure_time, r.arrival_time, r.price) for r in rows]
