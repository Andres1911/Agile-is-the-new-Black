"""Step definitions for ID001_Add_New_User.feature."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import login
from tests.conftest import register as _register_helper

# ---------------------------------------------------------------------------
scenarios("features/ID001_Add_New_User.feature")


# ---------------------------------------------------------------------------
@pytest.fixture()
def context():
    return {}


# ── GIVEN ─────────────────────────────────────────────────────────────────


@given(parsers.parse('the system has no user with email "{email}"'))
def given_no_user_with_email(client, email):
    """Fresh DB per test — nothing to do."""


@given(parsers.parse('the system has no user with username "{username}"'))
def given_no_user_with_username(client, username):
    """Fresh DB per test — nothing to do."""


@given(
    parsers.parse('a user with username "{username}" exists'),
    target_fixture="context",
)
def given_user_with_username_exists(client, username, context):
    email = f"{username.lower()}_seed@test.com"
    resp = _register_helper(
        client, email=email, username=username, password="SeedPass1!", full_name=username
    )
    assert resp.status_code == 200, f"Seed user creation failed: {resp.text}"
    return context


@given(
    parsers.parse('a user with email "{email}" already exists'),
    target_fixture="context",
)
def given_user_with_email_exists(client, email, context):
    username = f"{email.split('@')[0]}_seed"
    resp = _register_helper(
        client, email=email, username=username, password="SeedPass1!", full_name=username
    )
    assert resp.status_code == 200, f"Seed user creation failed: {resp.text}"
    return context


# ── WHEN ──────────────────────────────────────────────────────────────────


@when(parsers.parse('the password "{password}" is valid (at least 8 characters)'))
def when_password_valid(password):
    assert len(password) >= 8, f"Test data error: '{password}' should be >= 8 chars"


@when(parsers.parse('the password "{password}" is invalid (less than 8 characters)'))
def when_password_invalid(password):
    assert len(password) < 8, f"Test data error: '{password}' should be < 8 chars"


@when(
    parsers.parse(
        'a registration is requested with username "{username}" and email "{email}" and password "{password}"'
    ),
    target_fixture="context",
)
def when_register_requested(client, username, email, password, context):
    resp = _register_helper(
        client, email=email, username=username, password=password, full_name=username
    )
    context["response"] = resp
    context["password"] = password  # Store password for later verification
    return context


# ── THEN ──────────────────────────────────────────────────────────────────


@then(
    parsers.parse(
        'the account with email "{email}" and username "{username}" and password "{password}" is successfully created'
    ),
)
def then_account_created(context, email, username, password):
    resp = context["response"]
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["email"] == email
    assert data["username"] == username
    assert data["is_active"] is True
    assert "password" not in data


@then(parsers.parse('the message "{message}" is issued'))
def then_success_message(context, message):
    assert context["response"].status_code == 200


@then(parsers.parse('a user record for "{username}" should exist'))
def then_user_record_exists(client, context, username):
    """Verify the user can actually log in (proving the record was persisted and password was hashed correctly)."""
    # Retrieve the password that was stored during registration
    password = context.get("password")
    assert password, "Password must be stored in context during registration step"

    # Verify the user can log in with the password they registered with
    login_resp = login(client, username=username, password=password)
    assert login_resp.status_code == 200, (
        f"User {username} was created but cannot log in with the registered password. "
        f"Status: {login_resp.status_code}, Response: {login_resp.text}"
    )
    # Verify the login response contains an access token
    login_data = login_resp.json()
    assert "access_token" in login_data, "Login successful but no access token returned"


@then(parsers.parse('the account with email "{identifier}" should not be created'))
def then_account_not_created(context, identifier):
    resp = context["response"]
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"


@then(parsers.parse('the error message "{error_msg}" is returned'))
def then_error_message(context, error_msg):
    resp = context["response"]
    detail = resp.json()["detail"]
    assert detail == error_msg, f"Expected '{error_msg}', got '{detail}'"
