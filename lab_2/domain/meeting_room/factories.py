"""Фабрика восстановления агрегата из сохранённого состояния."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from domain.shared.value_objects import TimeInterval

from .aggregates import MeetingRoom
from .value_objects import Capacity, OfficeHours, ParticipantsCount


def restore_meeting_room(
    room_id: str,
    name: str,
    capacity_value: int,
    opens_at: datetime,
    closes_at: datetime,
    bookings: Iterable[dict],
) -> MeetingRoom:
    room = MeetingRoom(
        id=room_id,
        name=name,
        capacity=Capacity(capacity_value),
        office_hours=OfficeHours(opens_at=opens_at, closes_at=closes_at),
    )

    for raw in bookings:
        booking = room.book(
            TimeInterval(start=raw["start"], end=raw["end"]),
            ParticipantsCount(raw["participants"]),
        )
        if raw.get("is_cancelled"):
            room.cancel(booking.id)
    return room
