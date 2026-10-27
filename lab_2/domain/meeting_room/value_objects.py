"""Объекты-значения контекста «Бронирование переговорных комнат»."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from domain.shared.errors import InvalidValueObject


@dataclass(frozen=True)
class Capacity:
    """Вместимость переговорной комнаты."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or self.value <= 0:
            raise InvalidValueObject("Вместимость должна быть положительным целым числом")


@dataclass(frozen=True)
class ParticipantsCount:
    """Число участников брони."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or self.value <= 0:
            raise InvalidValueObject("Число участников должно быть положительным целым числом")


@dataclass(frozen=True)
class OfficeHours:
    """Часы работы офиса: время суток, одинаковое для каждого дня."""

    opens_at: time
    closes_at: time

    def __post_init__(self) -> None:
        if self.opens_at >= self.closes_at:
            raise InvalidValueObject("Время открытия должно быть раньше времени закрытия")

    def contains(self, start: datetime, end: datetime) -> bool:
        # Бронь должна уложиться в один день и в часы работы.
        return (start.date() == end.date()
                and self.opens_at <= start.time()
                and end.time() <= self.closes_at)