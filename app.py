"""Веб-адаптер на Flask. Единственный модуль, который импортирует Flask."""

from __future__ import annotations

from dataclasses import asdict
from datetime import time
from typing import Any

from flask import Flask, jsonify, request

from application.booking_process import BookingProcess
from domain.employee.aggregates import Employee
from domain.meeting_room.aggregates import MeetingRoom
from domain.meeting_room.booking import BookingLifecycle
from domain.meeting_room.services import BookingService
from domain.meeting_room.value_objects import Capacity, OfficeHours
from domain.shared.errors import (
    ClockMovedBackwards, DomainError, DomainInvariantViolation,
    EntityNotFound, GatewayUnresolved, InvalidValueObject, TransitionNotAllowed,
)
from infrastructure.booking_repositories import (
    InMemoryBookingLifecycleRepository, InMemoryEmployeeRepository)
from infrastructure.clock import ShiftedClock
from infrastructure.meeting_room_repository import InMemoryMeetingRoomRepository

# Таблица 7: исключение -> (HTTP-код, код ошибки). Порядок важен: частные классы первыми.
ERROR_TABLE: list[tuple[type[Exception], int, str]] = [
    (TransitionNotAllowed, 409, "transition_not_allowed"),
    (ClockMovedBackwards, 422, "clock_moved_backwards"),
    (InvalidValueObject, 422, "invalid_value"),
    (DomainInvariantViolation, 422, "invariant_violation"),
    (EntityNotFound, 404, "not_found"),
    (GatewayUnresolved, 500, "gateway_unresolved"),
]


# ---------- вспомогательные функции разбора запроса ----------

def _body() -> dict[str, Any]:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _require(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise InvalidValueObject(f"Не передано поле «{key}»")
    return data[key]


def _parse_time(value: Any, field: str) -> time:
    try:
        return time.fromisoformat(str(value))
    except ValueError:
        raise InvalidValueObject(f"Поле «{field}» должно быть временем в формате ЧЧ:ММ")


def _booking_view(booking: BookingLifecycle) -> dict[str, Any]:
    return {
        "id": booking.id,
        "room_id": booking.room_id,
        "employee_id": booking.employee_id,
        "start": booking.interval.start.isoformat(),
        "end": booking.interval.end.isoformat(),
        "participants": booking.participants.value,
        "state": booking.state.name,
        "is_final": booking.is_finished,
        "available_events": list(booking.available_events),
        "events": [
            {"type": type(e).__name__,
             **{k: (v.isoformat() if isinstance(v, datetime) else v)
                for k, v in asdict(e).items()}}
            for e in booking.events
        ],
    }


# ---------- фабрика приложения ----------

def create_app() -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False

    # Часы, репозитории и сервис процесса создаются один раз при запуске.
    clock = ShiftedClock()
    rooms = InMemoryMeetingRoomRepository()
    employees = InMemoryEmployeeRepository()
    bookings = InMemoryBookingLifecycleRepository()
    process = BookingProcess(
        rooms=rooms,
        bookings=bookings,
        employees=employees,
        booking_service=BookingService(rooms, employees, clock),
        clock=clock,
    )

    def _booking(booking_id: str) -> BookingLifecycle:
        booking = bookings.get(booking_id)
        if booking is None:
            raise EntityNotFound(f"Бронирование {booking_id} не найдено")
        return booking

    # ----- общий обработчик исключений -----
    @app.errorhandler(DomainError)
    def handle_domain_error(exc: DomainError):
        for exc_type, status, code in ERROR_TABLE:
            if isinstance(exc, exc_type):
                return jsonify({"error": code, "message": str(exc)}), status
        return jsonify({"error": "domain_error", "message": str(exc)}), 500

    # ----- справочники (подготовка данных) -----
    @app.post("/rooms")
    def create_room():
        data = _body()
        room = MeetingRoom.new(
            str(_require(data, "name")),
            Capacity(_require(data, "capacity")),
            OfficeHours(_parse_time(_require(data, "opens_at"), "opens_at"),
                _parse_time(_require(data, "closes_at"), "closes_at")),
        )
        rooms.add(room)
        return jsonify({"id": room.id, "name": room.name}), 201

    @app.post("/employees")
    def create_employee():
        employee = Employee.new(str(_require(_body(), "name")))
        employees.add(employee)
        return jsonify({"id": employee.id, "name": employee.name}), 201

    # ----- бизнес-операции процесса -----
    @app.post("/bookings")
    def start_booking():
        data = _body()
        booking_id = process.start(
            room_id=str(_require(data, "room_id")),
            employee_id=str(_require(data, "employee_id")),
            start=_parse_dt(_require(data, "start"), "start"),
            end=_parse_dt(_require(data, "end"), "end"),
            participants=_require(data, "participants"),
            needs_service_order=bool(data.get("needs_service_order", False)),
        )
        return jsonify(_booking_view(_booking(booking_id))), 201

    @app.post("/bookings/<booking_id>/approval")
    def approve_booking(booking_id: str):
        approved = _require(_body(), "approved")
        if not isinstance(approved, bool):
            raise InvalidValueObject("Поле «approved» должно быть true или false")
        process.approve_booking(booking_id, approved)
        return jsonify(_booking_view(_booking(booking_id)))

    @app.post("/bookings/<booking_id>/service-order/confirm")
    def confirm_service_order(booking_id: str):
        process.confirm_service_order(booking_id)
        return jsonify(_booking_view(_booking(booking_id)))

    @app.post("/bookings/<booking_id>/cancel")
    def cancel_booking(booking_id: str):
        process.request_cancellation(booking_id)
        return jsonify(_booking_view(_booking(booking_id)))

    @app.post("/bookings/<booking_id>/check-in")
    def check_in(booking_id: str):
        process.record_check_in(booking_id)
        return jsonify(_booking_view(_booking(booking_id)))

    # ----- состояние сущности -----
    @app.get("/bookings/<booking_id>")
    def get_booking(booking_id: str):
        return jsonify(_booking_view(_booking(booking_id)))

    # ----- служебный маршрут: часы и таймеры -----
    @app.post("/internal/tick")
    def tick():
        data = _body()
        if data.get("now") is not None:
            clock.set_to(_parse_dt(data["now"], "now"))     # назад нельзя -> 422
        fired = process.tick_all()
        return jsonify({"now": clock.now().isoformat(), "fired": fired})

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000)