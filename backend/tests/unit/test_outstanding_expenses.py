"""Unit tests for listing current user's outstanding expense shares."""

from tests.conftest import auth_header, create_expense, register


def _setup_household_and_expense(client, db):
    """Register Alice + Bob; create household; Alice creates expense split Bob owes 20."""
    from app.models.models import Expense, Household, HouseholdMember, User

    register(
        client,
        email="alice@test.com",
        username="Alice",
        password="Password123!",
        full_name="Alice",
    )
    register(
        client,
        email="bob@test.com",
        username="Bob",
        password="Password123!",
        full_name="Bob",
    )

    alice = db.query(User).filter(User.username == "Alice").first()
    bob = db.query(User).filter(User.username == "Bob").first()

    household = Household(name="MapleHouse", invite_code="MAPLE101", description="Test")
    db.add(household)
    db.flush()
    db.add(HouseholdMember(user_id=alice.id, household_id=household.id, is_admin=True))
    db.add(HouseholdMember(user_id=bob.id, household_id=household.id, is_admin=False))
    db.commit()

    headers_alice = auth_header(client, username="Alice", password="Password123!")
    headers_bob = auth_header(client, username="Bob", password="Password123!")

    payload = {
        "description": "Grocery run",
        "amount": 20.0,
        "category": "Grocery",
        "split_evenly": False,
        "include_creator": False,
        "manual_shares": [{"user_id": bob.id, "amount": 20.0}],
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

    return expense.id, headers_alice, headers_bob


class TestOutstandingExpenses:
    def test_lists_unpaid_shares_for_current_user(self, client, db):
        expense_id, _, headers_bob = _setup_household_and_expense(client, db)

        resp = client.get("/api/v1/expenses/outstanding", headers=headers_bob)
        assert resp.status_code == 200, resp.text

        items = resp.json()
        assert isinstance(items, list)
        assert len(items) == 1

        item = items[0]
        assert item["expense_id"] == expense_id
        assert item["description"] == "Grocery run"
        assert item["category"] == "Grocery"
        assert item["creator_username"] == "Alice"
        assert item["amount_total"] == 20.0
        assert item["amount_owed"] == 20.0
        assert item["paid_amount"] == 0.0
        assert item["outstanding_amount"] == 20.0

    def test_does_not_return_fully_paid_shares(self, client, db):
        expense_id, _, headers_bob = _setup_household_and_expense(client, db)

        pay = client.post(
            f"/api/v1/expenses/{expense_id}/confirm-payment",
            json={"amount": 20.0},
            headers=headers_bob,
        )
        assert pay.status_code == 200, pay.text

        resp = client.get("/api/v1/expenses/outstanding", headers=headers_bob)
        assert resp.status_code == 200, resp.text
        assert resp.json() == []
