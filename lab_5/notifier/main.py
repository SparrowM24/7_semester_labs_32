import asyncio
import json
import logging
import os
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import aio_pika
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
RABBITMQ_URL = os.environ["RABBITMQ_URL"]
MIN_DELAY_MS = int(os.getenv("MIN_DELAY_MS", "200"))
MAX_DELAY_MS = int(os.getenv("MAX_DELAY_MS", "1500"))
UNSUBSCRIBED = {c.strip() for c in os.getenv("UNSUBSCRIBED", "").split(",") if c.strip()}

# Всё хранится в памяти
notifications = []
processed = set()  # номера уже обработанных операций — защита от повторных событий
received = 0
sent = 0


def make_text(event):
    if event["status"] == "rejected":
        return f"Операция отклонена: {event['reject_reason']}"
    delta = event["points_delta"]
    if delta >= 0:
        return f"Начислено {delta} баллов, баланс {event['balance_after']}"
    return f"Списано {-delta} баллов, баланс {event['balance_after']}"


async def handle(event):
    global received, sent
    # Повторное событие (at-least-once) — пропускаем, чтобы не отправить уведомление дважды
    if event["operation_id"] in processed:
        logging.info("Повтор события %s, пропускаю", event["operation_id"])
        return
    processed.add(event["operation_id"])
    received += 1
    if event["customer_id"] in UNSUBSCRIBED:
        return  # отписан — не отправляем
    text = make_text(event)
    await asyncio.sleep(random.randint(MIN_DELAY_MS, MAX_DELAY_MS) / 1000)  # имитация отправки
    logging.info("Уведомление %s: %s", event["customer_id"], text)
    notifications.append({
        "customer_id": event["customer_id"],
        "operation_id": event["operation_id"],
        "text": text,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    })
    sent += 1


async def consume(connection):
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        exchange = await channel.declare_exchange("loyalty.events", aio_pika.ExchangeType.FANOUT, durable=True)
        queue = await channel.declare_queue("notifier.events", durable=True, arguments={"x-queue-type": "quorum"})
        await queue.bind(exchange)
        async with queue.iterator() as messages:
            async for message in messages:
                async with message.process():  # ack после обработки
                    await handle(json.loads(message.body))
    except asyncio.CancelledError:
        raise
    except Exception:
        logging.exception("Ошибка в получении событий")


@asynccontextmanager
async def lifespan(app):
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    task = asyncio.create_task(consume(connection))  # в фоне, чтобы не блокировать HTTP
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await connection.close()


app = FastAPI(lifespan=lifespan)


@app.get("/notifications")
async def get_notifications(customer_id: str):
    return [n for n in notifications if n["customer_id"] == customer_id]


@app.get("/stats")
async def get_stats():
    return {"received": received, "sent": sent}
