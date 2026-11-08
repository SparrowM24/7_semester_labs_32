"""Версия 4.1: обработчики объявлены через async def, остальной код не менялся.

Блокирующие вызовы (requests, time.sleep, синхронный SQLAlchemy) теперь
выполняются прямо в потоке цикла событий.
"""
from datetime import date

from fastapi import FastAPI, Query

from . import main as sync_version

app = FastAPI(title="Flight search (async def, blocking code)")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/search")
async def search(origin: str = Query(...), destination: str = Query(...), date: date = Query(...)):
    return sync_version.search(origin, destination, date)    # тот же синхронный код
