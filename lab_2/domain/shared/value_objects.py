"""Общие объекты-значения для всех контекстов."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .errors import InvalidValueObject


@dataclass(frozen=True)
class Money:
    """Денежная сумма. Округление до копеек, запрет отрицательных значений."""

    amount: float

    def __post_init__(self) -> None:
        if not isinstance(self.amount, (int, float)):
            raise InvalidValueObject("Сумма должна быть числом")
        if self.amount < 0:
            raise InvalidValueObject("Сумма не может быть отрицательной")
        object.__setattr__(self, "amount", round(float(self.amount), 2))

    def __add__(self, other: "Money") -> "Money":
        return Money(self.amount + other.amount)


@dataclass(frozen=True)
class TimeInterval:
    """Временной интервал [start, end)."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise InvalidValueObject("Начало интервала должно быть раньше окончания")

    def overlaps(self, other: "TimeInterval") -> bool:
        return self.start < other.end and other.start < self.end
