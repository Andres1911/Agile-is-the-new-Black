import pytest
from datetime import datetime, UTC
from fastapi import status
from app.models.models import Household, HouseholdMember
from app.models.models import User as UserModel
from tests.conftest import TestingSessionLocal, login, register

class TestCreateHousehold:
    
    def test_create_household_success(self, client):
        #arrange
        register(client, username="alice", email="alice@test.com")
        auth_resp = login(client, username="alice")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        #act
        payload = {
            "name": "Agile Manor",
            "description": "A test household",
            "address": "123 University St"
        }
        response = client.post("/api/v1/households/", json=payload, headers=headers)

        #assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Agile Manor"
        assert len(data["invite_code"]) == 8

        #DB Check
        db = TestingSessionLocal()
        user = db.query(UserModel).filter(UserModel.username == "alice").first()
        membership = db.query(HouseholdMember).filter(
            HouseholdMember.household_id == data["id"],
            HouseholdMember.user_id == user.id
        ).first()
        assert membership is not None
        assert membership.is_admin is True
        db.close()

    def test_create_household_after_leaving_previous(self, client):
        register(client, username="leaver", email="leaver@test.com")
        auth_resp = login(client, username="leaver")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        db = TestingSessionLocal()
        user = db.query(UserModel).filter(UserModel.username == "leaver").first()
        
        # Setup an old household that they already left
        old_hh = Household(name="Old Home", invite_code="BYEBYE12")
        db.add(old_hh)
        db.flush()
        db.add(HouseholdMember(user_id=user.id, household_id=old_hh.id, left_at=datetime.now(UTC)))
        db.commit()

        # Try creating new one
        payload = {"name": "Fresh Start"}
        response = client.post("/api/v1/households/", json=payload, headers=headers)

        assert response.status_code == status.HTTP_201_CREATED
        memberships = db.query(HouseholdMember).filter(HouseholdMember.user_id == user.id).all()
        assert len(memberships) == 2
        db.close()

    def test_create_household_duplicate_name(self, client):
        register(client, username="tester", email="tester@test.com")
        auth_resp = login(client, username="tester")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        db = TestingSessionLocal()
        db.add(Household(name="Duplicate", invite_code="CODE1234"))
        db.commit()

        payload = {"name": "Duplicate", "description": "Should fail"}
        response = client.post("/api/v1/households/", json=payload, headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name already exists" in response.json()["detail"].lower()
        db.close()

    def test_create_household_already_in_one(self, client):
        register(client, username="active_user", email="active@test.com")
        auth_resp = login(client, username="active_user")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        db = TestingSessionLocal()
        user = db.query(UserModel).filter(UserModel.username == "active_user").first()
        h = Household(name="Current Home", invite_code="ALREADY1")
        db.add(h)
        db.flush()
        db.add(HouseholdMember(user_id=user.id, household_id=h.id, is_admin=True))
        db.commit()

        payload = {"name": "New House"}
        response = client.post("/api/v1/households/", json=payload, headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "user is already registered as living in another household" in response.json()["detail"].lower()
        db.close()

    def test_create_household_unauthorized(self, client):
        # No login, no headers
        payload = {"name": "Ghost House"}
        response = client.post("/api/v1/households/", json=payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_household_missing_fields(self, client):
        register(client, username="bad_data", email="bad@test.com")
        auth_resp = login(client, username="bad_data")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        payload = {"description": "Missing the name field"}
        response = client.post("/api/v1/households/", json=payload, headers=headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_household_long_strings(self, client):
        register(client, username="long_str", email="long@test.com")
        auth_resp = login(client, username="long_str")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        payload = {
            "name": "Big House", 
            "description": "A" * 1000,
            "address": "B" * 1000
        }
        response = client.post("/api/v1/households/", json=payload, headers=headers)
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["name"] == "Big House"
        assert data["description"] == "A" * 1000
        assert data["address"] == "B" * 1000


    def test_create_household_trims_whitespace(self, client):
        register(client, username="trim_user", email="trim@test.com")
        auth_resp = login(client, username="trim_user")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        payload = {
            "name": "  Space House  ",  #spaces on both sides
            "description": "Cleaning up"
        }
        response = client.post("/api/v1/households/", json=payload, headers=headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["name"] == "Space House" #should be trimmed

    def test_create_household_unicode_support(self, client):
        register(client, username="euro_user", email="euro@test.com")
        auth_resp = login(client, username="euro_user")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        payload = {"name": "Maison d'Été 🏡"}
        response = client.post("/api/v1/households/", json=payload, headers=headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["name"] == "Maison d'Été 🏡"