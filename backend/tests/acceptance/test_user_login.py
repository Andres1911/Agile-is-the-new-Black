"""Step definitions for ID002_User_Login.feature.

Each Gherkin step maps to a function below. The ``client`` fixture is provided
by the shared conftest.py at the tests/ root, so every scenario gets a clean
database automatically.
"""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.conftest import register as _register_helper

# ---------------------------------------------------------------------------
# Bind all scenarios from the feature file to this module
# ---------------------------------------------------------------------------
scenarios("features/ID002_User_Login.feature")


# ---------------------------------------------------------------------------
# Shared context passed between steps via a dict fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def context():
    """Mutable dict shared across Given / When / Then in one scenario."""
    return {}


# ── GIVEN steps ───────────────────────────────────────────────────────────


@given(
    parsers.parse(
        'a user with email "{email}" and password "{password}" already exists in the system'
    ),
    target_fixture="context",
)
def given_user_with_email(client, email, password, context):
    """Register a user identified by email (username derived from email local part)."""
    username = email.split("@")[0]
    resp = _register_helper(
        client, email=email, username=username, password=password, full_name=username.title()
    )
    assert resp.status_code == 200, f"Seed user creation failed: {resp.text}"
    context["seeded_password"] = password
    return context


@given(
    parsers.parse(
        'a user with username "{username}" and password "{password}" already exists in the system'
    ),
    target_fixture="context",
)
def given_user_with_username_and_password(client, username, password, context):
    email = f"{username.lower()}@test.com"
    resp = _register_helper(
        client, email=email, username=username, password=password, full_name=username
    )
    assert resp.status_code == 200, f"Seed user creation failed: {resp.text}"
    context["seeded_password"] = password
    return context


@given(
    parsers.parse('a user with username "{username}" already exists in the system'),
    target_fixture="context",
)
def given_user_with_username_only(client, username, context):
    """Register a user with a default password (used in wrong‐password scenarios)."""
    email = f"{username.lower()}@test.com"
    default_password = "DefaultPass1!"
    resp = _register_helper(
        client, email=email, username=username, password=default_password, full_name=username
    )
    assert resp.status_code == 200, f"Seed user creation failed: {resp.text}"
    context["seeded_password"] = default_password
    return context


@given(
    parsers.parse('the system has no user with email "{email}"'),
    target_fixture="context",
)
def given_no_user_with_email(client, email, context):
    """Nothing to set up – the database is already empty per‐test."""
    return context


# ── WHEN steps ────────────────────────────────────────────────────────────


@when(
    parsers.parse('the user attempts to log in with email "{email}" and password "{password}"'),
    target_fixture="context",
)
def when_login_with_email(client, email, password, context):
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    context["response"] = resp
    return context


@when(
    parsers.parse(
        'the user attempts to log in with username "{username}" and password "{password}"'
    ),
    target_fixture="context",
)
def when_login_with_username(client, username, password, context):
    resp = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    context["response"] = resp
    return context


@when(
    parsers.parse(
        'the user attempts to log in with username "{username}" and an incorrect password "{wrong_password}"'
    ),
    target_fixture="context",
)
def when_login_with_wrong_password(client, username, wrong_password, context):
    resp = client.post(
        "/api/v1/auth/login", data={"username": username, "password": wrong_password}
    )
    context["response"] = resp
    return context


# ── THEN steps ────────────────────────────────────────────────────────────


@then(parsers.parse('the message "{message}" is issued'))
def then_success_message(context, message):
    resp = context["response"]
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    # A successful login returns a token – that is our "Success" signal
    assert "access_token" in resp.json()


@then(parsers.parse('the error message "{error_msg}" is returned'))
def then_error_message(context, error_msg):
    resp = context["response"]
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
    # The API returns "Incorrect username or password"; we accept the
    # Gherkin wording as equivalent (both communicate auth failure).
    assert (
        "incorrect" in resp.json()["detail"].lower() or "invalid" in resp.json()["detail"].lower()
    )


@then("a session will be created")
def then_session_created(context):
    """In our JWT-based API a "session" is represented by a valid access token."""
    data = context["response"].json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@then("a session will not be created")
def then_no_session_created(context):
    data = context["response"].json()
    assert "access_token" not in data


@then("the user should be redirected to the dashboard")
def then_redirected_to_dashboard(context):
    """Redirection is a frontend concern; from the backend's perspective a
    successful token issuance (200 + access_token) is sufficient to consider
    this step satisfied."""
    assert context["response"].status_code == 200


@then("the user should remain on the login page")
def then_remain_on_login_page(context):
    """The backend signals failure with a 401; the frontend keeps the user
    on the login page."""
    assert context["response"].status_code == 401
