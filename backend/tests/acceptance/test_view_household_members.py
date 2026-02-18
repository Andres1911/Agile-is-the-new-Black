"""Acceptance tests for ID008 — View Household Member List.

Binds to: features/ID008_View_Household_Member_list.feature
"""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.models.models import Household, HouseholdMember
from app.models.models import User as UserModel
from tests.conftest import auth_header as get_auth_header
from tests.conftest import register as register_user

scenarios("features/ID008_View_Household_Member_list.feature")

@pytest.fixture()
def context():
    return {}

def _get_table_dicts(datatable):
    keys = datatable[0]
    return [dict(zip(keys, row)) for row in datatable[1:]]

@given(parsers.parse('household "{household_name}" exists with members'), target_fixture="household_ctx")
def given_household_with_members(client, db, household_name, datatable):
    """Create the household and its members from the Background table."""
    rows = _get_table_dicts(datatable)  # [{member, role}, ...]

    user_objects = []
    for row in rows:
        name = row["member"]
        register_user(
            client,
            email=f"{name.lower()}@test.com",
            username=name,
            password="Password123!",
            full_name=name,
        )
        user = db.query(UserModel).filter(UserModel.username == name).first()
        user_objects.append((user, row["role"]))

    new_household = Household(
        name=household_name,
        invite_code="MAPLE001",
        description="Test Household",
    )
    db.add(new_household)
    db.flush()

    for user, role in user_objects:
        is_admin = role == "owner"
        db.add(HouseholdMember(user_id=user.id, household_id=new_household.id, is_admin=is_admin))

    db.commit()

    return {"household": new_household, "members": user_objects}


@given(parsers.parse('user "{username}" is authenticated as a household member'), target_fixture="context")
def given_user_authenticated(client, context, username):
    context["auth_headers"] = get_auth_header(client, username=username, password="Password123!")
    context["current_user"] = username
    return context


@given(parsers.parse('user "{username}" is authenticated and exists in the system'), target_fixture="context")
def given_user_exists_not_member(client, db, context, username):
    register_user(
        client,
        email=f"{username.lower()}@test.com",
        username=username,
        password="Password123!",
        full_name=username,
    )
    context["auth_headers"] = get_auth_header(client, username=username, password="Password123!")
    context["current_user"] = username
    return context


@given(parsers.parse('user "{username}" is not a member of household "{household_name}"'))
def given_user_not_a_member(db, username, household_name):
    """Verify that Dave has no membership record — nothing to do since we never added him."""
    user = db.query(UserModel).filter(UserModel.username == username).first()
    household = db.query(Household).filter(Household.name == household_name).first()
    if user and household:
        membership = db.query(HouseholdMember).filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == household.id,
        ).first()
        assert membership is None, f"{username} should not be in {household_name}"


@given("no user is authenticated", target_fixture="context")
def given_no_user_authenticated(context):
    context["auth_headers"] = None
    return context


@given(parsers.parse('no household with name "{household_name}" exists in the system'))
def given_household_does_not_exist(db, household_name):
    existing = db.query(Household).filter(Household.name == household_name).first()
    assert existing is None, f"Household '{household_name}' should not exist"

@when(parsers.parse('"{username}" requests the member list for household "{household_name}"'), target_fixture="context")
def when_request_member_list(client, db, context, username, household_name):
    household = db.query(Household).filter(Household.name == household_name).first()
    if household is None:
        # Household doesn't exist — use a sentinel ID so the API returns 404
        household_id = 99999
    else:
        household_id = household.id

    context["response"] = client.get(
        f"/api/v1/households/{household_id}/members",
        headers=context.get("auth_headers") or {},
    )
    return context


@when(parsers.parse('an unauthenticated request is made to view the member list for household "{household_name}"'), target_fixture="context")
def when_unauthenticated_request(client, db, context, household_name):
    household = db.query(Household).filter(Household.name == household_name).first()
    household_id = household.id if household else 99999

    context["response"] = client.get(f"/api/v1/households/{household_id}/members")
    return context

@then(parsers.parse('the system returns the following members for "{household_name}"'))
def then_verify_member_list(context, datatable):
    resp = context["response"]
    assert resp.status_code == 200

    expected_rows = _get_table_dicts(datatable)
    expected_usernames = {row["member"] for row in expected_rows}

    actual_members = resp.json()
    actual_usernames = {m["user"]["username"] for m in actual_members}

    assert actual_usernames == expected_usernames, (
        f"Expected members {expected_usernames}, got {actual_usernames}"
    )


@then('the message "Success" is issued')
def then_success(context):
    assert context["response"].status_code == 200


@then("the system denies the request")
def then_denied(context):
    assert context["response"].status_code in (401, 403, 404)


@then(parsers.parse('the error message "{error_msg}" is returned'))
def then_error_message(context, error_msg):
    detail = context["response"].json().get("detail", "")
    assert error_msg.lower() in detail.lower(), (
        f"Expected '{error_msg}' in response detail, got: '{detail}'"
    )
