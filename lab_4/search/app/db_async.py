"""Асинхронная работа с PostgreSQL: SQLAlchemy async + asyncpg."""
import os
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .db import flights_t
from .routes import Flight

ASYNC_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://flights:flights@localhost:5432/flights") \
    .replace("postgresql+psycopg://", "postgresql+asyncpg://")


def make_engine() -> AsyncEngine:
    return create_async_engine(ASYNC_URL, pool_size=10, max_overflow=30)


async def load_own_flights(engine: AsyncEngine, day: date) -> list[Flight]:
    start = datetime.combine(day, time.min)
    stmt = select(flights_t).where(flights_t.c.departure_time >= start,
                                   flights_t.c.departure_time < start + timedelta(days=1))
    async with engine.connect() as conn:
        rows = (await conn.execute(stmt)).all()
    return [Flight(r.carrier, r.flight_number, r.origin.strip(), r.destination.strip(),
                   r.departure_time, r.arrival_time, r.price) for r in rows]
