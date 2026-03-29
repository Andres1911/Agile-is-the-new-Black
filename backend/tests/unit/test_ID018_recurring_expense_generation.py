from datetime import UTC, datetime

import pytest

from app.models.models import (
    Expense,
    ExpenseShare,
    Household,
    HouseholdMember,
    RecurrenceUnit,
    RecurringExpense,
    RecurringExpenseShare,
    User,
    VoteStatus,
)
from app.services.recurring_expenses import generate_recurring_charges, preview_due_dates


def _mk_user(db, username: str) -> User:
    user = User(
        username=username,
        email=f"{username.lower()}@test.com",
        password_hash="x",
        full_name=username,
    )
    db.add(user)
    db.flush()
    return user


def _mk_household(db, name: str = "MapleHouse") -> Household:
    hh = Household(name=name, invite_code="MAPLE123", description="Test")
    db.add(hh)
    db.flush()
    return hh


class TestRecurringExpenseGeneration:
    def test_ID018_monthly_end_date_inclusive_generates_expected_charges_and_shares(self, db):
        alice = _mk_user(db, "Alice")
        bob = _mk_user(db, "Bob")
        cara = _mk_user(db, "Cara")
        hh = _mk_household(db)

        db.add(HouseholdMember(user_id=alice.id, household_id=hh.id, is_admin=True))
        db.add(HouseholdMember(user_id=bob.id, household_id=hh.id, is_admin=False))
        db.add(HouseholdMember(user_id=cara.id, household_id=hh.id, is_admin=False))
        db.flush()

        start_at = datetime(2026, 3, 15, tzinfo=UTC)
        end_at = datetime(2026, 6, 15, tzinfo=UTC)

        recurring = RecurringExpense(
            description="Internet",
            amount=60.0,
            category=None,
            split_evenly=False,
            include_creator=False,
            interval=1,
            unit=RecurrenceUnit.MONTHLY,
            start_at=start_at,
            next_due_at=start_at,
            end_at=end_at,
            max_occurrences=None,
            creator_id=alice.id,
            household_id=hh.id,
        )
        recurring.template_shares.append(RecurringExpenseShare(user_id=bob.id, amount_owed=20.0))
        recurring.template_shares.append(RecurringExpenseShare(user_id=cara.id, amount_owed=40.0))

        db.add(recurring)
        db.flush()

        preview = preview_due_dates(
            start_at=start_at,
            interval=1,
            unit=RecurrenceUnit.MONTHLY,
            end_at=end_at,
            max_occurrences=None,
        )
        created_ids = generate_recurring_charges(
            db=db, recurring=recurring, due_dates=preview.due_dates
        )
        db.commit()

        assert len(created_ids) == 4

        expenses = (
            db.query(Expense)
            .filter(Expense.household_id == hh.id, Expense.description == "Internet")
            .order_by(Expense.date.asc())
            .all()
        )
        assert [e.date.date().isoformat() for e in expenses] == [
            "2026-03-15",
            "2026-04-15",
            "2026-05-15",
            "2026-06-15",
        ]

        for e in expenses:
            shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == e.id).all()
            assert len(shares) == 2
            by_user = {s.user_id: s for s in shares}
            assert by_user[bob.id].amount_owed == 20.0
            assert by_user[cara.id].amount_owed == 40.0
            assert by_user[bob.id].paid_amount == 0.0
            assert by_user[cara.id].paid_amount == 0.0
            assert by_user[bob.id].is_paid is False
            assert by_user[cara.id].is_paid is False
            assert by_user[bob.id].vote_status == VoteStatus.PENDING
            assert by_user[cara.id].vote_status == VoteStatus.PENDING

        assert recurring.occurrences_generated == 4
        assert recurring.is_active is False

    def test_ID018_weekly_fixed_occurrences_generates_expected_charges(self, db):
        alice = _mk_user(db, "Alice")
        bob = _mk_user(db, "Bob")
        cara = _mk_user(db, "Cara")
        hh = _mk_household(db)

        db.add(HouseholdMember(user_id=alice.id, household_id=hh.id, is_admin=True))
        db.add(HouseholdMember(user_id=bob.id, household_id=hh.id, is_admin=False))
        db.add(HouseholdMember(user_id=cara.id, household_id=hh.id, is_admin=False))
        db.flush()

        start_at = datetime(2026, 3, 10, tzinfo=UTC)

        recurring = RecurringExpense(
            description="Gym",
            amount=25.0,
            category=None,
            split_evenly=True,
            include_creator=False,
            interval=1,
            unit=RecurrenceUnit.WEEKLY,
            start_at=start_at,
            next_due_at=start_at,
            end_at=None,
            max_occurrences=4,
            creator_id=alice.id,
            household_id=hh.id,
        )

        db.add(recurring)
        db.flush()

        preview = preview_due_dates(
            start_at=start_at,
            interval=1,
            unit=RecurrenceUnit.WEEKLY,
            end_at=None,
            max_occurrences=4,
        )
        created_ids = generate_recurring_charges(
            db=db, recurring=recurring, due_dates=preview.due_dates
        )
        db.commit()

        assert len(created_ids) == 4

        expenses = (
            db.query(Expense)
            .filter(Expense.household_id == hh.id, Expense.description == "Gym")
            .order_by(Expense.date.asc())
            .all()
        )
        assert [e.date.date().isoformat() for e in expenses] == [
            "2026-03-10",
            "2026-03-17",
            "2026-03-24",
            "2026-03-31",
        ]

        for e in expenses:
            shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == e.id).all()
            assert len(shares) == 2
            amounts = sorted([float(s.amount_owed) for s in shares])
            assert amounts == [12.5, 12.5]
            for s in shares:
                assert s.vote_status == VoteStatus.PENDING

        assert recurring.occurrences_generated == 4
        assert recurring.is_active is False

    def test_ID018_rejects_end_date_before_start_date(self):
        start_at = datetime(2026, 6, 1, tzinfo=UTC)
        end_at = datetime(2026, 5, 1, tzinfo=UTC)

        with pytest.raises(ValueError) as exc:
            preview_due_dates(
                start_at=start_at,
                interval=1,
                unit=RecurrenceUnit.MONTHLY,
                end_at=end_at,
                max_occurrences=None,
            )

        assert "End date must be after or equal" in str(exc.value)
