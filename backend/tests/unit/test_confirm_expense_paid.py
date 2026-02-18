"""Unit tests for confirm expense share payment (ID010 / TID022)."""

from app.models.models import Expense, ExpenseShare, ExpenseStatus, User
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


class TestConfirmPaymentSuccess:
    """Normal flows: full and partial payment."""

    def test_participant_confirms_full_payment(self, client, db):
        expense_id, _, headers_bob, _ = _setup_household_and_expense(client, db)
        resp = client.post(
            f"/api/v1/expenses/{expense_id}/confirm-payment",
            json={"amount": 20.0},
            headers=headers_bob,
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Payment recorded"

        db.expire_all()  # refresh from DB
        bob_id = db.query(User).filter(User.username == "Bob").first().id
        share = (
            db.query(ExpenseShare)
            .filter(ExpenseShare.expense_id == expense_id, ExpenseShare.user_id == bob_id)
            .first()
        )
        assert share.paid_amount == 20.0
        assert share.is_paid is True
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        assert expense.status == ExpenseStatus.PARTIALLY_SETTLED

    def test_second_participant_pays_and_expense_fully_settled(self, client, db):
        expense_id, _, headers_bob, headers_cara = _setup_household_and_expense(client, db)
        client.post(
            f"/api/v1/expenses/{expense_id}/confirm-payment",
            json={"amount": 20.0},
            headers=headers_bob,
        )
        resp = client.post(
            f"/api/v1/expenses/{expense_id}/confirm-payment",
            json={"amount": 40.0},
            headers=headers_cara,
        )
        assert resp.status_code == 200

        db.expire_all()
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        assert expense.status == ExpenseStatus.FULLY_SETTLED
        shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()
        assert all(s.is_paid for s in shares)

    def test_partial_payment_updates_outstanding(self, client, db):
        expense_id, _, _, headers_cara = _setup_household_and_expense(client, db)
        resp = client.post(
            f"/api/v1/expenses/{expense_id}/confirm-payment",
            json={"amount": 15.0},
            headers=headers_cara,
        )
        assert resp.status_code == 200

        db.expire_all()
        cara = db.query(User).filter(User.username == "Cara").first()
        share = (
            db.query(ExpenseShare)
            .filter(ExpenseShare.expense_id == expense_id, ExpenseShare.user_id == cara.id)
            .first()
        )
        assert share.paid_amount == 15.0
        assert share.is_paid is False
        assert share.amount_owed - share.paid_amount == 25.0


class TestConfirmPaymentErrors:
    """Error flows: non-participant, overpayment, already paid."""

    def test_non_participant_rejected(self, client, db):
        """Cara has no share in an expense that only has Bob; Cara cannot confirm payment."""
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
            f"/api/v1/expenses/{expense_id}/confirm-payment",
            json={"amount": 30.0},
            headers=headers_cara,
        )
        assert resp.status_code == 400
        assert "do not have an expense share" in resp.json()["detail"].lower()

    def test_payment_exceeds_outstanding_rejected(self, client, db):
        expense_id, _, headers_bob, _ = _setup_household_and_expense(client, db)
        resp = client.post(
            f"/api/v1/expenses/{expense_id}/confirm-payment",
            json={"amount": 25.0},
            headers=headers_bob,
        )
        assert resp.status_code == 400
        assert "exceeds outstanding" in resp.json()["detail"].lower()
        assert "25.00" in resp.json()["detail"]
        assert "20.00" in resp.json()["detail"]

    def test_already_paid_share_rejected(self, client, db):
        expense_id, _, headers_bob, _ = _setup_household_and_expense(client, db)
        client.post(
            f"/api/v1/expenses/{expense_id}/confirm-payment",
            json={"amount": 20.0},
            headers=headers_bob,
        )
        resp = client.post(
            f"/api/v1/expenses/{expense_id}/confirm-payment",
            json={"amount": 5.0},
            headers=headers_bob,
        )
        assert resp.status_code == 400
        assert "already fully paid" in resp.json()["detail"].lower()

    def test_zero_amount_rejected(self, client, db):
        expense_id, _, headers_bob, _ = _setup_household_and_expense(client, db)
        resp = client.post(
            f"/api/v1/expenses/{expense_id}/confirm-payment",
            json={"amount": 0.0},
            headers=headers_bob,
        )
        assert resp.status_code == 400
        assert "greater than zero" in resp.json()["detail"].lower()
