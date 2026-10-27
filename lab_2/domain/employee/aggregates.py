"""Агрегат «Сотрудник»: неявки и запрет на крупные комнаты."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

NO_SHOW_LIMIT = 3


def next_month_start(now: datetime) -> datetime:
    if now.month == 12:
        return datetime(now.year + 1, 1, 1)
    return datetime(now.year, now.month + 1, 1)


@dataclass
class Employee:
    id: str
    name: str
    _no_shows: List[datetime] = field(default_factory=list, repr=False)
    _large_rooms_ban_until: Optional[datetime] = None

    @classmethod
    def new(cls, name: str) -> "Employee":
        return cls(id=str(uuid4()), name=name)

    def no_shows_in_month(self, now: datetime) -> int:
        return sum(1 for d in self._no_shows
                   if (d.year, d.month) == (now.year, now.month))

    def register_no_show(self, now: datetime) -> int:
        self._no_shows.append(now)
        return self.no_shows_in_month(now)

    def would_reach_limit(self, now: datetime) -> bool:
        """Предикат шлюза «Неявок за месяц три или больше?» (с учётом текущей неявки)."""
        return self.no_shows_in_month(now) + 1 >= NO_SHOW_LIMIT

    def ban_large_rooms(self, until: datetime) -> None:
        self._large_rooms_ban_until = until

    def is_banned_from_large_rooms(self, now: datetime) -> bool:
        return self._large_rooms_ban_until is not None and now < self._large_rooms_ban_until