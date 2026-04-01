from app.models.models import (
    Expense,
    ExpenseShare,
    Household,
    HouseholdMember,
    VoteStatus,
)
from app.models.models import User as UserModel

from ..conftest import TestingSessionLocal, login, register

# ── Helpers ───────────────────────────────────────────────────────────────


def _setup_household_with_members(client):
    """Register Alice, Bob, Cara and place them in a household.
    Alice is admin. Returns dict of {name: id} and household_id.
    """
    for name in ["Alice", "Bob", "Cara"]:
        register(client, username=name, email=f"{name.lower()}@test.com", password="Password123!")

    db = TestingSessionLocal()
    alice = db.query(UserModel).filter(UserModel.username == "Alice").first()
    bob = db.query(UserModel).filter(UserModel.username == "Bob").first()
    cara = db.query(UserModel).filter(UserModel.username == "Cara").first()

    h = Household(name="TestHouse", invite_code="TEST123")
    db.add(h)
    db.flush()
    db.add(HouseholdMember(user_id=alice.id, household_id=h.id, is_admin=True))
    db.add(HouseholdMember(user_id=bob.id, household_id=h.id, is_admin=False))
    db.add(HouseholdMember(user_id=cara.id, household_id=h.id, is_admin=False))
    db.commit()

    ids = {"Alice": alice.id, "Bob": bob.id, "Cara": cara.id}
    household_id = h.id
    db.close()
    return ids, household_id


def _setup_single_member_household(client, username="Solo"):
    """Register a single user and place them as admin in a household."""
    register(
        client,
        username=username,
        email=f"{username.lower()}@test.com",
        password="Password123!",
    )

    db = TestingSessionLocal()
    user = db.query(UserModel).filter(UserModel.username == username).first()

    h = Household(name="SoloHouse", invite_code="SOLO123")
    db.add(h)
    db.flush()
    db.add(HouseholdMember(user_id=user.id, household_id=h.id, is_admin=True))
    db.commit()

    user_id = user.id
    household_id = h.id
    db.close()
    return user_id, household_id


def _create_outstanding_expense(creator_id, debtor_id, household_id, amount):
    """Create an expense where debtor owes creator money (accepted, unpaid)."""
    db = TestingSessionLocal()
    expense = Expense(
        description="Outstanding debt",
        amount=amount,
        creator_id=creator_id,
        household_id=household_id,
    )
    db.add(expense)
    db.flush()
    db.add(
        ExpenseShare(
            expense_id=expense.id,
            user_id=debtor_id,
            amount_owed=amount,
            paid_amount=0.0,
            is_paid=False,
            vote_status=VoteStatus.ACCEPTED,
        )
    )
    db.commit()
    expense_id = expense.id
    db.close()
    return expense_id


def _auth_headers(client, username="Alice"):
    token = login(client, username=username, password="Password123!").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Success Cases ─────────────────────────────────────────────────────────


class TestLeaveHouseholdSuccessCases:
    def test_ID029_household_becomes_empty_after_last_member_leaves(self, client):
        """Normal flow: last member leaves and household becomes empty."""
        user_id, h_id = _setup_single_member_household(client, username="Solo")
        headers = _auth_headers(client, username="Solo")

        resp = client.post("/api/v1/households/me/leave", headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["was_last_member"] is True
        assert "successfully left" in data["message"].lower()

        db = TestingSessionLocal()
        membership = (
            db.query(HouseholdMember)
            .filter(
                HouseholdMember.user_id == user_id,
                HouseholdMember.household_id == h_id,
            )
            .first()
        )
        assert membership.left_at is not None
        db.close()

    def test_ID029_household_member_leaves_successfully_after_paying_all_expenses(self, client):
        """Normal flow: member can leave once all their shares are paid."""
        ids, h_id = _setup_household_with_members(client)

        db = TestingSessionLocal()
        expense = Expense(
            description="Paid bill",
            amount=30.0,
            creator_id=ids["Alice"],
            household_id=h_id,
        )
        db.add(expense)
        db.flush()
        db.add(
            ExpenseShare(
                expense_id=expense.id,
                user_id=ids["Bob"],
                amount_owed=30.0,
                paid_amount=30.0,
                is_paid=True,
                vote_status=VoteStatus.ACCEPTED,
            )
        )
        db.commit()
        db.close()

        headers = _auth_headers(client, username="Bob")
        resp = client.post("/api/v1/households/me/leave", headers=headers)

        assert resp.status_code == 200
        assert "successfully left" in resp.json()["message"].lower()


# ── Error Cases ───────────────────────────────────────────────────────────


class TestLeaveHouseholdErrorCases:
    def test_ID029_household_member_with_unpaid_accepted_share_attempts_to_leave(self, client):
        """Error flow: member cannot leave with an unpaid accepted expense share."""
        ids, h_id = _setup_household_with_members(client)
        _create_outstanding_expense(
            creator_id=ids["Alice"],
            debtor_id=ids["Bob"],
            household_id=h_id,
            amount=50.0,
        )

        headers = _auth_headers(client, username="Bob")
        resp = client.post("/api/v1/households/me/leave", headers=headers)

        assert resp.status_code == 400
        assert "cannot leave: outstanding balance remains" in resp.json()["detail"].lower()

        db = TestingSessionLocal()
        membership = (
            db.query(HouseholdMember)
            .filter(
                HouseholdMember.user_id == ids["Bob"],
                HouseholdMember.household_id == h_id,
                HouseholdMember.left_at.is_(None),
            )
            .first()
        )
        assert membership is not None
        db.close()

    def test_ID029_household_member_with_pending_share_attempts_to_leave(self, client):
        """Error flow: member cannot leave with a pending expense share."""
        ids, h_id = _setup_household_with_members(client)

        db = TestingSessionLocal()
        expense = Expense(
            description="Pending bill",
            amount=20.0,
            creator_id=ids["Alice"],
            household_id=h_id,
        )
        db.add(expense)
        db.flush()
        db.add(
            ExpenseShare(
                expense_id=expense.id,
                user_id=ids["Bob"],
                amount_owed=20.0,
                paid_amount=0.0,
                is_paid=False,
                vote_status=VoteStatus.PENDING,
            )
        )
        db.commit()
        db.close()

        headers = _auth_headers(client, username="Bob")
        resp = client.post("/api/v1/households/me/leave", headers=headers)

        assert resp.status_code == 400
        assert "cannot leave: outstanding balance remains" in resp.json()["detail"].lower()

    def test_ID029_household_member_not_in_any_household_attempts_to_leave(self, client):
        """Error flow: user not in any household cannot call leave."""
        register(
            client,
            username="Dave",
            email="dave@test.com",
            password="Password123!",
        )
        headers = _auth_headers(client, username="Dave")

        resp = client.post("/api/v1/households/me/leave", headers=headers)

        assert resp.status_code == 400
        assert "not currently a member" in resp.json()["detail"].lower()

    def test_ID029_unauthenticated_user_attempts_to_leave_his_household(self, client):
        """Error flow: unauthenticated request returns 401."""
        resp = client.post("/api/v1/households/me/leave")

        assert resp.status_code == 401
