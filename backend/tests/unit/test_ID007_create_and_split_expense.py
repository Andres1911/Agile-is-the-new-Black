from app.models.models import Expense, ExpenseShare, Household, HouseholdMember, VoteStatus
from app.models.models import User as UserModel

from ..conftest import TestingSessionLocal, login, register


class TestCreateAndSplitExpenseFailCases:
    def test_ID007_member_without_household_attempt_to_create_expense(self, client):
        """
        1. Register and login a real user.
        2. Ensure no HouseholdMember records for this user in database.
        3. Call API and assert 400.
        """
        # 1. Prepare user and get Token
        register(client, username="lonely_alice", email="alice@edge.com")
        auth_resp = login(client, username="lonely_alice")
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. DB check: ensure no household membership
        db = TestingSessionLocal()
        user = db.query(UserModel).filter(UserModel.username == "lonely_alice").first()
        # Remove any existing household links for clean state
        db.query(HouseholdMember).filter(HouseholdMember.user_id == user.id).delete()
        db.commit()
        db.close()

        # 3. Send request
        payload = {
            "description": "Solo Expense",
            "amount": 100.0,
            "category": "Grocery",
            "split_evenly": True,
            "include_creator": True,
        }
        resp = client.post("/api/v1/expenses/create-and-split", json=payload, headers=headers)

        # 4. Assert results
        assert resp.status_code == 400
        assert "not currently in any household" in resp.json()["detail"].lower()

    def test_ID007_member_attempts_to_create_expense_with_no_payer(self, client):
        """
        Test scenario: Alice is in a household, but she's the only member.
        She tries to create an expense split that doesn't include herself (include_creator=False).
        Expected result: 400 error indicating no other members to split with.
        """
        # 1. Register and login user
        register(client, username="solo_alice", email="alice_solo@test.com")
        auth_resp = login(client, username="solo_alice")
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. DB state: household with only Alice
        db = TestingSessionLocal()
        user = db.query(UserModel).filter(UserModel.username == "solo_alice").first()

        new_household = Household(name="Solo Home", invite_code="SOLO123")
        db.add(new_household)
        db.flush()

        # Only Alice as member
        db.add(HouseholdMember(user_id=user.id, household_id=new_household.id, is_admin=True))
        db.commit()
        db.close()

        # 3. Request without self (include_creator=False)
        payload = {
            "description": "Ghost Party",
            "amount": 50.0,
            "category": "Entertainment",
            "split_evenly": True,
            "include_creator": False,  # key: no self, no other members
        }
        resp = client.post("/api/v1/expenses/create-and-split", json=payload, headers=headers)

        # 4. Assert results
        assert resp.status_code == 400
        assert "no other active members" in resp.json()["detail"].lower()

    def test_ID007_member_attempts_to_create_expense_share_for_non_household_member(self, client):
        """
        Scenario: Alice (Household A) tries to assign expense share to Stranger (not in Household A).
        Expected: 400 error indicating user is not an active member of the household.
        """
        # 1. Register Alice and a stranger
        register(client, username="alice_h", email="alice_h@test.com")
        register(client, username="stranger", email="stranger@test.com")

        auth_resp = login(client, username="alice_h")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        db = TestingSessionLocal()
        alice = db.query(UserModel).filter(UserModel.username == "alice_h").first()
        stranger = db.query(UserModel).filter(UserModel.username == "stranger").first()

        # 2. Add only Alice to household
        h = Household(name="Alice's Home", invite_code="ALICE99")
        db.add(h)
        db.flush()
        db.add(HouseholdMember(user_id=alice.id, household_id=h.id))
        db.commit()

        # 3. Request: assign share to stranger.id
        payload = {
            "description": "Hack test",
            "amount": 100.0,
            "category": "Test",
            "split_evenly": False,
            "include_creator": True,
            "manual_shares": [
                {"user_id": alice.id, "amount": 50.0},
                {"user_id": stranger.id, "amount": 50.0},  # This person is not in the household
            ],
        }
        resp = client.post("/api/v1/expenses/create-and-split", json=payload, headers=headers)

        # 4. Assert
        assert resp.status_code == 400
        assert f"User {stranger.id} is not an active member" in resp.json()["detail"]
        db.close()

    def test_ID007_member_attempts_to_create_expense_share_with_zero_amount(self, client):
        """
        Scenario: Alice assigns Bob 0 or negative amount in split.
        Expected: 400 error indicating share amount must be greater than zero.
        """
        # 1. Register Alice and Bob
        register(client, username="alice_z", email="alice_z@test.com")
        register(client, username="bob_z", email="bob_z@test.com")

        auth_resp = login(client, username="alice_z")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        db = TestingSessionLocal()
        alice = db.query(UserModel).filter(UserModel.username == "alice_z").first()
        bob = db.query(UserModel).filter(UserModel.username == "bob_z").first()

        h = Household(name="Zero Home", invite_code="ZERO1")
        db.add(h)
        db.flush()
        db.add(HouseholdMember(user_id=alice.id, household_id=h.id))
        db.add(HouseholdMember(user_id=bob.id, household_id=h.id))
        db.commit()

        # 2. Request: assign Bob 0 amount
        payload = {
            "description": "Zero split test",
            "amount": 100.0,
            "category": "Test",
            "split_evenly": False,
            "include_creator": True,
            "manual_shares": [
                {"user_id": alice.id, "amount": 100.0},
                {"user_id": bob.id, "amount": 0.0},  # zero amount, invalid
            ],
        }
        resp = client.post("/api/v1/expenses/create-and-split", json=payload, headers=headers)

        # 3. Assert
        assert resp.status_code == 400
        assert f"Share for user {bob.id} must be greater than zero" in resp.json()["detail"]
        db.close()


class TestCreateAndSplitExpenseSuccessCases:
    def test_ID007_equal_split_handles_floating_point_residue_correctly(self, client):
        """
        Scenario: 5 people split 100.01 equally.
        """
        # 1. Register and login 5 users
        member_names = ["Alice", "Bob", "Cara", "David", "Eve"]
        for name in member_names:
            register(client, username=name, email=f"{name.lower()}@test.com")

        # Must define headers here
        auth_resp = login(client, username="Alice")
        token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Set up 5-member household environment
        db = TestingSessionLocal()
        users = {
            u.username: u
            for u in db.query(UserModel).filter(UserModel.username.in_(member_names)).all()
        }

        h = Household(name="Precision Home", invite_code="PREC123")
        db.add(h)
        db.flush()

        for name in member_names:
            db.add(HouseholdMember(user_id=users[name].id, household_id=h.id))
        db.commit()

        # 3. Send request
        total_amount = 100.01
        payload = {
            "description": "Precision Test",
            "amount": total_amount,
            "category": "Test",
            "split_evenly": True,
            "include_creator": True,
        }

        resp = client.post("/api/v1/expenses/create-and-split", json=payload, headers=headers)
        assert resp.status_code == 201

        # 4. Deep database verification
        # Open new session to ensure we see committed data
        db_check = TestingSessionLocal()
        expense = db_check.query(Expense).filter(Expense.description == "Precision Test").first()
        actual_shares = (
            db_check.query(ExpenseShare).filter(ExpenseShare.expense_id == expense.id).all()
        )

        assert len(actual_shares) == 5

        # Verify total (float tolerance)
        total_calculated = sum(s.amount_owed for s in actual_shares)
        assert abs(total_calculated - total_amount) == 0

        for actual in actual_shares:
            assert actual.expense_id == expense.id

            # Use db_check to get associated username for assertion
            user = db_check.get(UserModel, actual.user_id)

            if user.username == "Alice":
                assert actual.vote_status == VoteStatus.ACCEPTED
            else:
                assert actual.vote_status == VoteStatus.PENDING

            # Amount should be 20.00 or 20.01 (remainder handling)
            assert actual.amount_owed in [20.00, 20.01], (
                f"Wrong amount {actual.amount_owed} for {user.username}"
            )

        db_check.close()
