from datetime import UTC, datetime

from fastapi import status

from tests.conftest import login, register


class TestRecurringExpenseApiValidation:
    def test_ID018_solo_household_member_cannot_create_recurring_expense(self, client):
        register(client, username="solo_admin", email="solo_admin@test.com")
        auth_resp = login(client, username="solo_admin")
        headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}

        # Create household (creator becomes admin + only active member)
        create_household_resp = client.post(
            "/api/v1/households/",
            json={"name": "SoloHouse", "description": "", "address": ""},
            headers=headers,
        )
        assert create_household_resp.status_code == status.HTTP_201_CREATED

        payload = {
            "amount": 10.0,
            "description": "Solo recurring",
            "category": None,
            "split_evenly": True,
            "include_creator": False,
            "manual_shares": None,
            "interval": 1,
            "unit": "WEEKLY",
            "start_at": datetime(2026, 3, 29, tzinfo=UTC).isoformat(),
            # no end condition needed; we just want to trigger generation
        }

        resp = client.post(
            "/api/v1/expenses/recurring",
            json=payload,
            headers=headers,
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "no active members" in resp.json()["detail"].lower()
