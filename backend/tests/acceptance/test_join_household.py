import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from app.models.models import User, Household, HouseholdMember
from tests.conftest import register as _register_helper, login as _login_helper

# Link to the feature file
scenarios("features/ID005_Join_A_Household.feature")

@pytest.fixture()
def context():
    """Fixture to share state between steps."""
    return {}

# GIVEN

@given(parsers.parse('another household named "{target_house}" exists with the invite code "{valid_code}"'))
def given_another_household_exists(db, target_house, valid_code):
    house = db.query(Household).filter(Household.name == target_house).first()
    if not house:
        house = Household(name=target_house, invite_code=valid_code)
        db.add(house)
        db.commit()
    else:
        house.invite_code = valid_code
        db.commit()

@given(parsers.parse('a user with username "{username}" already exists in the system'))
def given_user_exists(client, username):
    # Use helper from conftest to seed the user
    _register_helper(
        client,
        username=username,
        email=f"{username.lower()}@test.com",
        password="Password123!"
    )

@given(parsers.parse('the user "{username}" is logged in'), target_fixture="context")
def given_user_logged_in(client, username, context):
    login_resp = _login_helper(client, username=username, password="Password123!")
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    context["auth_headers"] = {"Authorization": f"Bearer {token}"}
    context["username"] = username
    return context

@given(parsers.parse('the user "{username}" does not currently belong to any household'))
def given_user_has_no_household(db, username):
    user = db.query(User).filter(User.username == username).first()
    # Ensure no active membership exists (left_at is None)
    membership = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == user.id,
        HouseholdMember.left_at.is_(None)
    ).first()
    assert membership is None

@given(parsers.parse('a household named "{household_name}" exists in the system'))
def given_household_exists(db, household_name):
    # Check if exists, or create it
    house = db.query(Household).filter(Household.name == household_name).first()
    if not house:
        house = Household(name=household_name, invite_code="TEMP_CODE")
        db.add(house)
        db.commit()

@given(parsers.parse('the household "{household_name}" has the invite code "{invite_code}"'))
def given_household_has_code(db, household_name, invite_code):
    house = db.query(Household).filter(Household.name == household_name).first()
    house.invite_code = invite_code
    db.commit()

@given(parsers.parse('the household "{household_name}" has a code that is NOT "{wrong_code}"'))
def given_household_has_different_code(db, household_name, wrong_code):
    house = db.query(Household).filter(Household.name == household_name).first()
    if house.invite_code == wrong_code:
        house.invite_code = "DIFFERENT_123"
        db.commit()

@given(parsers.parse('a household named "{fake_house}" does not exist in the system'))
def given_household_does_not_exist(db, fake_house):
    house = db.query(Household).filter(Household.name == fake_house).first()
    if house:
        db.delete(house)
        db.commit()

@given(parsers.parse('the user "{username}" is already living in the household "{current_home}"'))
def given_user_already_in_house(db, username, current_home):
    user = db.query(User).filter(User.username == username).first()
    house = Household(name=current_home, invite_code="HOME123")
    db.add(house)
    db.flush()
    # Create the binding (LiveIn = true means left_at is None)
    db.add(HouseholdMember(user_id=user.id, household_id=house.id, is_admin=True))
    db.commit()

# WHEN

@when(parsers.parse('the user requests to join household "{household_name}" with invite code "{invite_code}"'))
def when_request_join(client, context, household_name, invite_code):
    payload = {"household_name": household_name, "invite_code": invite_code}
    resp = client.post(
        "/api/v1/households/join",
        json=payload,
        headers=context["auth_headers"]
    )
    context["response"] = resp

@when(parsers.parse('the user requests to join household "{fake_house}" with any invite code "{invite_code}"'))
def when_request_join_any_code(client, context, fake_house, invite_code):
    # Reuse the same logic for the join request
    when_request_join(client, context, fake_house, invite_code)

# THEN

@then(parsers.parse('the message "{message}" is issued'))
def then_message_issued(context, message):
    resp = context["response"]
    # For Success, we expect 200. For errors, 400 or 404.
    if message == "Success":
        assert resp.status_code == 200
    else:
        # Check if the error message is in the response detail
        assert resp.status_code in [400, 404]
        assert message.lower() in resp.json()["detail"].lower()

@then(parsers.parse('a binding record should link User "{username}" to Household "{household_name}"'))
def then_verify_binding_exists(db, username, household_name):
    user = db.query(User).filter(User.username == username).first()
    house = db.query(Household).filter(Household.name == household_name).first()
    binding = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == user.id,
        HouseholdMember.household_id == house.id
    ).first()
    assert binding is not None

@then(parsers.parse('the binding should have LiveIn = true'))
def then_verify_live_in(db, context):
    # Retrieve binding based on context username
    user = db.query(User).filter(User.username == context["username"]).first()
    binding = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == user.id,
        HouseholdMember.left_at.is_(None)
    ).first()
    assert binding is not None # left_at is None implies currently living in

@then(parsers.parse('the binding should have IsAdmin = false'))
def then_verify_not_admin(db, context):
    user = db.query(User).filter(User.username == context["username"]).first()
    binding = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == user.id,
        HouseholdMember.left_at.is_(None)
    ).first()
    assert binding.is_admin is False

@then(parsers.parse('the user "{username}" should still not belong to any household'))
def then_verify_still_no_household(db, username):
    user = db.query(User).filter(User.username == username).first()
    active_membership = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == user.id,
        HouseholdMember.left_at.is_(None)
    ).first()
    assert active_membership is None

@then(parsers.parse('the user "{username}" should still only be bound to "{current_home}"'))
def then_verify_original_household_only(db, username, current_home):
    user = db.query(User).filter(User.username == username).first()
    memberships = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == user.id,
        HouseholdMember.left_at.is_(None)
    ).all()

    assert len(memberships) == 1
    house = db.query(Household).get(memberships[0].household_id)
    assert house.name == current_home

@then(parsers.parse('no binding record should exist between User "{username}" and Household "{target_house}"'))
def then_no_new_binding(db, username, target_house):
    user = db.query(User).filter(User.username == username).first()
    house = db.query(Household).filter(Household.name == target_house).first()
    if house:
        binding = db.query(HouseholdMember).filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == house.id
        ).first()
        assert binding is None