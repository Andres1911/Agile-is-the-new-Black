import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from main import app

# Place the test database in the OS temp directory so it never
# appears inside the project tree (and can never be committed).
_TEST_DB_PATH = Path(tempfile.gettempdir()) / "expense_tracker_test.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{_TEST_DB_PATH}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ── shared fixtures ───────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


# ── shared helpers ────────────────────────────────────────────────────────


def register(
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


def login(client, username="testuser", password="testpass123"):
    return client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )


def auth_header(client, **kwargs):
    token = login(client, **kwargs).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Expense handling ────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db():
    """管理数据库生命周期"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def create_expense(client, headers, payload):
    """发送创建账单请求"""
    return client.post(
        "/api/v1/expenses/create-and-split", 
        json=payload, 
        headers=headers
    )