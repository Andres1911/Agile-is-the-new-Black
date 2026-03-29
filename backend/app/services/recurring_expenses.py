from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import (
    Expense,
    ExpenseShare,
    HouseholdMember,
    RecurrenceUnit,
    RecurringExpense,
    RecurringExpenseInstance,
    RecurringExpenseShare,
    VoteStatus,
)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _add_months(dt: datetime, months: int) -> datetime:
    year = dt.year + (dt.month - 1 + months) // 12
    month = (dt.month - 1 + months) % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _add_years(dt: datetime, years: int) -> datetime:
    try:
        return dt.replace(year=dt.year + years)
    except ValueError:
        # Feb 29 -> Feb 28 on non-leap years
        return dt.replace(year=dt.year + years, month=2, day=28)


def advance_due_at(due_at: datetime, interval: int, unit: RecurrenceUnit) -> datetime:
    due_at = _ensure_utc(due_at)
    if interval <= 0:
        raise ValueError("interval must be >= 1")

    if unit == RecurrenceUnit.DAILY:
        return due_at + timedelta(days=interval)
    if unit == RecurrenceUnit.WEEKLY:
        return due_at + timedelta(days=7 * interval)
    if unit == RecurrenceUnit.MONTHLY:
        return _add_months(due_at, interval)
    if unit == RecurrenceUnit.YEARLY:
        return _add_years(due_at, interval)

    raise ValueError(f"Unsupported recurrence unit: {unit}")


@dataclass(frozen=True)
class RecurringPreview:
    due_dates: list[datetime]


def preview_due_dates(
    *,
    start_at: datetime,
    interval: int,
    unit: RecurrenceUnit,
    end_at: datetime | None,
    max_occurrences: int | None,
    hard_limit: int = 500,
) -> RecurringPreview:
    """Preview the due dates to generate.

    - Includes the start date as occurrence #1.
    - `end_at` is inclusive.
    - If neither `end_at` nor `max_occurrences` is provided, returns just [start_at].
    """

    start_at = _ensure_utc(start_at)
    if end_at is not None:
        end_at = _ensure_utc(end_at)
        if end_at < start_at:
            raise ValueError("End date must be after or equal to the start date")

    if interval <= 0:
        raise ValueError("interval must be >= 1")

    if max_occurrences is not None and max_occurrences <= 0:
        raise ValueError("max_occurrences must be >= 1")

    if end_at is None and max_occurrences is None:
        return RecurringPreview(due_dates=[start_at])

    due_dates: list[datetime] = []
    due_at = start_at
    occurrence = 0
    while True:
        occurrence += 1

        if end_at is not None and due_at > end_at:
            break
        if max_occurrences is not None and occurrence > max_occurrences:
            break

        due_dates.append(due_at)
        if len(due_dates) >= hard_limit:
            raise ValueError("Recurring expense exceeds generation limit")

        due_at = advance_due_at(due_at, interval, unit)

    return RecurringPreview(due_dates=due_dates)


def _active_household_member_ids(db: Session, household_id: int) -> set[int]:
    rows = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.household_id == household_id, HouseholdMember.left_at.is_(None))
        .all()
    )
    return {r.user_id for r in rows}


def _apply_even_split(
    *,
    expense: Expense,
    total_amount: float,
    member_ids: list[int],
    creator_id: int,
):
    num = len(member_ids)
    base_share = round(total_amount / num, 2)
    sum_of_others = base_share * (num - 1)
    last_share = round(total_amount - sum_of_others, 2)

    for i, user_id in enumerate(member_ids):
        amt = base_share if i < (num - 1) else last_share
        vote = VoteStatus.ACCEPTED if user_id == creator_id else VoteStatus.PENDING
        expense.shares.append(
            ExpenseShare(
                user_id=user_id,
                amount_owed=amt,
                vote_status=vote,
            )
        )


def _apply_manual_split(
    *,
    expense: Expense,
    template_shares: list[RecurringExpenseShare],
    creator_id: int,
):
    total_manual = 0.0
    for s in template_shares:
        if s.amount_owed <= 0:
            raise ValueError("Manual share amounts must be greater than zero")
        total_manual += float(s.amount_owed)
        vote = VoteStatus.ACCEPTED if s.user_id == creator_id else VoteStatus.PENDING
        expense.shares.append(
            ExpenseShare(
                user_id=s.user_id,
                amount_owed=float(s.amount_owed),
                vote_status=vote,
            )
        )

    if abs(round(total_manual, 2) - round(float(expense.amount), 2)) > 0:
        raise ValueError(
            f"Cannot generate expense: Split amounts {total_manual:.2f} CAD do not equal expense total {expense.amount:.2f} CAD"
        )


def generate_recurring_charges(
    *,
    db: Session,
    recurring: RecurringExpense,
    due_dates: list[datetime],
) -> list[int]:
    """Create concrete Expense rows for the given due dates.

    Returns a list of created Expense IDs.
    """

    created_ids: list[int] = []
    active_member_ids = _active_household_member_ids(db, recurring.household_id)

    if recurring.creator_id not in active_member_ids:
        raise ValueError("Recurring expense creator is not an active household member")

    for due_at in due_dates:
        due_at = _ensure_utc(due_at)

        # idempotency: skip if already generated
        existing = (
            db.query(RecurringExpenseInstance)
            .filter(
                RecurringExpenseInstance.recurring_expense_id == recurring.id,
                RecurringExpenseInstance.due_at == due_at,
            )
            .first()
        )
        if existing is not None:
            continue

        next_occurrence = recurring.occurrences_generated + 1
        if recurring.end_at is not None and due_at > _ensure_utc(recurring.end_at):
            recurring.is_active = False
            break
        if recurring.max_occurrences is not None and next_occurrence > recurring.max_occurrences:
            recurring.is_active = False
            break

        if recurring.amount <= 0:
            raise ValueError("Recurring expense amount must be greater than zero")

        expense = Expense(
            description=recurring.description,
            amount=recurring.amount,
            category=recurring.category,
            creator_id=recurring.creator_id,
            household_id=recurring.household_id,
            date=due_at,
        )

        if recurring.split_evenly:
            member_ids = sorted(active_member_ids)
            if not recurring.include_creator:
                member_ids = [uid for uid in member_ids if uid != recurring.creator_id]

            if not member_ids:
                raise ValueError("No active members to split with")

            _apply_even_split(
                expense=expense,
                total_amount=float(recurring.amount),
                member_ids=member_ids,
                creator_id=recurring.creator_id,
            )
        else:
            if not recurring.template_shares:
                raise ValueError("Manual shares are required when split_evenly is False")

            template_user_ids = {s.user_id for s in recurring.template_shares}
            missing = template_user_ids - active_member_ids
            if missing:
                raise ValueError("Some manual share users are not active household members")

            _apply_manual_split(
                expense=expense,
                template_shares=list(recurring.template_shares),
                creator_id=recurring.creator_id,
            )

        db.add(expense)
        db.flush()

        db.add(
            RecurringExpenseInstance(
                recurring_expense_id=recurring.id,
                expense_id=expense.id,
                occurrence_number=next_occurrence,
                due_at=due_at,
            )
        )

        recurring.occurrences_generated = next_occurrence
        recurring.next_due_at = advance_due_at(due_at, recurring.interval, recurring.unit)
        recurring.updated_at = datetime.now(UTC)

        created_ids.append(expense.id)

        # If we reached the end condition exactly, mark inactive for future generations.
        if recurring.end_at is not None and recurring.next_due_at > _ensure_utc(recurring.end_at):
            recurring.is_active = False
        if (
            recurring.max_occurrences is not None
            and recurring.occurrences_generated >= recurring.max_occurrences
        ):
            recurring.is_active = False

    return created_ids


def generate_due_recurring_expenses(
    *,
    db: Session,
    household_id: int,
    as_of: datetime | None = None,
    hard_limit_per_recurring: int = 200,
) -> list[int]:
    """Generate all charges due on or before `as_of` for a household."""

    if as_of is None:
        as_of = datetime.now(UTC)
    as_of = _ensure_utc(as_of)

    recurring_list = (
        db.query(RecurringExpense)
        .filter(
            RecurringExpense.household_id == household_id,
            RecurringExpense.is_active.is_(True),
            RecurringExpense.next_due_at <= as_of,
        )
        .order_by(RecurringExpense.id.asc())
        .all()
    )

    created_ids: list[int] = []
    for recurring in recurring_list:
        due_dates: list[datetime] = []
        due_at = _ensure_utc(recurring.next_due_at)

        for _ in range(hard_limit_per_recurring):
            if due_at > as_of:
                break

            next_occ = recurring.occurrences_generated + len(due_dates) + 1
            if recurring.end_at is not None and due_at > _ensure_utc(recurring.end_at):
                recurring.is_active = False
                break
            if recurring.max_occurrences is not None and next_occ > recurring.max_occurrences:
                recurring.is_active = False
                break

            due_dates.append(due_at)
            due_at = advance_due_at(due_at, recurring.interval, recurring.unit)
        else:
            raise ValueError("Recurring expense exceeds generation limit")

        created_ids.extend(generate_recurring_charges(db=db, recurring=recurring, due_dates=due_dates))

    return created_ids
