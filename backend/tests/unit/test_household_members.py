from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.households import get_household_members
from app.models.models import Household, HouseholdMember
from app.models.models import User as UserModel


# helpers needed to construct the objects returned by the mocked database queries

def _make_user(id_: int, username: str) -> UserModel:
    user = UserModel()
    user.id = id_
    user.username = username
    user.email = f"{username.lower()}@test.com"
    user.is_active = True
    return user


def _make_household(id_: int, name: str) -> Household:
    hh = Household()
    hh.id = id_
    hh.name = name
    hh.invite_code = "TEST1234"
    return hh


def _make_membership(user_id: int, household_id: int, is_admin: bool = False) -> HouseholdMember:
    m = HouseholdMember()
    m.user_id = user_id
    m.household_id = household_id
    m.is_admin = is_admin
    m.left_at = None
    return m


# Normal Flow Test

class TestGetHouseholdMembersNormalFlow:
    def test_member_can_view_member_list(self):
        """A current member receives the full list of household members."""
        alice = _make_user(1, "Alice")
        bob = _make_user(2, "Bob")
        cara = _make_user(3, "Cara")
        household = _make_household(10, "MapleHouse")

        memberships = [
            _make_membership(alice.id, household.id, is_admin=True),
            _make_membership(bob.id, household.id),
            _make_membership(cara.id, household.id),
        ]

        db = MagicMock()

        # Stub: household exists
        db.query(Household).filter().first.return_value = household

        # Stub: requesting user IS a member
        db.query(HouseholdMember).filter().first.return_value = memberships[0]

        # Stub: full member list
        db.query(HouseholdMember).filter().all.return_value = memberships

        result = get_household_members(
            household_id=household.id,
            db=db,
            current_user=alice,
        )

        assert result == memberships
        assert len(result) == 3

    def test_non_admin_member_can_also_view_list(self):
        """Any active member (not just admin) can view the list."""
        alice = _make_user(1, "Alice")
        bob = _make_user(2, "Bob")
        household = _make_household(10, "MapleHouse")

        bob_membership = _make_membership(bob.id, household.id, is_admin=False)
        all_members = [
            _make_membership(alice.id, household.id, is_admin=True),
            bob_membership,
        ]

        db = MagicMock()
        db.query(Household).filter().first.return_value = household
        db.query(HouseholdMember).filter().first.return_value = bob_membership
        db.query(HouseholdMember).filter().all.return_value = all_members

        result = get_household_members(
            household_id=household.id,
            db=db,
            current_user=bob,
        )

        assert len(result) == 2

    def test_returns_only_active_members(self):
        """Members who have left (left_at set) are excluded by the query."""
        alice = _make_user(1, "Alice")
        household = _make_household(10, "MapleHouse")

        alice_membership = _make_membership(alice.id, household.id, is_admin=True)
        # Only active members returned by the stubbed query
        active_members = [alice_membership]

        db = MagicMock()
        db.query(Household).filter().first.return_value = household
        db.query(HouseholdMember).filter().first.return_value = alice_membership
        db.query(HouseholdMember).filter().all.return_value = active_members

        result = get_household_members(
            household_id=household.id,
            db=db,
            current_user=alice,
        )

        assert result == active_members


# Error Flow Tests

class TestGetHouseholdMembersErrorFlows:
    def test_household_not_found_raises_404(self):
        """Should raise 404 when the household does not exist."""
        alice = _make_user(1, "Alice")

        db = MagicMock()
        db.query(Household).filter().first.return_value = None  # household missing

        with pytest.raises(HTTPException) as exc_info:
            get_household_members(household_id=999, db=db, current_user=alice)

        assert exc_info.value.status_code == 404
        assert "Household not found" in exc_info.value.detail

    def test_non_member_raises_403(self):
        """Should raise 403 when the requesting user is not in the household."""
        dave = _make_user(4, "Dave")
        household = _make_household(10, "MapleHouse")

        # Use side_effect to return different values for Household vs HouseholdMember queries
        db = MagicMock()

        household_query = MagicMock()
        household_query.filter.return_value.first.return_value = household

        member_query = MagicMock()
        member_query.filter.return_value.first.return_value = None  # Dave is not a member

        db.query.side_effect = lambda model: household_query if model is Household else member_query

        with pytest.raises(HTTPException) as exc_info:
            get_household_members(
                household_id=household.id,
                db=db,
                current_user=dave,
            )

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    def test_unauthenticated_request_raises_401(self, client):
        """No token → 401 from the FastAPI dependency layer."""
        resp = client.get("/api/v1/households/1/members")
        assert resp.status_code == 401

    def test_single_member_household_returns_one_item(self):
        """A household with only the creator should return a list of one."""
        alice = _make_user(1, "Alice")
        household = _make_household(10, "SoloHouse")

        alice_membership = _make_membership(alice.id, household.id, is_admin=True)

        db = MagicMock()
        db.query(Household).filter().first.return_value = household
        db.query(HouseholdMember).filter().first.return_value = alice_membership
        db.query(HouseholdMember).filter().all.return_value = [alice_membership]

        result = get_household_members(
            household_id=household.id,
            db=db,
            current_user=alice,
        )

        assert len(result) == 1
        assert result[0].user_id == alice.id
