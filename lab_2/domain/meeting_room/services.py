"""Доменный сервис бронирования. Затрагивает репозитории и агрегаты."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.employee.repositories import EmployeeRepository
from domain.shared.clock import Clock
from domain.shared.errors import DomainInvariantViolation, EntityNotFound
from domain.shared.value_objects import TimeInterval

from .repositories import MeetingRoomRepository
from .value_objects import ParticipantsCount

LARGE_ROOM_CAPACITY = 10


@dataclass
class BookingService:
    rooms: MeetingRoomRepository
    employees: Optional[EmployeeRepository] = None
    clock: Optional[Clock] = None

    def book_room(self, room_id: str, start: datetime, end: datetime,
                  participants: int, employee_id: Optional[str] = None) -> str:
        room = self.rooms.get(room_id)
        if room is None:
            raise EntityNotFound(f"Комната {room_id} не найдена")

        if employee_id is not None and self.employees and self.clock:
            employee = self.employees.get(employee_id)
            if employee is None:
                raise EntityNotFound(f"Сотрудник {employee_id} не найден")
            if (room.capacity.value > LARGE_ROOM_CAPACITY
                    and employee.is_banned_from_large_rooms(self.clock.now())):
                raise DomainInvariantViolation(
                    "Бронирование крупных комнат запрещено сотруднику до конца месяца"
                )

        booking = room.book(TimeInterval(start=start, end=end),
                            ParticipantsCount(participants))
        self.rooms.save(room)
        return booking.id