"""Объекты-значения контекста «Бронирование переговорных комнат»."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

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
    """Часы работы офиса."""

    opens_at: datetime
    closes_at: datetime

    def __post_init__(self) -> None:
        if self.opens_at >= self.closes_at:
            raise InvalidValueObject("Время открытия должно быть раньше времени закрытия")

    def contains(self, start: datetime, end: datetime) -> bool:
        return self.opens_at <= start and end <= self.closes_at
