"""Unit tests for auth edge cases not covered by acceptance tests.

The happy-path register / login flows are exercised thoroughly by the
BDD acceptance tests (ID001, ID002).  This file focuses on edge cases
and internal implementation details that acceptance tests don't reach.
"""

from app.core.security import create_access_token
from tests.conftest import auth_header, login, register


# ── login: edge cases ─────────────────────────────────────────────────────


class TestLoginEdgeCases:
    def test_token_contains_correct_subject(self, client):
        register(client)
        from jose import jwt
        from app.core.config import settings

        token = login(client).json()["access_token"]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "testuser"

    def test_inactive_user_rejected(self, client):
        """An inactive user should be rejected even with correct credentials."""
        register(client)
        from tests.conftest import TestingSessionLocal
        from app.models.models import User as UserModel

        db = TestingSessionLocal()
        user = db.query(UserModel).filter(UserModel.username == "testuser").first()
        user.is_active = False
        db.commit()
        db.close()

        resp = login(client)
        assert resp.status_code == 400
        assert "inactive" in resp.json()["detail"].lower()


# ── get_current_user: edge cases ──────────────────────────────────────────


class TestGetCurrentUserEdgeCases:
    def test_invalid_token_returns_401(self, client):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer totally.invalid.token"},
        )
        assert resp.status_code == 401

    def test_nonexistent_user_in_token_returns_401(self, client):
        token = create_access_token(data={"sub": "no_such_user"})
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    def test_token_without_sub_returns_401(self, client):
        token = create_access_token(data={"role": "admin"})
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
