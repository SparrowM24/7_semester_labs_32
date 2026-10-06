"""Фабрика восстановления агрегата «Парковочное место»."""

from __future__ import annotations

from typing import Iterable

from domain.shared.value_objects import Money

from .aggregates import ParkingSpace
from .value_objects import HourlyTariff


def restore_parking_space(
    space_id: str,
    number: str,
    price_per_hour: float,
    current_session: dict | None,
    closed_sessions: Iterable[dict],
) -> ParkingSpace:
    space = ParkingSpace(
        id=space_id,
        number=number,
        tariff=HourlyTariff(Money(price_per_hour)),
    )

    for raw in closed_sessions:
        space.open_session(raw["entry_time"])
        space.close_session(raw["exit_time"])

    if current_session is not None:
        space.open_session(current_session["entry_time"])

    return space