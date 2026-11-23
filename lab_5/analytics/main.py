import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI, HTTPException

logging.basicConfig(level=logging.INFO)
RABBITMQ_URL = os.environ["RABBITMQ_URL"]

# Статистика в памяти: store_id -> словарь со счётчиками
stores = {}
received = 0


def handle(event):
    global received
    received += 1
    store_id = event["store_id"]
    if store_id not in stores:
        stores[store_id] = {
            "store_id": store_id,
            "purchases": 0,        # принятые покупки
            "returns": 0,          # принятые возвраты
            "redeems": 0,          # принятые оплаты баллами
            "rejected": 0,         # отклонённые операции
            "points_accrued": 0,   # начислено баллов
            "points_returned": 0,  # списано при возвратах
            "points_redeemed": 0,  # потрачено на оплату
        }
    s = stores[store_id]

    if event["status"] == "rejected":
        s["rejected"] += 1
        return

    delta = abs(event["points_delta"])
    if event["type"] == "purchase":
        s["purchases"] += 1
        s["points_accrued"] += delta
    elif event["type"] == "return":
        s["returns"] += 1
        s["points_returned"] += delta
    elif event["type"] == "redeem":
        s["redeems"] += 1
        s["points_redeemed"] += delta


async def consume(connection):
    try:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        exchange = await channel.declare_exchange("loyalty.events", aio_pika.ExchangeType.FANOUT, durable=True)
        queue = await channel.declare_queue("analytics.events", durable=True, arguments={"x-queue-type": "quorum"})
        await queue.bind(exchange)
        async with queue.iterator() as messages:
            async for message in messages:
                async with message.process():  # ack после обработки
                    handle(json.loads(message.body))
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


@app.get("/stores")
async def get_stores():
    return list(stores.values())


@app.get("/stores/{store_id}")
async def get_store(store_id: str):
    if store_id not in stores:
        raise HTTPException(404, "по магазину нет событий")
    return stores[store_id]


@app.get("/stats")
async def get_stats():
    return {"received": received}
