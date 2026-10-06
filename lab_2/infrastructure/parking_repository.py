"""In-memory реализация порта ParkingSpaceRepository."""

from __future__ import annotations

from typing import Dict, Optional

from domain.parking.aggregates import ParkingSpace


class InMemoryParkingSpaceRepository:
    def __init__(self) -> None:
        self._storage: Dict[str, ParkingSpace] = {}

    def add(self, space: ParkingSpace) -> None:
        self._storage[space.id] = space

    def get(self, space_id: str) -> Optional[ParkingSpace]:
        return self._storage.get(space_id)

    def save(self, space: ParkingSpace) -> None:
        self._storage[space.id] = space