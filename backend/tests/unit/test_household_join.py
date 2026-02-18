
from app.models.models import Household, HouseholdMember
from app.models.models import User as UserModel
from tests.conftest import TestingSessionLocal, login, register


class TestJoinHouseholdFlows:

    # --- Normal Flow ---

    def test_join_household_success(self, client):
        """Scenario: Guest joins a household with correct credentials."""
        # Setup
        register(client, username="Charlie", email="charlie@test.com")
        auth_resp = login(client, username="Charlie")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        db = TestingSessionLocal()
        target_house = Household(name="The North Star", invite_code="MYHOUSE2024")
        db.add(target_house)
        db.commit()
        db.refresh(target_house)

        user = db.query(UserModel).filter(UserModel.username == "Charlie").first()
        user_id = user.id
        db.close()

        payload = {
            "household_name": "The North Star",
            "invite_code": "MYHOUSE2024"
        }
        resp = client.post("/api/v1/households/join", json=payload, headers=headers)

        # Assertions
        assert resp.status_code == 200
        assert resp.json()["message"] == "Success"

        # Verify DB Binding matches the model
        db_check = TestingSessionLocal()
        binding = db_check.query(HouseholdMember).filter(
            HouseholdMember.user_id == user_id,
            HouseholdMember.household_id == target_house.id
        ).first()

        assert binding is not None
        assert binding.left_at is None
        assert binding.is_admin is False
        db_check.close()

    # --- Error Flows ---

    def test_join_with_incorrect_invite_code(self, client):
        """Scenario: Attempt to join with an incorrect invite code."""
        register(client, username="Charlie_Fail", email="cfail@test.com")
        auth_resp = login(client, username="Charlie_Fail")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        db = TestingSessionLocal()
        h = Household(name="The North Star", invite_code="REAL_CODE")
        db.add(h)
        db.commit()
        db.close()

        payload = {"household_name": "The North Star", "invite_code": "WRONG666"}
        resp = client.post("/api/v1/households/join", json=payload, headers=headers)

        assert resp.status_code == 400
        assert "invalid invite code" in resp.json()["detail"].lower()

    def test_already_in_household_prevented(self, client):
        """Scenario: Already-in-household user attempts to join another."""
        register(client, username="Charlie_Busy", email="busy@test.com")
        auth_resp = login(client, username="Charlie_Busy")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        db = TestingSessionLocal()
        user = db.query(UserModel).filter(UserModel.username == "Charlie_Busy").first()

        home1 = Household(name="The North Star", invite_code="STARS")
        home2 = Household(name="DowntownLoft", invite_code="LOFTSUITE123")
        db.add_all([home1, home2])
        db.flush()

        # Add Charlie to the first home
        db.add(HouseholdMember(user_id=user.id, household_id=home1.id, is_admin=False))
        db.commit()
        db.close()

        payload = {"household_name": "DowntownLoft", "invite_code": "LOFTSUITE123"}
        resp = client.post("/api/v1/households/join", json=payload, headers=headers)

        assert resp.status_code == 400
        assert "already registered as living in another household" in resp.json()["detail"].lower()
