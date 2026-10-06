"""Доменный сервис парковки."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.shared.errors import EntityNotFound

from .repositories import ParkingSpaceRepository


@dataclass
class ParkingService:
    spaces: ParkingSpaceRepository

    def open_session(self, space_id: str, entry_time: datetime) -> str:
        space = self.spaces.get(space_id)
        if space is None:
            raise EntityNotFound(f"Место {space_id} не найдено")
        session = space.open_session(entry_time)
        self.spaces.save(space)
        return session.id

    def close_session(self, space_id: str, exit_time: datetime) -> float:
        space = self.spaces.get(space_id)
        if space is None:
            raise EntityNotFound(f"Место {space_id} не найдено")
        _, cost = space.close_session(exit_time)
        self.spaces.save(space)
        return cost.amount
