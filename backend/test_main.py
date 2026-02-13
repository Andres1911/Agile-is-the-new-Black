import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from main import app

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ── helpers ───────────────────────────────────────────────────────────────


def _register(
    client,
    email="test@example.com",
    username="testuser",
    password="testpass123",
    full_name="Test User",
):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "full_name": full_name,
        },
    )


def _login(client, username="testuser", password="testpass123"):
    return client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )


def _auth_header(client, **kwargs):
    token = _login(client, **kwargs).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


# ── general ───────────────────────────────────────────────────────────────


def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


# ── auth: register ────────────────────────────────────────────────────────


def test_register_user(client):
    response = _register(client)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert data["is_active"] is True
    assert "password" not in data


def test_register_duplicate_email(client):
    _register(client)
    response = _register(client, username="other")
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_register_duplicate_username(client):
    _register(client)
    response = _register(client, email="other@example.com")
    assert response.status_code == 400
    assert "Username already taken" in response.json()["detail"]


# ── auth: login ───────────────────────────────────────────────────────────


def test_login_user(client):
    _register(client)
    response = _login(client)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    _register(client)
    response = _login(client, password="wrong")
    assert response.status_code == 401


def test_login_unknown_user(client):
    response = _login(client, username="ghost")
    assert response.status_code == 401


# ── auth: me ──────────────────────────────────────────────────────────────


def test_get_current_user(client):
    _register(client)
    headers = _auth_header(client)
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["is_active"] is True


def test_me_without_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
