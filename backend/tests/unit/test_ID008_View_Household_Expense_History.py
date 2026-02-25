from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, status

from app.api.households import get_household_expense_history
from app.models.models import Expense, Household, HouseholdMember
from app.models.models import User as UserModel

# helpers


def _make_user(id_: int, username: str) -> UserModel:
    user = UserModel()
    user.id = id_
    user.username = username
    return user


def _make_household(id_: int, name: str) -> Household:
    hh = Household()
    hh.id = id_
    hh.name = name
    return hh


def _make_expense(id_: int, hh_id: int, description: str, amount: float) -> Expense:
    e = Expense()
    e.id = id_
    e.household_id = hh_id
    e.description = description
    e.amount = amount
    e.date = datetime.now(UTC)
    return e


# unit tests


class TestGetExpenseHistory:
    @pytest.fixture
    def alice(self):
        return _make_user(1, "Alice")

    def test_ID008_retrieve_household_expense_history_successfully(self, alice):
        """Authentic Pass: Verifies correct table queries and sorting."""
        db = MagicMock()
        hh = _make_household(10, "MapleHouse")
        membership = HouseholdMember(user_id=alice.id, household_id=hh.id, left_at=None)
        expenses = [
            _make_expense(1, hh.id, "Groceries", 50.0),
            _make_expense(2, hh.id, "Internet", 60.0),
        ]

        # Define specific query chains to prevent false positives
        hh_query = MagicMock()
        hh_query.filter.return_value.first.return_value = hh

        mem_query = MagicMock()
        mem_query.filter.return_value.first.return_value = membership

        exp_query = MagicMock()
        # We mock the full chain: .filter().order_by().all()
        exp_query.filter.return_value.order_by.return_value.all.return_value = expenses

        # The Side Effect ensures the code touches the RIGHT models
        db.query.side_effect = lambda model: {
            Household: hh_query,
            HouseholdMember: mem_query,
            Expense: exp_query,
        }.get(model)

        # Act
        result = get_household_expense_history(hh.id, db, alice)

        # Assert
        assert len(result) == 2
        assert result[0].description == "Groceries"
        # Verify the backend actually asked for the date sort
        exp_query.filter.return_value.order_by.assert_called()

    def test_ID008_reject_non_household_member_access_expense_history(self, alice):
        """Verified Failure: Ensures 403 if membership record is missing."""
        db = MagicMock()
        hh = _make_household(10, "MapleHouse")

        hh_query = MagicMock()
        hh_query.filter.return_value.first.return_value = hh

        mem_query = MagicMock()
        mem_query.filter.return_value.first.return_value = None  # No membership found

        db.query.side_effect = lambda model: hh_query if model is Household else mem_query

        with pytest.raises(HTTPException) as exc:
            get_household_expense_history(hh.id, db, alice)

        assert exc.value.status_code == status.HTTP_403_FORBIDDEN
        assert "not a member" in exc.value.detail


    def test_ID008_reject_getting_expense_history_from_nonexisting_household(self, alice):
        """Existence Test: Ensures 404 if the household ID is invalid."""
        db = MagicMock()
        db.query(Household).filter().first.return_value = None

        with pytest.raises(HTTPException) as exc:
            get_household_expense_history(999, db, alice)

        assert exc.value.status_code == status.HTTP_404_NOT_FOUND
