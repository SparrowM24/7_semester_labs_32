"""Нагрузочный скрипт: замкнутый и открытый режимы + опрос /health каждые 100 мс.

Примеры:
  python loadtest.py --mode closed --clients 10
  python loadtest.py --mode open --rate 5
"""
import argparse
import asyncio
import json
import random
import time

import httpx

AIRPORTS = ["SVO", "DME", "VKO", "LED", "OVB", "KZN", "AER", "KRR", "SVX", "ROV",
            "UFA", "KJA", "GOJ", "KUF", "VVO", "KGD", "MRV", "IKT", "PEE", "CEK",
            "TJM", "OMS", "KHV", "MMK", "ARH", "YKS", "TOF", "BAX", "KEJ", "NJC"]


def percentile(sorted_vals, q):
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * q / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def summarize(records, duration):
    """records: список (длительность_мс, ok)."""
    lat = sorted(r[0] for r in records)
    errors = sum(1 for r in records if not r[1])
    return {
        "n": len(records),
        "rps": len(records) / duration,
        "p50": percentile(lat, 50), "p95": percentile(lat, 95), "p99": percentile(lat, 99),
        "max": lat[-1] if lat else float("nan"),
        "errors_pct": 100 * errors / len(records) if records else float("nan"),
    }


async def timed_get(client, url, params, records, measure_from, measure_to):
    t_start = time.monotonic()
    try:
        r = await client.get(url, params=params)
        ok = r.status_code == 200
    except Exception:
        ok = False
    t_end = time.monotonic()
    if measure_from <= t_start < measure_to:          # прогрев не учитывается
        records.append(((t_end - t_start) * 1000, ok))


def make_params(rng, date):
    o, d = rng.sample(AIRPORTS, 2)
    return {"origin": o, "destination": d, "date": date}


async def closed_mode(client, a, rng, records, t_from, t_to):
    async def worker():
        while time.monotonic() < t_to:
            await timed_get(client, f"{a.url}/search", make_params(rng, a.date),
                            records, t_from, t_to)
    await asyncio.gather(*(worker() for _ in range(a.clients)))


async def open_mode(client, a, rng, records, t_from, t_to):
    tasks = []
    next_t = time.monotonic()
    while next_t < t_to:
        delay = next_t - time.monotonic()
        if delay > 0:
            await asyncio.sleep(delay)
        tasks.append(asyncio.create_task(timed_get(
            client, f"{a.url}/search", make_params(rng, a.date), records, t_from, t_to)))
        next_t += rng.expovariate(a.rate)             # экспоненциальные интервалы
    await asyncio.gather(*tasks)                      # дождаться ответов (тайм-аут клиента ограничит)


async def health_poller(a, records, t_from, t_to):
    async with httpx.AsyncClient(timeout=a.timeout) as hc:   # отдельный пул соединений
        next_t = time.monotonic()
        while time.monotonic() < t_to:
            delay = next_t - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            await timed_get(hc, f"{a.url}/health", None, records, t_from, t_to)
            next_t += 0.1


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--mode", choices=["closed", "open"], required=True)
    ap.add_argument("--clients", type=int, default=10, help="C для замкнутого режима")
    ap.add_argument("--rate", type=float, default=5.0, help="запросов/с для открытого режима")
    ap.add_argument("--duration", type=float, default=60)
    ap.add_argument("--warmup", type=float, default=10)
    ap.add_argument("--timeout", type=float, default=30)
    ap.add_argument("--date", default="2026-12-10")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--json", help="сохранить результат в файл")
    a = ap.parse_args()

    rng = random.Random(a.seed)
    t0 = time.monotonic()
    t_from, t_to = t0 + a.warmup, t0 + a.warmup + a.duration
    search_rec, health_rec = [], []
    limits = httpx.Limits(max_connections=2000, max_keepalive_connections=2000)
    async with httpx.AsyncClient(timeout=a.timeout, limits=limits) as client:
        poller = asyncio.create_task(health_poller(a, health_rec, t_from, t_to))
        if a.mode == "closed":
            await closed_mode(client, a, rng, search_rec, t_from, t_to)
        else:
            await open_mode(client, a, rng, search_rec, t_from, t_to)
        await poller

    res = {"mode": a.mode, "clients": a.clients if a.mode == "closed" else None,
           "rate": a.rate if a.mode == "open" else None,
           "search": summarize(search_rec, a.duration),
           "health": summarize(health_rec, a.duration)}
    for name in ("search", "health"):
        s = res[name]
        print(f"[{name}] запросов={s['n']}  rps={s['rps']:.2f}  p50={s['p50']:.0f} мс  "
              f"p95={s['p95']:.0f} мс  p99={s['p99']:.0f} мс  max={s['max']:.0f} мс  "
              f"ошибок={s['errors_pct']:.1f}%")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    asyncio.run(main())
