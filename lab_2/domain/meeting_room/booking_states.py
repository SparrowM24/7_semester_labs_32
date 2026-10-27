"""Паттерн «Состояние» для жизненного цикла бронирования."""

from __future__ import annotations

from datetime import datetime
from typing import FrozenSet

from domain.shared.errors import DomainInvariantViolation, TransitionNotAllowed

# Названия событий (13 событий таблицы переходов)
CHECK_BUSY = "проверить (занята)"
CHECK_NEEDS_APPROVAL = "проверить (свободна, нужно согласование)"
CHECK_NO_APPROVAL = "проверить (свободна, не нужно)"
APPROVE = "согласовать"
REJECT = "отклонить"
APPROVAL_TIMEOUT = "истечь 24 часа"
CONFIRM_PARTIAL = "подтвердить (не всё)"
CONFIRM_ALL = "подтвердить (всё)"
CANCEL = "отменить бронь"
START_MEETING = "начать встречу"
CHECK_IN = "отметиться"
NO_SHOW = "истечь 15 мин (неявок < 3)"
NO_SHOW_BAN = "истечь 15 мин (неявок ≥ 3)"


class BookingState:
    """Базовое состояние. Все события по умолчанию запрещены."""

    name: str = ""
    is_final: bool = False
    allowed_events: FrozenSet[str] = frozenset()

    def _deny(self, event: str):
        raise TransitionNotAllowed(self.name, event)

    def check_busy(self) -> "BookingState":
        return self._deny(CHECK_BUSY)

    def check_needs_approval(self) -> "BookingState":
        return self._deny(CHECK_NEEDS_APPROVAL)

    def check_no_approval(self) -> "BookingState":
        return self._deny(CHECK_NO_APPROVAL)

    def approve(self) -> "BookingState":
        return self._deny(APPROVE)

    def reject(self) -> "BookingState":
        return self._deny(REJECT)

    def approval_timeout(self, now: datetime, deadline: datetime) -> "BookingState":
        return self._deny(APPROVAL_TIMEOUT)

    def confirm_partial(self) -> "BookingState":
        return self._deny(CONFIRM_PARTIAL)

    def confirm_all(self) -> "BookingState":
        return self._deny(CONFIRM_ALL)

    def cancel(self, now: datetime, starts_at: datetime) -> "BookingState":
        return self._deny(CANCEL)

    def start_meeting(self, now: datetime, starts_at: datetime) -> "BookingState":
        return self._deny(START_MEETING)

    def check_in(self) -> "BookingState":
        return self._deny(CHECK_IN)

    def no_show(self, now: datetime, starts_at: datetime,
                no_shows_in_month: int) -> "BookingState":
        return self._deny(NO_SHOW)

    def no_show_ban(self, now: datetime, starts_at: datetime,
                    no_shows_in_month: int) -> "BookingState":
        return self._deny(NO_SHOW_BAN)

    def __repr__(self) -> str:
        return f"<{self.name}>"


# ---------- Конечные состояния (событий нет) ----------

class RejectedBusy(BookingState):          # S2
    name = "Отклонена: комната занята"
    is_final = True


class RejectedNoReply(BookingState):       # S4
    name = "Отклонена: нет ответа руководителя"
    is_final = True


class RejectedByManager(BookingState):     # S5
    name = "Отклонена руководителем"
    is_final = True


class Cancelled(BookingState):             # S8
    name = "Отменена"
    is_final = True


class Held(BookingState):                  # S10
    name = "Состоялась"
    is_final = True


class NoShow(BookingState):                # S11
    name = "Снята: неявка"
    is_final = True


class NoShowBanned(BookingState):          # S12
    name = "Снята: неявка, крупные комнаты заблокированы"
    is_final = True


# ---------- Нефинальные состояния ----------

class Submitted(BookingState):             # S1, начальное
    name = "Подана"
    allowed_events = frozenset({CHECK_BUSY, CHECK_NEEDS_APPROVAL, CHECK_NO_APPROVAL})

    def check_busy(self) -> BookingState:
        return RejectedBusy()

    def check_needs_approval(self) -> BookingState:
        return PendingApproval()

    def check_no_approval(self) -> BookingState:
        return Processing()


class PendingApproval(BookingState):       # S3
    name = "На согласовании"
    allowed_events = frozenset({APPROVE, REJECT, APPROVAL_TIMEOUT})

    def approve(self) -> BookingState:
        return Processing()

    def reject(self) -> BookingState:
        return RejectedByManager()

    def approval_timeout(self, now: datetime, deadline: datetime) -> BookingState:
        # Инвариант: таймер срабатывает не раньше истечения срока согласования.
        if now < deadline:
            raise DomainInvariantViolation("Срок согласования ещё не истёк")
        return RejectedNoReply()


class Processing(BookingState):            # S6
    name = "Оформляется"
    allowed_events = frozenset({CONFIRM_PARTIAL, CONFIRM_ALL})

    def confirm_partial(self) -> BookingState:
        return Processing()                # ждём вторую ветку (комната или заказ)

    def confirm_all(self) -> BookingState:
        return Confirmed()


class Confirmed(BookingState):             # S7
    name = "Подтверждена"
    allowed_events = frozenset({CANCEL, START_MEETING})

    def cancel(self, now: datetime, starts_at: datetime) -> BookingState:
        # Инвариант: отменить можно только до начала встречи.
        if now >= starts_at:
            raise DomainInvariantViolation("Нельзя отменить бронь после начала встречи")
        return Cancelled()

    def start_meeting(self, now: datetime, starts_at: datetime) -> BookingState:
        if now < starts_at:
            raise DomainInvariantViolation("Встреча ещё не началась")
        return AwaitingCheckIn()


class AwaitingCheckIn(BookingState):       # S9
    name = "Ожидает отметки"
    allowed_events = frozenset({CHECK_IN, NO_SHOW, NO_SHOW_BAN})

    def check_in(self) -> BookingState:
        return Held()

    def no_show(self, now: datetime, starts_at: datetime,
                no_shows_in_month: int) -> BookingState:
        self._check_timeout(now, starts_at)
        # Инвариант: ветка «без блокировки» только при числе неявок меньше трёх.
        if no_shows_in_month >= 3:
            raise DomainInvariantViolation("Неявок за месяц три или больше: нужна блокировка")
        return NoShow()

    def no_show_ban(self, now: datetime, starts_at: datetime,
                    no_shows_in_month: int) -> BookingState:
        self._check_timeout(now, starts_at)
        if no_shows_in_month < 3:
            raise DomainInvariantViolation("Неявок за месяц меньше трёх: блокировка не нужна")
        return NoShowBanned()

    @staticmethod
    def _check_timeout(now: datetime, starts_at: datetime) -> None:
        # Инвариант: 15 минут с начала встречи должны пройти.
        if (now - starts_at).total_seconds() < 15 * 60:
            raise DomainInvariantViolation("15 минут ожидания ещё не прошли")