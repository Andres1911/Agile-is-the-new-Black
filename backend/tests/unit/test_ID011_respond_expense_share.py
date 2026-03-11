# tests/unit/test_respond_expense_share.py

"""Unit tests for responding to an expense share (accept/decline) (ID011 / TID0XX)."""

from app.models.models import Expense, ExpenseShare, ExpenseStatus, User, VoteStatus
from tests.conftest import auth_header, create_expense, register


def _setup_household_and_expense(client, db):
    """Register Alice, Bob, Cara; create household with all three; Alice creates expense 60 CAD split Bob=20, Cara=40. Returns (expense_id, headers_alice, headers_bob, headers_cara)."""
    from app.models.models import Household, HouseholdMember

    for name in ("Alice", "Bob", "Cara"):
        register(
            client,
            email=f"{name.lower()}@test.com",
            username=name,
            password="Password123!",
            full_name=name,
        )
    alice = db.query(User).filter(User.username == "Alice").first()
    bob = db.query(User).filter(User.username == "Bob").first()
    cara = db.query(User).filter(User.username == "Cara").first()

    household = Household(name="MapleHouse", invite_code="MAPLE101", description="Test")
    db.add(household)
    db.flush()
    db.add(HouseholdMember(user_id=alice.id, household_id=household.id, is_admin=True))
    db.add(HouseholdMember(user_id=bob.id, household_id=household.id, is_admin=False))
    db.add(HouseholdMember(user_id=cara.id, household_id=household.id, is_admin=False))
    db.commit()

    headers_alice = auth_header(client, username="Alice", password="Password123!")
    headers_bob = auth_header(client, username="Bob", password="Password123!")
    headers_cara = auth_header(client, username="Cara", password="Password123!")

    payload = {
        "description": "Grocery run",
        "amount": 60.0,
        "category": "Grocery",
        "split_evenly": False,
        "include_creator": False,
        "manual_shares": [
            {"user_id": bob.id, "amount": 20.0},
            {"user_id": cara.id, "amount": 40.0},
        ],
    }
    resp = create_expense(client, headers_alice, payload)
    assert resp.status_code == 201, resp.text

    expense = (
        db.query(Expense)
        .filter(Expense.creator_id == alice.id, Expense.household_id == household.id)
        .order_by(Expense.id.desc())
        .first()
    )
    assert expense is not None
    return expense.id, headers_alice, headers_bob, headers_cara


class TestRespondExpenseShareSuccess:
    """Normal and alternative flows: accept/decline expense share."""

    def test_ID011_participant_accepts_expense_share(self, client, db):
        expense_id, _, headers_bob, _ = _setup_household_and_expense(client, db)

        resp = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "accept"},
            headers=headers_bob,
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Expense share accepted"

        db.expire_all()
        bob_id = db.query(User).filter(User.username == "Bob").first().id
        share = (
            db.query(ExpenseShare)
            .filter(ExpenseShare.expense_id == expense_id, ExpenseShare.user_id == bob_id)
            .first()
        )
        assert share.vote_status == VoteStatus.ACCEPTED

        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        # Cara is still pending, so expense should remain pending
        assert expense.status == ExpenseStatus.PENDING

    def test_ID011_participant_declines_expense_share_and_expense_becomes_disputed(
        self, client, db
    ):
        expense_id, _, headers_bob, _ = _setup_household_and_expense(client, db)

        resp = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "decline"},
            headers=headers_bob,
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Expense share declined"

        db.expire_all()
        bob_id = db.query(User).filter(User.username == "Bob").first().id
        share = (
            db.query(ExpenseShare)
            .filter(ExpenseShare.expense_id == expense_id, ExpenseShare.user_id == bob_id)
            .first()
        )
        assert share.vote_status == VoteStatus.REJECTED

        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        assert expense.status == ExpenseStatus.DISPUTED

    def test_ID011_all_participants_accept_and_expense_becomes_finalized(self, client, db):
        expense_id, _, headers_bob, headers_cara = _setup_household_and_expense(client, db)

        resp_bob = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "accept"},
            headers=headers_bob,
        )
        assert resp_bob.status_code == 200

        resp_cara = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "accept"},
            headers=headers_cara,
        )
        assert resp_cara.status_code == 200
        assert resp_cara.json()["detail"] == "Expense share accepted"

        db.expire_all()
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        assert expense.status == ExpenseStatus.FINALIZED

        shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()
        assert all(s.vote_status == VoteStatus.ACCEPTED for s in shares)


class TestRespondExpenseShareErrors:
    """Error flows: non-participant, invalid decision, missing expense, no household."""

    def test_ID011_non_participant_rejected(self, client, db):
        """Cara has no share in an expense that only has Bob; Cara cannot respond."""
        from app.models.models import Household, HouseholdMember

        for name in ("Alice", "Bob", "Cara"):
            register(
                client,
                email=f"{name.lower()}2@test.com",
                username=name + "2",
                password="Password123!",
                full_name=name,
            )
        alice = db.query(User).filter(User.username == "Alice2").first()
        bob = db.query(User).filter(User.username == "Bob2").first()
        cara = db.query(User).filter(User.username == "Cara2").first()

        household = Household(name="OtherHouse", invite_code="OTHER102", description="Test")
        db.add(household)
        db.flush()
        db.add(HouseholdMember(user_id=alice.id, household_id=household.id, is_admin=True))
        db.add(HouseholdMember(user_id=bob.id, household_id=household.id, is_admin=False))
        db.add(HouseholdMember(user_id=cara.id, household_id=household.id, is_admin=False))
        db.commit()

        headers_alice = auth_header(client, username="Alice2", password="Password123!")
        headers_cara = auth_header(client, username="Cara2", password="Password123!")

        payload = {
            "description": "Movie night",
            "amount": 30.0,
            "category": "Fun",
            "split_evenly": False,
            "include_creator": False,
            "manual_shares": [{"user_id": bob.id, "amount": 30.0}],
        }
        create_expense(client, headers_alice, payload)
        expense = (
            db.query(Expense)
            .filter(Expense.creator_id == alice.id, Expense.household_id == household.id)
            .order_by(Expense.id.desc())
            .first()
        )
        expense_id = expense.id

        resp = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "accept"},
            headers=headers_cara,
        )
        assert resp.status_code == 400
        assert "do not have an expense share" in resp.json()["detail"].lower()

    def test_ID011_expense_not_found(self, client, db):
        expense_id, _, headers_bob, _ = _setup_household_and_expense(client, db)

        # Use a non-existing expense id
        resp = client.post(
            f"/api/v1/expenses/{expense_id + 99999}/respond-share",
            json={"decision": "accept"},
            headers=headers_bob,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Expense not found"

    def test_ID011_user_not_in_household_rejected(self, client, db):
        expense_id, _, _, _ = _setup_household_and_expense(client, db)

        register(
            client,
            email="outsider@test.com",
            username="Outsider",
            password="Password123!",
            full_name="Outsider",
        )
        headers_outsider = auth_header(client, username="Outsider", password="Password123!")

        resp = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "accept"},
            headers=headers_outsider,
        )
        assert resp.status_code == 400
        assert "not currently in any household" in resp.json()["detail"].lower()

    def test_ID011_invalid_decision_rejected_by_schema(self, client, db):
        expense_id, _, headers_bob, _ = _setup_household_and_expense(client, db)

        resp = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "maybe"},
            headers=headers_bob,
        )
        assert resp.status_code == 422
