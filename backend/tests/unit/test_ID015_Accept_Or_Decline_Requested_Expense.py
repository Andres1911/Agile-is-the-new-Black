from app.models.models import Expense, ExpenseShare, Household, HouseholdMember, User, VoteStatus
from tests.conftest import auth_header, create_expense, register


def _setup_household_and_expense(client, db):
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

    household = Household(name="MapleHouse", invite_code="MAP101", description="Test")
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
        "category": "Food",
        "split_evenly": False,
        "include_creator": False,
        "manual_shares": [
            {"user_id": bob.id, "amount": 20.0},
            {"user_id": cara.id, "amount": 40.0},
        ],
    }
    resp = create_expense(client, headers_alice, payload)
    assert resp.status_code == 201

    expense = (
        db.query(Expense)
        .filter(Expense.creator_id == alice.id, Expense.household_id == household.id)
        .order_by(Expense.id.desc())
        .first()
    )
    assert expense is not None

    return expense.id, headers_bob, headers_cara


class TestID015RespondExpenseShare:
    def test_ID015_household_member_accepts_pending_share(self, client, db):
        expense_id, headers_bob, _ = _setup_household_and_expense(client, db)

        resp = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "accept"},
            headers=headers_bob,
        )

        assert resp.status_code == 200
        assert resp.json()["detail"] == "Expense share accepted"

        bob = db.query(User).filter(User.username == "Bob").first()
        share = (
            db.query(ExpenseShare)
            .filter(
                ExpenseShare.expense_id == expense_id,
                ExpenseShare.user_id == bob.id,
            )
            .first()
        )
        assert share.vote_status == VoteStatus.ACCEPTED

    def test_ID015_household_member_declines_pending_share(self, client, db):
        expense_id, _, headers_cara = _setup_household_and_expense(client, db)

        resp = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "decline"},
            headers=headers_cara,
        )

        assert resp.status_code == 200
        assert resp.json()["detail"] == "Expense share declined"

        cara = db.query(User).filter(User.username == "Cara").first()
        share = (
            db.query(ExpenseShare)
            .filter(
                ExpenseShare.expense_id == expense_id,
                ExpenseShare.user_id == cara.id,
            )
            .first()
        )
        assert share.vote_status == VoteStatus.REJECTED

    def test_ID015_household_member_attempts_to_accept_rejected_share(self, client, db):
        expense_id, _, headers_cara = _setup_household_and_expense(client, db)

        first_resp = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "decline"},
            headers=headers_cara,
        )
        assert first_resp.status_code == 200

        second_resp = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "accept"},
            headers=headers_cara,
        )

        assert second_resp.status_code == 400
        assert second_resp.json()["detail"] == "Cannot accept a rejected expense"

    def test_ID015_household_member_attempts_to_decline_accepted_share(self, client, db):
        expense_id, headers_bob, _ = _setup_household_and_expense(client, db)

        first_resp = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "accept"},
            headers=headers_bob,
        )
        assert first_resp.status_code == 200

        second_resp = client.post(
            f"/api/v1/expenses/{expense_id}/respond-share",
            json={"decision": "decline"},
            headers=headers_bob,
        )

        assert second_resp.status_code == 400
        assert second_resp.json()["detail"] == "Cannot reject an already accepted expense"
