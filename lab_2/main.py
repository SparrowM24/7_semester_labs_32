"""Демонстрация доменной модели. Запуск: python main.py"""

from datetime import datetime, time

from domain.meeting_room.aggregates import MeetingRoom
from domain.meeting_room.factories import restore_meeting_room
from domain.meeting_room.services import BookingService
from domain.meeting_room.value_objects import Capacity, OfficeHours, ParticipantsCount
from domain.parking.aggregates import ParkingSpace
from domain.parking.factories import restore_parking_space
from domain.parking.services import ParkingService
from domain.parking.value_objects import HourlyTariff
from domain.shared.errors import DomainInvariantViolation, InvalidValueObject
from domain.shared.value_objects import Money
from infrastructure.meeting_room_repository import InMemoryMeetingRoomRepository
from infrastructure.parking_repository import InMemoryParkingSpaceRepository
from application.booking_process import BookingProcess
from domain.employee.aggregates import Employee
from infrastructure.booking_repositories import (
    InMemoryBookingLifecycleRepository, InMemoryEmployeeRepository)
from infrastructure.clock import FixedClock


def demo_booking_process() -> None:
    print("=== Процесс бронирования ===")
    clock = FixedClock(datetime(2026, 1, 1, 8, 0))
    rooms = InMemoryMeetingRoomRepository()
    employees = InMemoryEmployeeRepository()
    bookings = InMemoryBookingLifecycleRepository()

    room = MeetingRoom.new("Альфа", Capacity(10), OfficeHours(
        time(9, 0), time(18, 0)))
    rooms.add(room)
    emp = Employee.new("Иванов")
    emp.register_no_show(datetime(2026, 1, 1, 0, 0))
    emp.register_no_show(datetime(2026, 1, 1, 0, 0))   # уже две неявки в месяце
    employees.add(emp)

    process = BookingProcess(
        rooms, bookings, employees,
        BookingService(rooms, employees, clock), clock)

    # 5 часов > 4 часов: нужно согласование; заказан кейтеринг
    bid = process.start(room.id, emp.id,
                        datetime(2026, 1, 1, 10, 0), datetime(2026, 1, 1, 15, 0),
                        participants=5, needs_service_order=True)
    b = bookings.get(bid)
    print(b.state.name)                      # На согласовании

    process.approve_booking(bid, approved=True)
    print(b.state.name)                      # Оформляется (ждём заказ)
    process.confirm_service_order(bid)
    print(b.state.name)                      # Подтверждена

    clock.set(datetime(2026, 1, 1, 10, 0))
    process.tick(bid)                        # время начала встречи
    print(b.state.name)                      # Ожидает отметки

    clock.set(datetime(2026, 1, 1, 10, 15))
    process.tick(bid)                        # неявка, третья за месяц
    print(b.state.name, "| финальное:", b.is_finished)
    print([type(e).__name__ for e in b.events])


def demo_meeting_room() -> None:
    print("=== Переговорная комната ===")
    office = OfficeHours(opens_at=time(9, 0), closes_at=time(18, 0))
    room = MeetingRoom.new("Альфа", Capacity(10), office)

    rooms = InMemoryMeetingRoomRepository()
    rooms.add(room)
    service = BookingService(rooms)

    booking_id = service.book_room(
        room.id,
        datetime(2026, 1, 1, 10, 0),
        datetime(2026, 1, 1, 11, 0),
        participants=5,
    )
    print("Создана бронь:", booking_id)

    try:
        service.book_room(
            room.id,
            datetime(2026, 1, 1, 10, 30),
            datetime(2026, 1, 1, 11, 30),
            participants=5,
        )
    except DomainInvariantViolation as exc:
        print("Ожидаемое нарушение (пересечение):", exc)

    try:
        service.book_room(
            room.id,
            datetime(2026, 1, 1, 12, 0),
            datetime(2026, 1, 1, 13, 0),
            participants=20,
        )
    except DomainInvariantViolation as exc:
        print("Ожидаемое нарушение (вместимость):", exc)

    try:
        ParticipantsCount(0)
    except InvalidValueObject as exc:
        print("Ожидаемое нарушение VO:", exc)


def demo_parking() -> None:
    print("=== Парковка ===")
    space = ParkingSpace.new("A-1", HourlyTariff(Money(100)))

    spaces = InMemoryParkingSpaceRepository()
    spaces.add(space)
    service = ParkingService(spaces)

    service.open_session(space.id, datetime(2026, 1, 1, 10, 0))
    try:
        service.open_session(space.id, datetime(2026, 1, 1, 10, 30))
    except DomainInvariantViolation as exc:
        print("Ожидаемое нарушение (место занято):", exc)

    cost = service.close_session(space.id, datetime(2026, 1, 1, 11, 30))
    print("Стоимость парковки:", cost)

    try:
        service.close_session(space.id, datetime(2026, 1, 1, 12, 0))
    except DomainInvariantViolation as exc:
        print("Ожидаемое нарушение (нет сессии):", exc)


def demo_factories() -> None:
    print("=== Восстановление из состояния ===")
    room = restore_meeting_room(
        room_id="room-1", name="Бета", capacity_value=8,
        opens_at=time(9, 0), closes_at=time(18, 0),
        bookings=[
            {
                "start": datetime(2026, 1, 1, 10, 0),
                "end": datetime(2026, 1, 1, 11, 0),
                "participants": 4,
                "is_cancelled": False
            }
        ],
    )
    print("Комната восстановлена, броней:", len(room.bookings))

    space = restore_parking_space(
        space_id="space-1",
        number="B-2",
        price_per_hour=150,
        current_session=None,
        closed_sessions=[
            {
                "entry_time": datetime(2026, 1, 1, 8, 0),
                "exit_time": datetime(2026, 1, 1, 9, 30),
            },
        ],
    )
    print("Место восстановлено, закрытых сессий:", len(space.closed_sessions))


if __name__ == "__main__":
    demo_meeting_room()
    demo_parking()
    demo_factories()
    demo_booking_process()