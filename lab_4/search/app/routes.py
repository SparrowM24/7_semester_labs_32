"""Составление маршрутов. Чистая функция: не обращается к сети и БД."""
import heapq
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

MIN_LAYOVER = timedelta(hours=1)
MAX_LAYOVER = timedelta(hours=6)
MAX_FLIGHTS = 3          # прямой рейс или до двух пересадок
TOP_N = 20


@dataclass(frozen=True)
class Flight:
    carrier: str
    flight_number: str
    origin: str
    destination: str
    departure: datetime
    arrival: datetime
    price: int


def build_routes(flights, origin: str, destination: str, day: date, limit: int = TOP_N):
    """Возвращает не более limit самых дешёвых маршрутов (список списков Flight)."""
    by_origin = defaultdict(list)
    for f in flights:
        if f.departure.date() == day:                       # все рейсы вылетают в дату поиска
            by_origin[f.origin].append(f)
    for lst in by_origin.values():
        lst.sort(key=lambda f: f.departure)
    deps = {a: [f.departure for f in lst] for a, lst in by_origin.items()}

    found = []                                              # (цена, ..., маршрут)

    def next_flights(prev: Flight):
        """Рейсы из аэропорта прилёта prev с пересадкой от 1 до 6 часов."""
        lst = by_origin.get(prev.destination, [])
        lo = bisect_left(deps.get(prev.destination, []), prev.arrival + MIN_LAYOVER)
        hi_t = prev.arrival + MAX_LAYOVER
        for f in lst[lo:]:
            if f.departure > hi_t:
                break
            yield f

    def extend(route, visited, price):
        last = route[-1]
        if last.destination == destination:
            found.append((price, route[0].departure, tuple(f.flight_number for f in route), route))
            return
        if len(route) == MAX_FLIGHTS:
            return
        for nxt in next_flights(last):
            if nxt.destination in visited:                  # аэропорты не повторяются
                continue
            extend(route + [nxt], visited | {nxt.destination}, price + nxt.price)

    for f in by_origin.get(origin, []):
        if f.destination == origin:
            continue
        extend([f], {origin, f.destination}, f.price)

    best = heapq.nsmallest(limit, found, key=lambda x: x[:3])
    return [r[3] for r in best]
