import os
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import Literal

import aio_pika
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, model_validator
from sqlalchemy import select, text

from models import Account, Operation, Session

RABBITMQ_URL = os.environ["RABBITMQ_URL"]
connection = None
exchange = None


@asynccontextmanager
async def lifespan(app):
    global connection, exchange
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
    exchange = await channel.declare_exchange("loyalty", aio_pika.ExchangeType.DIRECT, durable=True)
    queue = await channel.declare_queue("operations", durable=True, arguments={"x-queue-type": "quorum"})
    await queue.bind(exchange, routing_key="operation")
    yield
    await connection.close()


app = FastAPI(lifespan=lifespan)


class OperationIn(BaseModel):
    """Проверка формата операции. Ошибка -> FastAPI сам вернёт 422."""
    operation_id: str
    type: Literal["purchase", "return", "redeem"]
    customer_id: str
    store_id: str
    check_number: str
    occurred_at: datetime
    amount: Decimal | None = None
    points: int | None = None

    @model_validator(mode="after")
    def check_fields(self):
        if self.type in ("purchase", "redeem"):
            if self.amount is None or self.amount <= 0:
                raise ValueError("amount обязателен и должен быть > 0")
        if self.type == "return" and self.amount is not None:
            raise ValueError("в возврате amount не передаётся")
        if self.type == "redeem":
            if self.points is None or self.points <= 0:
                raise ValueError("points обязателен и должен быть > 0")
        elif self.points is not None:
            raise ValueError("points передаётся только для redeem")
        return self


def op_to_dict(op):
    return {
        "operation_id": op.operation_id,
        "type": op.type,
        "store_id": op.store_id,
        "check_number": op.check_number,
        "amount": str(op.amount) if op.amount is not None else None,
        "status": op.status,
        "points_delta": op.points_delta,
        "balance_after": op.balance_after,
        "reject_reason": op.reject_reason,
        "occurred_at": op.occurred_at.isoformat(),
        "processed_at": op.processed_at.isoformat(),
    }


@app.post("/operations", status_code=202)
async def create_operation(op: OperationIn):
    body = op.model_dump_json(exclude_none=True).encode()
    message = aio_pika.Message(
        body=body,
        content_type="application/json",
        message_id=op.operation_id,
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )
    try:
        # await ждёт подтверждения от брокера (publisher confirms)
        await exchange.publish(message, routing_key="operation", mandatory=True)
    except Exception:
        raise HTTPException(503, "брокер не подтвердил публикацию")
    return {"operation_id": op.operation_id}


@app.get("/operations/{operation_id}")
async def get_operation(operation_id: str):
    async with Session() as session:
        op = await session.get(Operation, operation_id)
    if op is None:
        raise HTTPException(404, "операция ещё не обработана")
    return {
        "operation_id": op.operation_id,
        "status": op.status,
        "points_delta": op.points_delta,
        "balance_after": op.balance_after,
        "reject_reason": op.reject_reason,
    }


@app.get("/accounts/{customer_id}")
async def get_account(customer_id: str):
    async with Session() as session:
        account = await session.get(Account, customer_id)
        if account is None:
            raise HTTPException(404, "счёт не найден")
        query = (
            select(Operation)
            .where(Operation.customer_id == customer_id)
            .order_by(Operation.processed_at.desc())
            .limit(20)
        )
        ops = (await session.execute(query)).scalars().all()
    return {
        "customer_id": account.customer_id,
        "balance": account.balance,
        "operations": [op_to_dict(op) for op in ops],
    }


@app.get("/health")
async def health():
    try:
        async with Session() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    broker_ok = connection is not None and not connection.is_closed
    if db_ok and broker_ok:
        return {"database": "ok", "broker": "ok"}
    return JSONResponse(
        status_code=503,
        content={"database": "ok" if db_ok else "fail", "broker": "ok" if broker_ok else "fail"},
    )
