class ClockMovedBackwards(DomainError):
    """Попытка перевести часы приложения назад."""

class GatewayUnresolved(DomainError):
    """Ни одно условие исключающего шлюза не выполнено, потока по умолчанию нет."""

    def __init__(self, gateway: str) -> None:
        self.gateway = gateway
        super().__init__(f"Шлюз «{gateway}»: ни одно условие не выполнено")

        
class TransitionNotAllowed(DomainError):
    """Событие недопустимо в текущем состоянии."""

    def __init__(self, state: str, event: str) -> None:
        self.state = state
        self.event = event
        super().__init__(f"В состоянии «{state}» событие «{event}» недопустимо")


class DomainError(Exception):
    """Базовое исключение домена. Всё, что связано с правилами, наследуется от него."""


class InvalidValueObject(DomainError):
    """Объект-значение создан с недопустимыми данными."""


class DomainInvariantViolation(DomainError):
    """Попытка нарушить инвариант агрегата."""


class EntityNotFound(DomainError):
    """Сущность не найдена в репозитории."""


