"""Одновременный опрос поставщиков (httpx.AsyncClient, asyncio)."""
import asyncio
from datetime import date

import httpx

from .providers import PROVIDER_BUDGET_S, RETRY_PAUSE_S, parse_flights
from .routes import Flight


async def query_provider(client: httpx.AsyncClient, base_url: str, day: date):
    """Рейсы поставщика или None. На всё (оба запроса и паузу) – 2 с."""
    try:
        async with asyncio.timeout(PROVIDER_BUDGET_S):
            for attempt in (1, 2):
                try:
                    r = await client.get(f"{base_url}/flights", params={"date": day.isoformat()})
                    if r.status_code == 200:
                        return parse_flights(r.json())
                except httpx.HTTPError:
                    pass
                if attempt == 1:
                    await asyncio.sleep(RETRY_PAUSE_S)      # пауза не блокирует цикл
    except TimeoutError:
        return None
    return None


async def query_all(client: httpx.AsyncClient, providers: dict[str, str], day: date):
    names = list(providers)
    # return_exceptions=True: сбой одного поставщика не прерывает остальных
    results = await asyncio.gather(
        *(query_provider(client, providers[n], day) for n in names), return_exceptions=True)
    flights: list[Flight] = []
    failed = []
    for name, res in zip(names, results):
        if isinstance(res, BaseException) or res is None:
            failed.append(name)
        else:
            flights.extend(res)
    return flights, failed
