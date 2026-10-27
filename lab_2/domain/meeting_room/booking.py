"""Агрегат «Бронирование»: жизненный цикл по паттерну «Состояние»."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Tuple
from uuid import uuid4

from domain.shared.value_objects import TimeInterval

from .booking_states import BookingState, Submitted
from .events import DomainEvent
from .value_objects import ParticipantsCount

APPROVAL_PARTICIPANTS_LIMIT = 10
APPROVAL_DURATION_LIMIT = timedelta(hours=4)


class BookingLifecycle:
    APPROVAL_PERIOD = timedelta(hours=24)
    CHECK_IN_PERIOD = timedelta(minutes=15)

    def __init__(self, room_id: str, employee_id: str, interval: TimeInterval,
                 participants: ParticipantsCount, needs_service_order: bool = False,
                 booking_id: Optional[str] = None) -> None:
        self.id = booking_id or str(uuid4())
        self.room_id = room_id
        self.employee_id = employee_id
        self.interval = interval
        self.participants = participants
        self._needs_service_order = needs_service_order
        self._state: BookingState = Submitted()
        self._approval_deadline: Optional[datetime] = None
        self._room_booking_id: Optional[str] = None
        self._room_confirmed = False
        self._order_confirmed = False
        self._events: list[DomainEvent] = []

    # ---- чтение (сеттеров нет) ----
    @property
    def state(self) -> BookingState:
        return self._state

    @property
    def available_events(self) -> Tuple[str, ...]:
        return tuple(sorted(self._state.allowed_events))

    @property
    def is_finished(self) -> bool:
        return self._state.is_final

    @property
    def approval_deadline(self) -> Optional[datetime]:
        return self._approval_deadline

    @property
    def room_booking_id(self) -> Optional[str]:
        return self._room_booking_id

    @property
    def events(self) -> Tuple[DomainEvent, ...]:
        return tuple(self._events)

    # ---- журнал доменных событий ----
    def publish(self, event: DomainEvent) -> None:
        self._events.append(event)

    # ---- предикаты шлюзов ----
    def needs_approval(self) -> bool:
        return (self.participants.value > APPROVAL_PARTICIPANTS_LIMIT
                or self.interval.end - self.interval.start > APPROVAL_DURATION_LIMIT)

    def has_service_order(self) -> bool:
        return self._needs_service_order

    def all_branches_done(self) -> bool:
        """Условие параллельного слияния."""
        return self._room_confirmed and (self._order_confirmed or not self._needs_service_order)

    # ---- данные ветвей ----
    def attach_room_booking(self, room_booking_id: str) -> None:
        self._room_booking_id = room_booking_id
        self._room_confirmed = True

    def mark_order_confirmed(self) -> None:
        self._order_confirmed = True

    # ---- события: единственный способ сменить состояние ----
    def check_busy(self) -> None:
        self._state = self._state.check_busy()

    def check_needs_approval(self, now: datetime) -> None:
        self._state = self._state.check_needs_approval()
        self._approval_deadline = now + self.APPROVAL_PERIOD

    def check_no_approval(self) -> None:
        self._state = self._state.check_no_approval()

    def approve(self) -> None:
        self._state = self._state.approve()

    def reject(self) -> None:
        self._state = self._state.reject()

    def on_approval_timeout(self, now: datetime) -> None:
        self._state = self._state.approval_timeout(now, self._approval_deadline or now)

    def confirm_partial(self) -> None:
        self._state = self._state.confirm_partial()

    def confirm_all(self) -> None:
        self._state = self._state.confirm_all()

    def cancel(self, now: datetime) -> None:
        self._state = self._state.cancel(now, self.interval.start)

    def on_meeting_start(self, now: datetime) -> None:
        self._state = self._state.start_meeting(now, self.interval.start)

    def check_in(self) -> None:
        self._state = self._state.check_in()

    def on_checkin_timeout(self, now: datetime, no_shows_in_month: int) -> None:
        if no_shows_in_month >= 3:
            self._state = self._state.no_show_ban(now, self.interval.start, no_shows_in_month)
        else:
            self._state = self._state.no_show(now, self.interval.start, no_shows_in_month)