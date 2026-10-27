from datetime import datetime
import threading
from datetime import datetime, timedelta

from domain.shared.errors import ClockMovedBackwards


class ShiftedClock:
    """Часы приложения: системное время плюс сдвиг. Назад переводить нельзя."""

    def __init__(self) -> None:
        self._offset = timedelta(0)
        self._lock = threading.Lock()

    def now(self) -> datetime:
        with self._lock:
            return datetime.now() + self._offset

    def set_to(self, target: datetime) -> datetime:
        with self._lock:
            current = datetime.now() + self._offset
            if target < current:
                raise ClockMovedBackwards(
                    f"Нельзя перевести часы назад: {target.isoformat()} < {current.isoformat()}"
                )
            self._offset = target - datetime.now()
            return target
            

class SystemClock:
    def now(self) -> datetime:
        return datetime.now()


class FixedClock:
    """Управляемые часы для демонстрации и тестов."""

    def __init__(self, current: datetime) -> None:
        self._current = current

    def now(self) -> datetime:
        return self._current

    def set(self, value: datetime) -> None:
        self._current = value