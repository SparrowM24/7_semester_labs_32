"""Прикладной сервис: процесс «Бронирование переговорной комнаты» (BPMN)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional, Tuple

from domain.employee.aggregates import Employee, next_month_start
from domain.employee.repositories import EmployeeRepository
from domain.meeting_room import events as ev
from domain.meeting_room.aggregates import MeetingRoom
from domain.meeting_room.booking import BookingLifecycle
from domain.meeting_room.booking_states import AwaitingCheckIn, Confirmed, PendingApproval
from domain.meeting_room.repositories import BookingLifecycleRepository, MeetingRoomRepository
from domain.meeting_room.services import BookingService
from domain.meeting_room.value_objects import ParticipantsCount
from domain.shared.clock import Clock
from domain.shared.errors import EntityNotFound, GatewayUnresolved
from domain.shared.value_objects import TimeInterval

Branch = Tuple[Callable[[], bool], str]


def exclusive_gateway(name: str, branches: List[Branch], default: Optional[str] = None) -> str:
    """Исключающий шлюз: первая выполненная ветка; иначе поток по умолчанию; иначе ошибка."""
    for predicate, label in branches:
        if predicate():
            return label
    if default is not None:
        return default
    raise GatewayUnresolved(name)


@dataclass
class BookingProcess:
    rooms: MeetingRoomRepository
    bookings: BookingLifecycleRepository
    employees: EmployeeRepository
    booking_service: BookingService
    clock: Clock

    # ===================== запуск процесса =====================
    def start(self, room_id: str, employee_id: str, start: datetime, end: datetime,
              participants: int, needs_service_order: bool = False) -> str:
        booking = BookingLifecycle(
            room_id, employee_id, TimeInterval(start, end),
            ParticipantsCount(participants), needs_service_order,
        )
        booking.publish(ev.BookingRequested(booking.id, self.clock.now()))
        self.bookings.add(booking)

        room = self.check_room_availability(booking)
        branch = exclusive_gateway("Комната свободна?", [
            (lambda: room.is_free(booking.interval), "free"),
            (lambda: not room.is_free(booking.interval), "busy"),
        ])
        if branch == "busy":
            self.reject_request(booking)                      # конец: комната занята
            return booking.id

        branch = exclusive_gateway("Нужно согласование?", [
            (booking.needs_approval, "yes"),
            (lambda: not booking.needs_approval(), "no"),
        ])
        if branch == "yes":
            self.submit_for_approval(booking)                 # ждём решения или таймера
        else:
            booking.check_no_approval()
            self._prepare_booking(booking)
        return booking.id

    # ===================== задачи схемы =====================
    def check_room_availability(self, booking: BookingLifecycle) -> MeetingRoom:
        room = self.rooms.get(booking.room_id)
        if room is None:
            raise EntityNotFound(f"Комната {booking.room_id} не найдена")
        return room

    def reject_request(self, booking: BookingLifecycle) -> None:
        booking.check_busy()
        booking.publish(ev.BookingRejected(booking.id, self.clock.now(), "комната занята"))
        self.bookings.save(booking)

    def submit_for_approval(self, booking: BookingLifecycle) -> None:
        now = self.clock.now()
        booking.check_needs_approval(now)
        booking.publish(ev.ApprovalRequested(booking.id, now, booking.approval_deadline))
        self.bookings.save(booking)

    def approve_booking(self, booking_id: str, approved: bool) -> None:
        """Задача человека «Согласовать бронирование»: принимает решение руководителя."""
        booking = self._get(booking_id)
        branch = exclusive_gateway("Согласовано?", [
            (lambda: approved, "yes"),
            (lambda: not approved, "no"),
        ])
        if branch == "no":
            booking.reject()
            booking.publish(ev.BookingRejected(booking.id, self.clock.now(),
                                               "отклонено руководителем"))
            self.bookings.save(booking)
            return                                            # конец: отклонена руководителем
        booking.approve()
        self._prepare_booking(booking)

    def reject_automatically(self, booking: BookingLifecycle) -> None:
        booking.publish(ev.BookingRejected(booking.id, self.clock.now(),
                                           "нет ответа руководителя"))
        self.bookings.save(booking)

    def confirm_room_booking(self, booking: BookingLifecycle) -> None:
        room_booking_id = self.booking_service.book_room(
            booking.room_id, booking.interval.start, booking.interval.end,
            booking.participants.value, booking.employee_id,
        )
        booking.attach_room_booking(room_booking_id)

    def send_request_to_admin(self, booking: BookingLifecycle) -> None:
        booking.publish(ev.ServiceOrderRequested(booking.id, self.clock.now()))

    def confirm_service_order(self, booking_id: str) -> None:
        """Задача человека «Подтвердить заказ оборудования и кейтеринга»."""
        booking = self._get(booking_id)
        booking.mark_order_confirmed()
        self._join_branches(booking)

    def notify_employee_ready(self, booking: BookingLifecycle) -> None:
        booking.publish(ev.BookingReady(booking.id, self.clock.now()))

    def request_cancellation(self, booking_id: str) -> None:
        """Сообщение «Отмена брони». Допустимо только до начала встречи (инвариант состояния)."""
        booking = self._get(booking_id)
        booking.cancel(self.clock.now())
        self.release_room(booking)                            # конец: бронь отменена

    def release_room(self, booking: BookingLifecycle) -> None:
        room = self.check_room_availability(booking)
        room.cancel(booking.room_booking_id)                  # метод лабораторной №2
        self.rooms.save(room)
        booking.publish(ev.BookingCancelledNotice(booking.id, self.clock.now()))
        self.bookings.save(booking)

    def wait_for_check_in(self, booking: BookingLifecycle) -> datetime:
        """Задача «Ожидать отметки сотрудника»: возвращает крайний срок отметки."""
        return booking.interval.start + booking.CHECK_IN_PERIOD

    def record_check_in(self, booking_id: str) -> None:
        """Сотрудник отметился: конец «Встреча состоялась»."""
        booking = self._get(booking_id)
        booking.check_in()
        self.bookings.save(booking)

    def remove_booking_and_release_room(self, booking: BookingLifecycle) -> None:
        room = self.check_room_availability(booking)
        room.cancel(booking.room_booking_id)
        self.rooms.save(room)

    def register_no_show(self, booking: BookingLifecycle, employee: Employee) -> int:
        count = employee.register_no_show(self.clock.now())
        booking.publish(ev.NoShowRecorded(booking.id, self.clock.now(), employee.id, count))
        self.employees.save(employee)
        return count

    def ban_large_rooms(self, booking: BookingLifecycle, employee: Employee) -> None:
        now = self.clock.now()
        until = next_month_start(now)
        employee.ban_large_rooms(until)
        booking.publish(ev.LargeRoomsBanned(booking.id, now, employee.id, until))
        self.employees.save(employee)

    # ===================== события таймера =====================
    def on_approval_timeout(self, booking_id: str, now: datetime) -> None:
        """Граничный таймер «24 часа» (прерывающий)."""
        booking = self._get(booking_id)
        booking.on_approval_timeout(now)
        self.reject_automatically(booking)                    # конец: нет ответа руководителя

    def on_booking_start(self, booking_id: str, now: datetime) -> None:
        """Промежуточный таймер «Время начала встречи»."""
        booking = self._get(booking_id)
        booking.on_meeting_start(now)
        self.wait_for_check_in(booking)
        self.bookings.save(booking)

    def on_checkin_timeout(self, booking_id: str, now: datetime) -> None:
        """Граничный таймер «15 минут» (прерывающий)."""
        booking = self._get(booking_id)
        employee = self.employees.get(booking.employee_id)
        if employee is None:
            raise EntityNotFound(f"Сотрудник {booking.employee_id} не найден")

        branch = exclusive_gateway("Неявок за месяц три или больше?", [
            (lambda: employee.would_reach_limit(now), "ban"),
            (lambda: not employee.would_reach_limit(now), "no_ban"),
        ])
        projected = employee.no_shows_in_month(now) + 1
        booking.on_checkin_timeout(now, projected)            # конечное состояние

        self.remove_booking_and_release_room(booking)
        self.register_no_show(booking, employee)
        if branch == "ban":
            self.ban_large_rooms(booking, employee)
        self.bookings.save(booking)

    def tick(self, booking_id: str) -> bool:
        """Запускает все наступившие таймеры сущности. Время берётся только из Clock."""
        fired = False
        while self._fire_due(booking_id):
            fired = True
        return fired

    def tick_all(self) -> list[str]:
        """Проверяет все бронирования, возвращает идентификаторы тех, у кого сработал таймер."""
        return [b.id for b in self.bookings.all() if self.tick(b.id)]

    def _fire_due(self, booking_id: str) -> bool:
        now = self.clock.now()
        booking = self._get(booking_id)
        state = booking.state
        if isinstance(state, PendingApproval) and now >= booking.approval_deadline:
            self.on_approval_timeout(booking_id, now)
        elif isinstance(state, Confirmed) and now >= booking.interval.start:
            self.on_booking_start(booking_id, now)
        elif isinstance(state, AwaitingCheckIn) and now >= self.wait_for_check_in(booking):
            self.on_checkin_timeout(booking_id, now)
        else:
            return False
        return True
            
    # ===================== внутренние шаги =====================
    def _prepare_booking(self, booking: BookingLifecycle) -> None:
        """Шлюз «Нужны оборудование или кейтеринг?» и параллельный блок."""
        branch = exclusive_gateway("Нужны оборудование или кейтеринг?", [
            (booking.has_service_order, "yes"),
            (lambda: not booking.has_service_order(), "no"),
        ])
        # Параллельные ветви выполняются последовательно:
        self.confirm_room_booking(booking)                    # ветвь 1
        if branch == "yes":
            self.send_request_to_admin(booking)               # ветвь 2 (ожидает человека)
        self._join_branches(booking)

    def _join_branches(self, booking: BookingLifecycle) -> None:
        """Параллельное слияние: дальше только когда завершены все ветви."""
        if booking.all_branches_done():
            booking.confirm_all()
            self.notify_employee_ready(booking)
        else:
            booking.confirm_partial()
        self.bookings.save(booking)

    def _get(self, booking_id: str) -> BookingLifecycle:
        booking = self.bookings.get(booking_id)
        if booking is None:
            raise EntityNotFound(f"Бронирование {booking_id} не найдено")
        return booking