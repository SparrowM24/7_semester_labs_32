"""Агрегат «Переговорная комната»."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from uuid import uuid4

from domain.shared.errors import DomainInvariantViolation
from domain.shared.value_objects import TimeInterval

from .value_objects import Capacity, OfficeHours, ParticipantsCount


@dataclass(frozen=True)
class Booking:
    """Сущность брони внутри агрегата."""

    id: str
    room_id: str
    interval: TimeInterval
    participants: ParticipantsCount
    is_cancelled: bool = False


@dataclass
class MeetingRoom:
    """Корень агрегата. Состояние меняется только через методы."""

    id: str
    name: str
    capacity: Capacity
    office_hours: OfficeHours
    _bookings: List[Booking] = field(default_factory=list, repr=False)

    @classmethod
    def new(cls, name: str, capacity: Capacity, office_hours: OfficeHours) -> "MeetingRoom":
        return cls(id=str(uuid4()), name=name, capacity=capacity, office_hours=office_hours)

    @property
    def bookings(self) -> tuple[Booking, ...]:
        return tuple(self._bookings)

    def book(self, interval: TimeInterval, participants: ParticipantsCount) -> Booking:
        # Инвариант 1: число участников не превышает вместимость.
        if participants.value > self.capacity.value:
            raise DomainInvariantViolation(
                f"Число участников ({participants.value}) превышает "
                f"вместимость комнаты ({self.capacity.value})"
            )

        # Инвариант 2: бронь не выходит за часы работы офиса.
        if not self.office_hours.contains(interval.start, interval.end):
            raise DomainInvariantViolation("Бронь выходит за пределы часов работы офиса")

        # Инвариант 3: брони одной комнаты не пересекаются.
        for existing in self._bookings:
            if existing.is_cancelled:
                continue
            if existing.interval.overlaps(interval):
                raise DomainInvariantViolation(
                    "Бронь пересекается с существующей бронью этой комнаты"
                )

        booking = Booking(
            id=str(uuid4()),
            room_id=self.id,
            interval=interval,
            participants=participants,
        )
        self._bookings.append(booking)
        return booking

    def cancel(self, booking_id: str) -> None:
        for index, booking in enumerate(self._bookings):
            if booking.id == booking_id:
                if booking.is_cancelled:
                    raise DomainInvariantViolation("Бронь уже отменена")
                self._bookings[index] = Booking(
                    id=booking.id,
                    room_id=booking.room_id,
                    interval=booking.interval,
                    participants=booking.participants,
                    is_cancelled=True,
                )
                return
        raise DomainInvariantViolation("Бронь не найдена в этой комнате")