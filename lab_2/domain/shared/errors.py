"""Иерархия доменных исключений. Чистый Python, без инфраструктуры."""


class DomainError(Exception):
    """Базовое исключение домена. Всё, что связано с правилами, наследуется от него."""


class InvalidValueObject(DomainError):
    """Объект-значение создан с недопустимыми данными."""


class DomainInvariantViolation(DomainError):
    """Попытка нарушить инвариант агрегата."""


class EntityNotFound(DomainError):
    """Сущность не найдена в репозитории."""

