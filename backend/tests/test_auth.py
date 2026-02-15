from tests.conftest import auth_header, login, register


# ── register ──────────────────────────────────────────────────────────────


def test_register_user(client):
    response = register(client)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert data["is_active"] is True
    assert "password" not in data


def test_register_duplicate_email(client):
    register(client)
    response = register(client, username="other")
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_register_duplicate_username(client):
    register(client)
    response = register(client, email="other@example.com")
    assert response.status_code == 400
    assert "Username already taken" in response.json()["detail"]


# ── login ─────────────────────────────────────────────────────────────────


def test_login_user(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    register(client)
    response = login(client, password="wrong")
    assert response.status_code == 401


def test_login_unknown_user(client):
    response = login(client, username="ghost")
    assert response.status_code == 401


# ── me ────────────────────────────────────────────────────────────────────


def test_get_current_user(client):
    register(client)
    headers = auth_header(client)
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["is_active"] is True


def test_me_without_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
