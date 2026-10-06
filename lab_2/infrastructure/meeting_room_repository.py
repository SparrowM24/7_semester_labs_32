"""In-memory реализация порта MeetingRoomRepository."""

from __future__ import annotations

from typing import Dict, Optional

from domain.meeting_room.aggregates import MeetingRoom


class InMemoryMeetingRoomRepository:
    def __init__(self) -> None:
        self._storage: Dict[str, MeetingRoom] = {}

    def add(self, room: MeetingRoom) -> None:
        self._storage[room.id] = room

    def get(self, room_id: str) -> Optional[MeetingRoom]:
        return self._storage.get(room_id)

    def save(self, room: MeetingRoom) -> None:
        self._storage[room.id] = room