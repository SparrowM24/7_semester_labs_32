"""Детерминированный генератор рейсов (общий для БД и заглушек поставщиков)."""
import random
from datetime import date, datetime, timedelta

AIRPORTS = [
    "SVO", "DME", "VKO", "LED", "OVB", "KZN", "AER", "KRR", "SVX", "ROV",
    "UFA", "KJA", "GOJ", "KUF", "VVO", "KGD", "MRV", "IKT", "PEE", "CEK",
    "TJM", "OMS", "KHV", "MMK", "ARH", "YKS", "TOF", "BAX", "KEJ", "NJC",
]


def generate_day(day: date, count: int, carriers: list[str], seed: str):
    """Возвращает список из count рейсов, вылетающих в дату day.

    Результат зависит только от (day, count, carriers, seed): генератор
    random.Random со строковым seed даёт одну и ту же последовательность
    при каждом запуске.
    """
    rng = random.Random(f"{seed}:{day.isoformat()}")
    midnight = datetime(day.year, day.month, day.day)
    flights = []
    for i in range(count):
        carrier = carriers[rng.randrange(len(carriers))]
        origin, destination = rng.sample(AIRPORTS, 2)
        departure = midnight + timedelta(minutes=rng.randrange(24 * 60))
        duration_min = rng.randrange(60, 6 * 60 + 1)          # 1..6 часов
        arrival = departure + timedelta(minutes=duration_min)
        price = int(round((1500 + duration_min * 18 + rng.uniform(0, 3000)) / 10) * 10)
        flights.append({
            "carrier": carrier,
            "flight_number": f"{carrier}{100 + i}",
            "origin": origin,
            "destination": destination,
            "departure_time": departure.isoformat(),
            "arrival_time": arrival.isoformat(),
            "price": price,
        })
    return flights
