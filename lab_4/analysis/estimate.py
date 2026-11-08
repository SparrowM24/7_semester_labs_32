"""Оценка среднего времени ответа и p95 для последовательного и параллельного опроса (метод Монте-Карло).

Допущения: задержка ответа поставщика равномерна на [0,7·d; 1,3·d]; ошибка 500 приходит
после обычной задержки; повтор через 200 мс; на поставщика 2 с; ответ с задержкой 3 с
обрывается по тайм-ауту; БД ≈ 15 мс, разбор JSON + маршруты + ответ ≈ 23 мс.
"""
import random
import statistics as st

random.seed(1)
PROVIDERS = [(300, .05, 0), (500, .05, 0), (800, .05, .10)]   # задержка, доля 500, доля «3 с»
DB, CPU, BUDGET = 15, 23, 2000


def provider_time(mean, err, slow):
    t = 0
    for attempt in (1, 2):
        d = 3000 if random.random() < slow else mean * random.uniform(.7, 1.3)
        failed = random.random() < err
        if t + d >= BUDGET:
            return BUDGET
        t += d
        if not failed:
            return t
        if attempt == 1:
            if BUDGET - t <= 200:
                return BUDGET
            t += 200
    return t


def q(a, p):
    a = sorted(a)
    return a[int(len(a) * p)]


seq, par = [], []
for _ in range(200_000):
    w = [provider_time(*p) for p in PROVIDERS]
    seq.append(DB + sum(w) + CPU)
    par.append(max(max(w), DB) + CPU)
print("W поставщиков, мс:", [round(st.mean(provider_time(*p) for _ in range(100_000))) for p in PROVIDERS])
for name, a in (("по очереди", seq), ("одновременно", par)):
    print(f"{name:13s} среднее {st.mean(a):6.0f}  p50 {q(a, .5):6.0f}  p95 {q(a, .95):6.0f}  p99 {q(a, .99):6.0f} мс")
