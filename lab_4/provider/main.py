"""Заглушка поставщика. Параметры задаются переменными окружения."""
import asyncio
import os
import random
from datetime import date
from functools import lru_cache

from fastapi import FastAPI, HTTPException

from common.flightgen import generate_day

PROVIDER_ID = os.environ.get("PROVIDER_ID", "1")
MEAN_DELAY_MS = float(os.environ.get("MEAN_DELAY_MS", "300"))
JITTER = float(os.environ.get("DELAY_JITTER", "0.3"))          # ±30 %
ERROR_RATE = float(os.environ.get("ERROR_RATE", "0.05"))        # доля ответов 500
SLOW_RATE = float(os.environ.get("SLOW_RATE", "0"))             # доля ответов с задержкой
SLOW_DELAY_MS = float(os.environ.get("SLOW_DELAY_MS", "3000"))
FLIGHTS_PER_DAY = int(os.environ.get("FLIGHTS_PER_DAY", "500"))
CARRIERS = [f"P{PROVIDER_ID}"]

app = FastAPI(title=f"provider-{PROVIDER_ID}")


@lru_cache(maxsize=256)
def flights_for(day: date):
    return generate_day(day, FLIGHTS_PER_DAY, CARRIERS, seed=f"provider-{PROVIDER_ID}")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/flights")
async def get_flights(date: date):
    # async def + asyncio.sleep: заглушка не должна ограничивать нагрузку
    # числом потоков, иначе она исказит замеры сервиса поиска.
    slow = random.random() < SLOW_RATE
    fail = random.random() < ERROR_RATE
    if slow:
        delay = SLOW_DELAY_MS
    else:
        delay = MEAN_DELAY_MS * random.uniform(1 - JITTER, 1 + JITTER)
    await asyncio.sleep(delay / 1000)
    if fail:
        raise HTTPException(status_code=500, detail="provider error")
    return flights_for(date)
