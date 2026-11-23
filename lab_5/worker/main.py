import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal

import aio_pika
from sqlalchemy import select

from domain import Purchase, calculate
from models import Account, Base, Operation, Session, engine

logging.basicConfig(level=logging.INFO)
RABBITMQ_URL = os.environ["RABBITMQ_URL"]


def to_event(op):
    """Строка таблицы operations -> событие «операция обработана»."""
    return {
        "operation_id": op.operation_id,
        "type": op.type,
        "customer_id": op.customer_id,
        "store_id": op.store_id,
        "status": op.status,
        "points_delta": op.points_delta,
        "balance_after": op.balance_after,
        "reject_reason": op.reject_reason,
        "processed_at": op.processed_at.isoformat(),
    }


async def find_operation(session, op_type, check_number):
    """Ищет принятую операцию нужного вида по номеру чека."""
    query = select(Operation).where(
        Operation.type == op_type,
        Operation.check_number == check_number,
        Operation.status == "applied",
    )
    return (await session.execute(query)).scalars().first()


async def handle(data):
    """Обработка одной операции в ОДНОЙ транзакции."""
    async with Session() as session, session.begin():
        # Если сообщение пришло повторно — операция уже в базе, просто вернём её
        old = await session.get(Operation, data["operation_id"])
        if old is not None:
            return to_event(old)

        # Счёт создаётся с нулевым балансом при первой операции
        account = await session.get(Account, data["customer_id"])
        if account is None:
            account = Account(customer_id=data["customer_id"], balance=0)
            session.add(account)

        amount = Decimal(data["amount"]) if "amount" in data else None

        purchase_row = await find_operation(session, "purchase", data["check_number"])
        purchase = None
        if purchase_row is not None:
            purchase = Purchase(purchase_row.customer_id, purchase_row.points_delta)
        already_returned = await find_operation(session, "return", data["check_number"]) is not None

        # Расчёт — в доменном слое
        status, delta, reason = calculate(
            data["type"], data["customer_id"], amount, data.get("points"),
            account.balance, purchase, already_returned,
        )

        account.balance += delta
        op = Operation(
            operation_id=data["operation_id"],
            type=data["type"],
            customer_id=data["customer_id"],
            store_id=data["store_id"],
            check_number=data["check_number"],
            amount=amount,
            points_delta=delta,
            balance_after=account.balance,
            status=status,
            reject_reason=reason,
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
            processed_at=datetime.now(timezone.utc),
        )
        session.add(op)
    # здесь транзакция уже зафиксирована (commit)
    return to_event(op)


async def main():
    # Метка готовности для healthcheck: при старте удаляем старую
    if os.path.exists("/tmp/ready"):
        os.remove("/tmp/ready")

    # 1. Таблицы создаются автоматически
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Подключение к RabbitMQ
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
    await channel.set_qos(prefetch_count=1)

    # Очередь операций (direct)
    loyalty = await channel.declare_exchange("loyalty", aio_pika.ExchangeType.DIRECT, durable=True)
    queue = await channel.declare_queue("operations", durable=True, arguments={"x-queue-type": "quorum"})
    await queue.bind(loyalty, routing_key="operation")

    # Рассылка событий (fanout) — объявляем ДО обработки, чтобы события не терялись
    events = await channel.declare_exchange("loyalty.events", aio_pika.ExchangeType.FANOUT, durable=True)
    for name in ("notifier.events", "analytics.events"):
        q = await channel.declare_queue(name, durable=True, arguments={"x-queue-type": "quorum"})
        await q.bind(events)

    # Таблицы созданы, брокер подключён, очереди объявлены — worker готов
    open("/tmp/ready", "w").close()

    logging.info("worker запущен, жду операции")
    async with queue.iterator() as messages:
        async for message in messages:
            # ack будет отправлен при выходе из блока, т.е. ПОСЛЕ commit и ПОСЛЕ подтверждения публикации.
            # При ошибке сообщение вернётся в очередь (requeue=True).
            async with message.process(requeue=True):
                data = json.loads(message.body)
                event = await handle(data)
                await events.publish(
                    aio_pika.Message(
                        body=json.dumps(event).encode(),
                        content_type="application/json",
                        message_id=event["operation_id"],
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key="",
                    mandatory=True,
                )
                logging.info("обработано: %s", event)


if __name__ == "__main__":
    asyncio.run(main())
