"""Доменный сервис бронирования. Затрагивает репозиторий и агрегат."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.shared.errors import EntityNotFound
from domain.shared.value_objects import TimeInterval

from .repositories import MeetingRoomRepository
from .value_objects import ParticipantsCount


@dataclass
class BookingService:
    rooms: MeetingRoomRepository

    def book_room(
        self,
        room_id: str,
        start: datetime,
        end: datetime,
        participants: int,
    ) -> str:
        room = self.rooms.get(room_id)
        if room is None:
            raise EntityNotFound(f"Комната {room_id} не найдена")

        booking = room.book(
            TimeInterval(start=start, end=end),
            ParticipantsCount(participants),
        )
        self.rooms.save(room)
        return booking.id