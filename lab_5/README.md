# Лабораторная работа №5 — бонусная программа на RabbitMQ

## Запуск

```
docker compose up --build
```

- api: http://localhost:8000/docs
- notifier: http://localhost:8001/docs
- analytics: http://localhost:8002/docs
- RabbitMQ: http://localhost:15672 (логин/пароль `loyalty` / `loyalty`, см. файл `.env`)

## Структура

```
api/        FastAPI: принимает операции, кладёт в очередь, отдаёт данные из БД
worker/     обрабатывает очередь operations, считает баллы, пишет в БД, публикует события
  domain.py   расчёт баллов (без aio-pika и SQLAlchemy)
  models.py   таблицы accounts и operations
notifier/   уведомления покупателям (данные в памяти)
analytics/  статистика по магазинам (данные в памяти)
```

## Как идёт операция

```
касса -> POST /operations (api) -> обменник loyalty (direct, ключ operation) -> очередь operations
      -> worker: транзакция в БД -> событие в обменник loyalty.events (fanout)
      -> очереди notifier.events и analytics.events -> notifier и analytics
```

## Проверочные запросы

```
curl -X POST localhost:8000/operations -H "Content-Type: application/json" -d "{\"operation_id\":\"op1\",\"type\":\"purchase\",\"customer_id\":\"C1042\",\"store_id\":\"S12\",\"check_number\":\"S12-1\",\"amount\":\"2490.00\",\"occurred_at\":\"2026-11-10T14:32:05+07:00\"}"
curl localhost:8000/operations/op1
curl localhost:8000/accounts/C1042
curl localhost:8000/health
curl "localhost:8001/notifications?customer_id=C1042"
curl localhost:8001/stats
curl localhost:8002/stores
curl localhost:8002/stores/S12
curl localhost:8002/stats
```

Можно отправлять запросы и через страницу http://localhost:8000/docs (кнопка «Try it out»).

## Ответы на вопросы преподавателя

**Почему api возвращает 202, а не 200?** 202 значит «принято в обработку». Баллы считает worker позже, результат смотрим через `GET /operations/{id}`.

**direct и fanout — в чём разница?** direct отправляет сообщение в очередь, у которой ключ привязки совпадает с ключом сообщения (`operation`). fanout копирует сообщение во все привязанные очереди, ключ не учитывает. Поэтому notifier и analytics получают каждый свою копию события.

**Зачем у notifier и analytics отдельные очереди?** Если бы оба читали одну очередь, сообщения делились бы между ними, а не копировались каждому.

**Почему worker объявляет очереди notifier.events и analytics.events?** Если очереди ещё нет, событие уйдёт «в никуда». worker создаёт их до начала работы, поэтому события не теряются, даже если notifier ещё не запустился.

**durable, delivery_mode=2, quorum — зачем?** durable: обменник и очередь сохраняются после перезапуска брокера. delivery_mode=2 (PERSISTENT): сообщение записывается на диск. quorum: надёжный тип очереди с репликацией.

**publisher confirms и ack — это одно и то же?** Нет. Publisher confirms означает, что брокер подтвердил отправителю, что принял сообщение (`await exchange.publish(...)` ждёт этого подтверждения). Ack означает, что получатель подтвердил брокеру, что обработал сообщение.

**Когда worker делает ack?** При выходе из блока `async with message.process()`, то есть после commit транзакции и после того, как брокер подтвердил публикацию события. Если что-то упало, сообщение вернётся в очередь (`requeue=True`).

**Что будет, если сообщение придёт второй раз?** worker найдёт операцию по `operation_id` в базе и просто заново опубликует событие, не начисляя баллы повторно.

**prefetch_count=1?** Брокер выдаёт worker'у не больше одного неподтверждённого сообщения, поэтому операции обрабатываются строго по одной и по порядку.

**connect_robust?** Соединение, которое само восстанавливается после обрыва связи.

**Почему потребитель в notifier/analytics запускается через create_task?** Цикл `async for` бесконечный. Если запустить его напрямую, FastAPI не начнёт отвечать на HTTP. Фоновая задача работает параллельно с маршрутами.

**Где доменный слой?** `worker/domain.py`, функция `calculate`. Это чистый Python: получает данные, возвращает `(status, points_delta, reject_reason)`. Проверки идут в порядке таблицы 3.

**Как считаются 5 %?** `int(amount * 5 / 100)`: `int` отбрасывает дробную часть. amount имеет тип `Decimal`, в базе он хранится как `NUMERIC`.

**Почему в compose `postgres`, а не `localhost`?** Внутри Docker Compose каждый контейнер доступен по имени сервиса. `localhost` в контейнере указывает на сам этот контейнер.

**Многостадийный Dockerfile?** На первой стадии устанавливаются зависимости. На вторую стадию копируются только готовые пакеты и код. Запуск идёт от пользователя `appuser`, а не от root.
