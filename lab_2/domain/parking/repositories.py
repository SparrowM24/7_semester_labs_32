"""Порт репозитория для агрегата «Парковочное место»."""

from __future__ import annotations

from typing import Optional, Protocol

from .aggregates import ParkingSpace


class ParkingSpaceRepository(Protocol):
    def add(self, space: ParkingSpace) -> None: ...
    def get(self, space_id: str) -> Optional[ParkingSpace]: ...
    def save(self, space: ParkingSpace) -> None: ...
