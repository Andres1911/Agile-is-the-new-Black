"""Unit tests for resolving disputed expenses (ID016)."""


from app.models.models import Expense, ExpenseShare, ExpenseStatus, User, VoteStatus
from tests.conftest import auth_header, register


def _setup_household_and_disputed_expense(client, db):
    """
    Registers Alice (Admin), Bob, and Cara.
    Creates a household and an expense created by Alice.
    Forces the expense into a DISPUTED state with Bob and Cara's shares REJECTED.
    Returns (expense_id, headers_alice, headers_bob, headers_cara).
    """
    from app.models.models import Household, HouseholdMember
    from datetime import datetime, UTC


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


    # 1. Create Household and Members
    household = Household(name="MapleHouse", invite_code="MAPLE101", description="Test")
    db.add(household)
    db.flush()
    # Alice is ADMIN
    db.add(HouseholdMember(user_id=alice.id, household_id=household.id, is_admin=True))
    db.add(HouseholdMember(user_id=bob.id, household_id=household.id, is_admin=False))
    db.add(HouseholdMember(user_id=cara.id, household_id=household.id, is_admin=False))
    db.commit()


    # 2. Setup Headers for API calls
    headers_alice = auth_header(client, username="Alice", password="Password123!")
    headers_bob = auth_header(client, username="Bob", password="Password123!")
    headers_cara = auth_header(client, username="Cara", password="Password123!")


    # 3. Directly create a DISPUTED expense in the DB (bypassing API for faster setup)
    expense = Expense(
        description="Internet Bill",
        amount=60.0,
        status=ExpenseStatus.DISPUTED,
        household_id=household.id,
        creator_id=alice.id,
        date=datetime.now(UTC)
    )
    db.add(expense)
    db.flush()


    # Add Rejected Shares
    share_bob = ExpenseShare(
        expense_id=expense.id, user_id=bob.id, amount_owed=20.0,
        paid_amount=0.0, is_paid=False, vote_status=VoteStatus.REJECTED
    )
    share_cara = ExpenseShare(
        expense_id=expense.id, user_id=cara.id, amount_owed=20.0,
        paid_amount=0.0, is_paid=False, vote_status=VoteStatus.REJECTED
    )
    db.add(share_bob)
    db.add(share_cara)
    db.commit()


    return expense.id, headers_alice, headers_bob, headers_cara




class TestResolveDisputedExpenseSuccess:
    """Normal flows: Admin validates or invalidates."""


    def test_ID016_admin_validates_disputed_expense(self, client, db):
        expense_id, headers_alice, _, _ = _setup_household_and_disputed_expense(client, db)


        resp = client.post(
            f"/api/v1/expenses/{expense_id}/resolve",
            json={"decision": "VALID"},
            headers=headers_alice,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["detail"] == "Expense validated by admin"


        # Verify DB State Changes
        db.expire_all()
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        assert expense.status == ExpenseStatus.PENDING


        shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()
        assert all(s.vote_status == VoteStatus.ACCEPTED for s in shares)


    def test_ID016_admin_invalidates_disputed_expense(self, client, db):
        expense_id, headers_alice, _, _ = _setup_household_and_disputed_expense(client, db)


        resp = client.post(
            f"/api/v1/expenses/{expense_id}/resolve",
            json={"decision": "INVALID"},
            headers=headers_alice,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["detail"] == "Expense dismissed by admin"


        # Verify DB State Changes
        db.expire_all()
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        assert expense.status == ExpenseStatus.REJECTED


        shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()
        assert all(s.vote_status == VoteStatus.REJECTED for s in shares)




class TestResolveDisputedExpenseErrors:
    """Error flows: Non-admins, wrong status, wrong household."""


    def test_ID016_non_admin_cannot_resolve(self, client, db):
        expense_id, _, headers_bob, _ = _setup_household_and_disputed_expense(client, db)


        resp = client.post(
            f"/api/v1/expenses/{expense_id}/resolve",
            json={"decision": "VALID"},
            headers=headers_bob,
        )
        assert resp.status_code == 403
        assert "Access denied: Only admins can resolve disputed expenses" in resp.json()["detail"]


        # Ensure state didn't change
        db.expire_all()
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        assert expense.status == ExpenseStatus.DISPUTED


    def test_ID016_admin_cannot_resolve_non_disputed_expense(self, client, db):
        expense_id, headers_alice, _, _ = _setup_household_and_disputed_expense(client, db)


        # Force status to PENDING
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        expense.status = ExpenseStatus.PENDING
        db.commit()


        resp = client.post(
            f"/api/v1/expenses/{expense_id}/resolve",
            json={"decision": "VALID"},
            headers=headers_alice,
        )
        assert resp.status_code == 400
        assert "Cannot resolve: Expense is not in a disputed state" in resp.json()["detail"]


    def test_ID016_expense_not_found(self, client, db):
        _, headers_alice, _, _ = _setup_household_and_disputed_expense(client, db)


        resp = client.post(
            f"/api/v1/expenses/999999/resolve",
            json={"decision": "VALID"},
            headers=headers_alice,
        )
        assert resp.status_code == 404
        assert "Expense not found" in resp.json()["detail"]