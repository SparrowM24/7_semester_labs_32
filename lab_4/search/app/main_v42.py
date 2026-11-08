"""Версия 4.2: полностью асинхронная (httpx, asyncpg, asyncio.gather/timeout)."""
import asyncio
import re
import time
from contextlib import asynccontextmanager
from datetime import date

import httpx
from fastapi import FastAPI, HTTPException, Query, Request

from . import db_async, providers_async
from .main import PROVIDERS
from .routes import build_routes

IATA = re.compile(r"^[A-Z]{3}$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # клиент и движок создаются один раз при запуске приложения
    app.state.client = httpx.AsyncClient(
        timeout=httpx.Timeout(5.0),
        limits=httpx.Limits(max_connections=500, max_keepalive_connections=200))
    app.state.engine = db_async.make_engine()
    yield
    await app.state.client.aclose()
    await app.state.engine.dispose()


app = FastAPI(title="Flight search (async)", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/search")
async def search(request: Request, origin: str = Query(...), destination: str = Query(...),
                 date: date = Query(...)):
    t0 = time.perf_counter()
    if not (IATA.match(origin) and IATA.match(destination)):
        raise HTTPException(422, "origin и destination — коды из трёх латинских букв")
    if origin == destination:
        raise HTTPException(400, "аэропорты вылета и прилёта совпадают")

    # база и три поставщика опрашиваются одновременно
    own, (external, failed) = await asyncio.gather(
        db_async.load_own_flights(request.app.state.engine, date),
        providers_async.query_all(request.app.state.client, PROVIDERS, date))

    if len(failed) == len(PROVIDERS) and not own:
        raise HTTPException(503, "Поиск временно недоступен")

    routes = build_routes(own + external, origin, destination, date)
    return {
        "routes": [{"price": sum(f.price for f in r),
                    "flights": [{"carrier": f.carrier, "flight_number": f.flight_number,
                                 "origin": f.origin, "destination": f.destination,
                                 "departure_time": f.departure.isoformat(),
                                 "arrival_time": f.arrival.isoformat(),
                                 "price": f.price} for f in r]} for r in routes],
        "unavailable_providers": failed,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
    }
