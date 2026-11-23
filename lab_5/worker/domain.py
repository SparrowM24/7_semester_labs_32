# Доменный слой: только расчёт баллов.
# Здесь НЕТ aio-pika и SQLAlchemy — обычный Python.
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Purchase:
    """Принятая покупка, найденная по номеру чека."""
    customer_id: str
    points: int  # сколько баллов было начислено за этот чек


def calculate(op_type, customer_id, amount, points, balance, purchase, already_returned):
    """Возвращает (status, points_delta, reject_reason)."""

    if op_type == "purchase":
        if purchase is not None:
            return "rejected", 0, "duplicate_purchase"
        bonus = int(amount * 5 / 100)  # 5 %, дробная часть отбрасывается
        return "applied", bonus, None

    if op_type == "return":
        if purchase is None:
            return "rejected", 0, "purchase_not_found"
        if purchase.customer_id != customer_id:
            return "rejected", 0, "customer_mismatch"
        if already_returned:
            return "rejected", 0, "already_returned"
        return "applied", -purchase.points, None

    if op_type == "redeem":
        if points > amount * Decimal("0.3"):
            return "rejected", 0, "limit_exceeded"
        if points > balance:
            return "rejected", 0, "insufficient_balance"
        return "applied", -points, None
