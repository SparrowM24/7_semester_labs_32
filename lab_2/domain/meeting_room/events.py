"""Сообщения между участниками процесса: неизменяемые доменные события."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DomainEvent:
    booking_id: str
    occurred_at: datetime


@dataclass(frozen=True)
class BookingRequested(DomainEvent):
    pass


@dataclass(frozen=True)
class ApprovalRequested(DomainEvent):       # сообщение руководителю
    deadline: datetime


@dataclass(frozen=True)
class ServiceOrderRequested(DomainEvent):   # заявка администратору
    pass


@dataclass(frozen=True)
class BookingRejected(DomainEvent):         # отказ сотруднику
    reason: str


@dataclass(frozen=True)
class BookingReady(DomainEvent):            # уведомление о готовности
    pass


@dataclass(frozen=True)
class BookingCancelledNotice(DomainEvent):
    pass


@dataclass(frozen=True)
class NoShowRecorded(DomainEvent):
    employee_id: str
    no_shows_in_month: int


@dataclass(frozen=True)
class LargeRoomsBanned(DomainEvent):
    employee_id: str
    until: datetime