"""Агрегат «Парковочное место»."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Optional
from uuid import uuid4

from domain.shared.errors import DomainInvariantViolation
from domain.shared.value_objects import Money

from .value_objects import HourlyTariff


@dataclass(frozen=True)
class ParkingSession:
    """Сущность парковочной сессии внутри агрегата."""

    id: str
    space_id: str
    entry_time: datetime
    exit_time: Optional[datetime] = None

    @property
    def is_open(self) -> bool:
        return self.exit_time is None


@dataclass
class ParkingSpace:
    """Корень агрегата. Состояние меняется только через методы."""

    id: str
    number: str
    tariff: HourlyTariff
    _current_session: Optional[ParkingSession] = field(default=None, repr=False)
    _closed_sessions: list[ParkingSession] = field(default_factory=list, repr=False)

    @classmethod
    def new(cls, number: str, tariff: HourlyTariff) -> "ParkingSpace":
        return cls(id=str(uuid4()), number=number, tariff=tariff)

    @property
    def is_free(self) -> bool:
        return self._current_session is None

    @property
    def current_session(self) -> Optional[ParkingSession]:
        return self._current_session

    @property
    def closed_sessions(self) -> tuple[ParkingSession, ...]:
        return tuple(self._closed_sessions)

    def open_session(self, entry_time: datetime) -> ParkingSession:
        # Инвариант 1: место не может быть занято повторно, пока сессия не закрыта.
        if self._current_session is not None:
            raise DomainInvariantViolation("Место занято: сначала закройте текущую сессию")

        session = ParkingSession(
            id=str(uuid4()),
            space_id=self.id,
            entry_time=entry_time,
        )
        self._current_session = session
        return session

    def close_session(self, exit_time: datetime) -> tuple[ParkingSession, Money]:
        # Инвариант 2: нельзя закрыть сессию, которой нет.
        if self._current_session is None:
            raise DomainInvariantViolation("Нет открытой сессии для закрытия")

        session = self._current_session

        # Инвариант 3: время выезда не раньше времени въезда.
        if exit_time < session.entry_time:
            raise DomainInvariantViolation("Время выезда не может быть раньше времени въезда")

        closed = replace(session, exit_time=exit_time)
        hours = self._billable_hours(session.entry_time, exit_time)
        cost = self.tariff.cost_for(hours)

        self._current_session = None
        self._closed_sessions.append(closed)
        return closed, cost

    @staticmethod
    def _billable_hours(entry: datetime, exit_: datetime) -> int:
        seconds = (exit_ - entry).total_seconds()
        if seconds <= 0:
            return 0
        # Округление вверх до полного часа.
        return int(seconds // 3600) + (1 if seconds % 3600 else 0)