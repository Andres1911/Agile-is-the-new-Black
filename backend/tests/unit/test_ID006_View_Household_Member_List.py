from unittest.mock import MagicMock

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
    def test_ID006_household_admin_view_member_list_successfully(self):
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

    def test_ID006_non_household_admin_view_member_list_successfully(self):
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

    def test_ID006_member_list_retrieve_active_members_only(self):
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
    def test_ID006_household_not_found_raises_404(self):
        """Should raise 404 when the household does not exist."""
        alice = _make_user(1, "Alice")

        db = MagicMock()
        db.query(Household).filter().first.return_value = None  # household missing

        with pytest.raises(HTTPException) as exc_info:
            get_household_members(household_id=999, db=db, current_user=alice)

        assert exc_info.value.status_code == 404
        assert "Household not found" in exc_info.value.detail

    def test_ID006_unauthenticated_request_raises_401(self, client):
        """No token → 401 from the FastAPI dependency layer."""
        resp = client.get("/api/v1/households/1/members")
        assert resp.status_code == 401
