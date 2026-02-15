"""Unit tests for app.core.security – pure functions, no DB needed."""

from datetime import timedelta

from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password

# ── verify_password ───────────────────────────────────────────────────────


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        hashed = get_password_hash("Secret123!")
        assert verify_password("Secret123!", hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = get_password_hash("Secret123!")
        assert verify_password("WrongPassword", hashed) is False

    def test_empty_password_returns_false(self):
        hashed = get_password_hash("Secret123!")
        assert verify_password("", hashed) is False

    def test_case_sensitive_password(self):
        hashed = get_password_hash("Secret123!")
        assert verify_password("secret123!", hashed) is False


# ── get_password_hash ─────────────────────────────────────────────────────


class TestGetPasswordHash:
    def test_returns_bcrypt_hash(self):
        h = get_password_hash("mypassword")
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_different_calls_produce_different_hashes(self):
        h1 = get_password_hash("same")
        h2 = get_password_hash("same")
        assert h1 != h2  # bcrypt uses a random salt

    def test_hash_is_verifiable(self):
        password = "Complex!Pa55"
        h = get_password_hash(password)
        assert verify_password(password, h) is True


# ── create_access_token ───────────────────────────────────────────────────


class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token(data={"sub": "alice"})
        assert isinstance(token, str)

    def test_token_contains_subject(self):
        token = create_access_token(data={"sub": "alice"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "alice"

    def test_token_contains_expiry(self):
        token = create_access_token(data={"sub": "bob"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_custom_expiry_delta(self):
        token = create_access_token(data={"sub": "carol"}, expires_delta=timedelta(minutes=5))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_default_expiry_when_none(self):
        token = create_access_token(data={"sub": "dave"}, expires_delta=None)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_extra_data_preserved(self):
        token = create_access_token(data={"sub": "eve", "role": "admin"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["role"] == "admin"
