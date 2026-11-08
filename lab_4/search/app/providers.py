"""Опрос поставщиков по очереди (синхронно, requests)."""
import threading
import time
from datetime import date, datetime

import requests

from .routes import Flight

PROVIDER_BUDGET_S = 2.0      # на поставщика, включая повторный запрос
RETRY_PAUSE_S = 0.2

_local = threading.local()


def _session() -> requests.Session:
    # Session не потокобезопасна -> по одной на поток
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
    return _local.s


def parse_flights(items) -> list[Flight]:
    return [Flight(i["carrier"], i["flight_number"], i["origin"], i["destination"],
                   datetime.fromisoformat(i["departure_time"]),
                   datetime.fromisoformat(i["arrival_time"]), int(i["price"]))
            for i in items]


def query_provider(base_url: str, day: date) -> list[Flight] | None:
    """Рейсы поставщика или None, если он не ответил в отведённое время."""
    started = time.monotonic()
    for attempt in (1, 2):
        remaining = PROVIDER_BUDGET_S - (time.monotonic() - started)
        if remaining <= 0:
            return None
        try:
            r = _session().get(f"{base_url}/flights", params={"date": day.isoformat()},
                               timeout=remaining)
            if r.status_code == 200:
                return parse_flights(r.json())
        except requests.Timeout:
            return None                  # время вышло, повтор не имеет смысла
        except requests.RequestException:
            pass
        # ошибка: один повтор через 200 мс, если укладываемся в бюджет
        if attempt == 1:
            if PROVIDER_BUDGET_S - (time.monotonic() - started) <= RETRY_PAUSE_S:
                return None
            time.sleep(RETRY_PAUSE_S)
    return None


def query_all(providers: dict[str, str], day: date):
    """Опрашивает поставщиков по очереди. Возвращает (рейсы, имена не ответивших)."""
    flights, failed = [], []
    for name, url in providers.items():
        res = query_provider(url, day)
        if res is None:
            failed.append(name)
        else:
            flights.extend(res)
    return flights, failed
