"""Порт репозитория для агрегата «Переговорная комната»."""

from __future__ import annotations

from typing import Optional, Protocol

from .aggregates import MeetingRoom


class MeetingRoomRepository(Protocol):
    def add(self, room: MeetingRoom) -> None: ...
    def get(self, room_id: str) -> Optional[MeetingRoom]: ...
    def save(self, room: MeetingRoom) -> None: ...