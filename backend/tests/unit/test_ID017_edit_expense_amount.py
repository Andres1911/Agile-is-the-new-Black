from app.models.models import (
    Expense,
    ExpenseShare,
    ExpenseStatus,
    Household,
    HouseholdMember,
    VoteStatus,
)
from app.models.models import User as UserModel

from ..conftest import TestingSessionLocal, login, register


def _setup_household_with_members(client):
    """Register Alice, Bob, Cara and place them in a household.
    Returns dict of {name: id} and household_id.
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
    db.add(HouseholdMember(user_id=bob.id, household_id=h.id))
    db.add(HouseholdMember(user_id=cara.id, household_id=h.id))
    db.commit()

    ids = {"Alice": alice.id, "Bob": bob.id, "Cara": cara.id}
    household_id = h.id
    db.close()
    return ids, household_id


def _create_expense_with_shares(creator_id, household_id, amount, description, status, shares):
    """Create an expense and its shares directly in the DB. Returns expense id."""
    db = TestingSessionLocal()
    expense = Expense(
        description=description,
        amount=amount,
        creator_id=creator_id,
        household_id=household_id,
        status=status,
    )
    db.add(expense)
    db.flush()

    for s in shares:
        db.add(ExpenseShare(
            expense_id=expense.id,
            user_id=s["user_id"],
            amount_owed=s["amount_owed"],
            paid_amount=s.get("paid_amount", 0.0),
            is_paid=s.get("is_paid", False),
            vote_status=s.get("vote_status", VoteStatus.PENDING),
        ))
    db.commit()
    expense_id = expense.id
    db.close()
    return expense_id


def _auth_headers(client, username="Alice"):
    token = login(client, username=username, password="Password123!").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestEditExpenseAmountSuccessCases:
    def test_ID017_edit_amount_manual_resplit(self, client):
        """Normal flow: edit amount from 60 to 90 with manual resplit."""
        ids, h_id = _setup_household_with_members(client)
        headers = _auth_headers(client)

        expense_id = _create_expense_with_shares(
            creator_id=ids["Alice"],
            household_id=h_id,
            amount=60.00,
            description="Grocery run",
            status=ExpenseStatus.PENDING,
            shares=[
                {"user_id": ids["Bob"], "amount_owed": 30.00},
                {"user_id": ids["Cara"], "amount_owed": 30.00},
            ],
        )

        payload = {
            "amount": 90.00,
            "split_evenly": False,
            "manual_shares": [
                {"user_id": ids["Bob"], "amount": 30.00},
                {"user_id": ids["Cara"], "amount": 60.00},
            ],
        }

        resp = client.put(
            f"/api/v1/expenses/{expense_id}/edit-amount",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 200

        db = TestingSessionLocal()
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        assert expense.amount == 90.00
        assert expense.description == "Grocery run"
        assert expense.status == ExpenseStatus.PENDING

        shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()
        assert len(shares) == 2

        bob_share = next(s for s in shares if s.user_id == ids["Bob"])
        cara_share = next(s for s in shares if s.user_id == ids["Cara"])
        assert bob_share.amount_owed == 30.00
        assert cara_share.amount_owed == 60.00
        assert bob_share.paid_amount == 0.0
        assert cara_share.paid_amount == 0.0
        db.close()

    def test_ID017_edit_amount_equal_resplit_with_self(self, client):
        """Alternative flow: edit amount and resplit equally including self."""
        ids, h_id = _setup_household_with_members(client)
        headers = _auth_headers(client)

        expense_id = _create_expense_with_shares(
            creator_id=ids["Alice"],
            household_id=h_id,
            amount=30.00,
            description="Pizza night",
            status=ExpenseStatus.DISPUTED,
            shares=[
                {"user_id": ids["Alice"], "amount_owed": 10.00, "vote_status": VoteStatus.ACCEPTED},
                {"user_id": ids["Bob"], "amount_owed": 5.00, "vote_status": VoteStatus.REJECTED},
                {"user_id": ids["Cara"], "amount_owed": 15.00, "vote_status": VoteStatus.REJECTED},
            ],
        )

        payload = {
            "amount": 45.00,
            "split_evenly": True,
            "include_self": True,
        }

        resp = client.put(
            f"/api/v1/expenses/{expense_id}/edit-amount",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 200

        db = TestingSessionLocal()
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        assert expense.amount == 45.00
        assert expense.status == ExpenseStatus.PENDING

        shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()
        assert len(shares) == 3

        for s in shares:
            assert s.amount_owed == 15.00
            assert s.paid_amount == 0.0
            if s.user_id == ids["Alice"]:
                assert s.vote_status == VoteStatus.ACCEPTED
            else:
                assert s.vote_status == VoteStatus.PENDING
        db.close()

    def test_ID017_former_member_can_edit_their_expense(self, client):
        """Alternative flow: former member edits expense after leaving household."""
        ids, h_id = _setup_household_with_members(client)
        headers = _auth_headers(client)

        expense_id = _create_expense_with_shares(
            creator_id=ids["Alice"],
            household_id=h_id,
            amount=60.00,
            description="Grocery run",
            status=ExpenseStatus.PENDING,
            shares=[
                {"user_id": ids["Bob"], "amount_owed": 30.00, "vote_status": VoteStatus.ACCEPTED},
                {"user_id": ids["Cara"], "amount_owed": 30.00},
            ],
        )

        # Alice leaves the household
        from datetime import UTC, datetime

        db = TestingSessionLocal()
        membership = (
            db.query(HouseholdMember)
            .filter(HouseholdMember.user_id == ids["Alice"], HouseholdMember.household_id == h_id)
            .first()
        )
        membership.left_at = datetime.now(UTC)
        db.commit()
        db.close()

        payload = {
            "amount": 90.00,
            "split_evenly": False,
            "manual_shares": [
                {"user_id": ids["Bob"], "amount": 30.00},
                {"user_id": ids["Cara"], "amount": 60.00},
            ],
        }

        resp = client.put(
            f"/api/v1/expenses/{expense_id}/edit-amount",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 200

        db = TestingSessionLocal()
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        assert expense.amount == 90.00

        shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()
        assert len(shares) == 2
        bob_share = next(s for s in shares if s.user_id == ids["Bob"])
        cara_share = next(s for s in shares if s.user_id == ids["Cara"])
        # After edit, previously accepted shares reset to PENDING
        assert bob_share.vote_status == VoteStatus.PENDING
        assert bob_share.amount_owed == 30.00
        assert cara_share.amount_owed == 60.00
        db.close()


class TestEditExpenseAmountFailCases:
    def test_ID017_split_amounts_do_not_equal_total(self, client):
        """Error flow: manual shares don't sum to new amount."""
        ids, h_id = _setup_household_with_members(client)
        headers = _auth_headers(client)

        expense_id = _create_expense_with_shares(
            creator_id=ids["Alice"],
            household_id=h_id,
            amount=60.00,
            description="Grocery run",
            status=ExpenseStatus.PENDING,
            shares=[
                {"user_id": ids["Bob"], "amount_owed": 30.00},
                {"user_id": ids["Cara"], "amount_owed": 30.00},
            ],
        )

        payload = {
            "amount": 100.00,
            "split_evenly": False,
            "manual_shares": [
                {"user_id": ids["Bob"], "amount": 40.00},
                {"user_id": ids["Cara"], "amount": 40.00},
            ],
        }

        resp = client.put(
            f"/api/v1/expenses/{expense_id}/edit-amount",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 400
        assert "split amounts 80.00 cad do not equal expense total 100.00 cad" in resp.json()["detail"].lower()

    def test_ID017_negative_amount(self, client):
        """Error flow: negative amount."""
        ids, h_id = _setup_household_with_members(client)
        headers = _auth_headers(client)

        expense_id = _create_expense_with_shares(
            creator_id=ids["Alice"],
            household_id=h_id,
            amount=60.00,
            description="Grocery run",
            status=ExpenseStatus.PENDING,
            shares=[
                {"user_id": ids["Bob"], "amount_owed": 60.00},
            ],
        )

        payload = {
            "amount": -20.00,
            "split_evenly": False,
            "manual_shares": [
                {"user_id": ids["Bob"], "amount": -20.00},
            ],
        }

        resp = client.put(
            f"/api/v1/expenses/{expense_id}/edit-amount",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 400
        assert "amount must be greater than zero" in resp.json()["detail"].lower()

    def test_ID017_cannot_edit_finalized_expense(self, client):
        """Error flow: editing a finalized expense."""
        ids, h_id = _setup_household_with_members(client)
        headers = _auth_headers(client)

        expense_id = _create_expense_with_shares(
            creator_id=ids["Alice"],
            household_id=h_id,
            amount=150.00,
            description="Hydro Bill",
            status=ExpenseStatus.FINALIZED,
            shares=[
                {"user_id": ids["Alice"], "amount_owed": 100.00, "is_paid": True, "vote_status": VoteStatus.ACCEPTED},
                {"user_id": ids["Bob"], "amount_owed": 25.00, "is_paid": True, "vote_status": VoteStatus.ACCEPTED},
                {"user_id": ids["Cara"], "amount_owed": 25.00, "is_paid": True, "vote_status": VoteStatus.ACCEPTED},
            ],
        )

        payload = {
            "amount": 180.00,
            "split_evenly": False,
            "manual_shares": [
                {"user_id": ids["Alice"], "amount": 60.00},
                {"user_id": ids["Bob"], "amount": 60.00},
                {"user_id": ids["Cara"], "amount": 60.00},
            ],
        }

        resp = client.put(
            f"/api/v1/expenses/{expense_id}/edit-amount",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 400
        assert "finalized expenses cannot be modified" in resp.json()["detail"].lower()

    def test_ID017_cannot_edit_fully_settled_expense(self, client):
        """Error flow: editing a fully settled expense."""
        ids, h_id = _setup_household_with_members(client)
        headers = _auth_headers(client)

        expense_id = _create_expense_with_shares(
            creator_id=ids["Alice"],
            household_id=h_id,
            amount=150.00,
            description="Hydro Bill",
            status=ExpenseStatus.FULLY_SETTLED,
            shares=[
                {"user_id": ids["Alice"], "amount_owed": 50.00, "paid_amount": 50.00, "is_paid": True, "vote_status": VoteStatus.ACCEPTED},
                {"user_id": ids["Bob"], "amount_owed": 50.00, "paid_amount": 50.00, "is_paid": True, "vote_status": VoteStatus.ACCEPTED},
                {"user_id": ids["Cara"], "amount_owed": 50.00, "paid_amount": 50.00, "is_paid": True, "vote_status": VoteStatus.ACCEPTED},
            ],
        )

        payload = {
            "amount": 180.00,
            "split_evenly": False,
            "manual_shares": [
                {"user_id": ids["Alice"], "amount": 60.00},
                {"user_id": ids["Bob"], "amount": 60.00},
                {"user_id": ids["Cara"], "amount": 60.00},
            ],
        }

        resp = client.put(
            f"/api/v1/expenses/{expense_id}/edit-amount",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 400
        assert "fully settled expenses cannot be modified" in resp.json()["detail"].lower()

    def test_ID017_non_creator_cannot_edit_expense(self, client):
        """Error flow: non-creator tries to edit expense."""
        ids, h_id = _setup_household_with_members(client)
        bob_headers = _auth_headers(client, username="Bob")

        expense_id = _create_expense_with_shares(
            creator_id=ids["Alice"],
            household_id=h_id,
            amount=60.00,
            description="Grocery run",
            status=ExpenseStatus.PENDING,
            shares=[
                {"user_id": ids["Bob"], "amount_owed": 30.00},
                {"user_id": ids["Cara"], "amount_owed": 30.00},
            ],
        )

        payload = {
            "amount": 90.00,
            "split_evenly": False,
            "manual_shares": [
                {"user_id": ids["Bob"], "amount": 45.00},
                {"user_id": ids["Cara"], "amount": 45.00},
            ],
        }

        resp = client.put(
            f"/api/v1/expenses/{expense_id}/edit-amount",
            json=payload,
            headers=bob_headers,
        )
        assert resp.status_code == 403
        assert "only the expense creator" in resp.json()["detail"].lower()
