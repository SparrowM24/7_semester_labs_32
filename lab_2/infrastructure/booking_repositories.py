from typing import Dict, Optional

from domain.employee.aggregates import Employee
from domain.meeting_room.booking import BookingLifecycle


class InMemoryBookingLifecycleRepository:
    def __init__(self) -> None:
        self._storage: Dict[str, BookingLifecycle] = {}
    
    def all(self) -> list[BookingLifecycle]:
        return list(self._storage.values())

    def add(self, booking: BookingLifecycle) -> None:
        self._storage[booking.id] = booking

    def get(self, booking_id: str) -> Optional[BookingLifecycle]:
        return self._storage.get(booking_id)

    def save(self, booking: BookingLifecycle) -> None:
        self._storage[booking.id] = booking

    
class InMemoryEmployeeRepository:
    def __init__(self) -> None:
        self._storage: Dict[str, Employee] = {}

    def add(self, employee: Employee) -> None:
        self._storage[employee.id] = employee

    def get(self, employee_id: str) -> Optional[Employee]:
        return self._storage.get(employee_id)

    def save(self, employee: Employee) -> None:
        self._storage[employee.id] = employee