import os
import re
import time
from datetime import date

from fastapi import FastAPI, HTTPException, Query

from . import db, providers
from .routes import build_routes

PROVIDERS = dict(
    (f"provider-{i + 1}", url.strip())
    for i, url in enumerate(os.environ.get(
        "PROVIDER_URLS",
        "http://localhost:8001,http://localhost:8002,http://localhost:8003").split(","))
)

app = FastAPI(title="Flight search (sync)")
IATA = re.compile(r"^[A-Z]{3}$")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/search")
def search(origin: str = Query(...), destination: str = Query(...), date: date = Query(...)):
    t0 = time.perf_counter()
    if not (IATA.match(origin) and IATA.match(destination)):
        raise HTTPException(422, "origin и destination — коды из трёх латинских букв")
    if origin == destination:
        raise HTTPException(400, "аэропорты вылета и прилёта совпадают")

    own = db.load_own_flights(date)                                   # база
    external, failed = providers.query_all(PROVIDERS, date)           # поставщики по очереди

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
