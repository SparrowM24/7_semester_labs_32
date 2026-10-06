"""Объекты-значения контекста «Платная парковка»."""

from __future__ import annotations

from dataclasses import dataclass

from domain.shared.errors import InvalidValueObject
from domain.shared.value_objects import Money


@dataclass(frozen=True)
class HourlyTariff:
    """Тариф за час парковки."""

    price_per_hour: Money

    def __post_init__(self) -> None:
        if self.price_per_hour.amount <= 0:
            raise InvalidValueObject("Цена за час должна быть больше нуля")

    def cost_for(self, hours: int) -> Money:
        if hours < 0:
            raise InvalidValueObject("Количество часов не может быть отрицательным")
        return Money(self.price_per_hour.amount * hours)