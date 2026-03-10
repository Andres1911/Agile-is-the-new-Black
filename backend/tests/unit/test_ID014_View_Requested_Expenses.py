"""Unit tests for viewing requested expenses awaiting approval (ID014 / TID079)."""

from app.models.models import Expense, User
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


class TestViewRequestedExpenses:
    """Normal, alternative, and error flows for viewing requested expenses."""

    def test_ID014_view_requested_expenses_lists_pending_shares_for_current_user(
        self, client, db
    ):
        expense_id, _, headers_bob, _ = _setup_household_and_expense(client, db)

        resp = client.get("/api/v1/expenses/requested", headers=headers_bob)
        assert resp.status_code == 200, resp.text

        items = resp.json()
        assert isinstance(items, list)
        assert len(items) == 1

        item = items[0]
        assert item["expense_id"] == expense_id
        assert item["description"] == "Grocery run"
        assert item["category"] == "Grocery"
        assert item["creator_username"] == "Alice"
        assert item["amount_total"] == 60.0
        assert item["amount_requested"] == 20.0
        assert item["vote_status"] == "PENDING"

    def test_ID014_view_requested_expenses_does_not_return_already_accepted_shares(
        self, client, db
    ):
        expense_id, _, headers_bob, _ = _setup_household_and_expense(client, db)

        respond = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "accept"},
            headers=headers_bob,
        )
        assert respond.status_code == 200, respond.text

        resp = client.get("/api/v1/expenses/requested", headers=headers_bob)
        assert resp.status_code == 200, resp.text
        assert resp.json() == []

    def test_ID014_view_requested_expenses_does_not_return_rejected_shares(
        self, client, db
    ):
        expense_id, _, headers_bob, _ = _setup_household_and_expense(client, db)

        respond = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "decline"},
            headers=headers_bob,
        )
        assert respond.status_code == 200, respond.text

        resp = client.get("/api/v1/expenses/requested", headers=headers_bob)
        assert resp.status_code == 200, resp.text
        assert resp.json() == []

    def test_ID014_view_requested_expenses_returns_empty_for_member_with_no_pending_requests(
        self, client, db
    ):
        _setup_household_and_expense(client, db)

        headers_alice = auth_header(client, username="Alice", password="Password123!")
        resp = client.get("/api/v1/expenses/requested", headers=headers_alice)

        assert resp.status_code == 200, resp.text
        assert resp.json() == []

    def test_ID014_view_requested_expenses_user_not_in_household_rejected(
        self, client, db
    ):
        _setup_household_and_expense(client, db)

        register(
            client,
            email="outsider@test.com",
            username="Outsider",
            password="Password123!",
            full_name="Outsider",
        )
        headers_outsider = auth_header(client, username="Outsider", password="Password123!")

        resp = client.get("/api/v1/expenses/requested", headers=headers_outsider)
        assert resp.status_code == 400
        assert "not a member of any household" in resp.json()["detail"].lower()
