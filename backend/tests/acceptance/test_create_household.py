import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.models.models import Household, HouseholdMember
from app.models.models import User as UserModel
from tests.conftest import TestingSessionLocal, login
from tests.conftest import register as _register_helper

#Link to the feature file
scenarios("features/ID003_Create_A_Household.feature")

@pytest.fixture()
def context():
    """Dictionary to share data between steps (like the API response)."""
    return {}

# ── GIVEN ─────────────────────────────────────────────────────────────────

@given(parsers.parse('a user with username "{username}" already exists in the system'), target_fixture="context")
def given_user_exists(client, username, context):
    email = f"{username.lower()}@test.com"
    _register_helper(client, username=username, email=email, password="Password123!")
    context["username"] = username
    return context

@given(parsers.parse('the user "{username}" is logged in'), target_fixture="context")
def given_user_logged_in(client, username, context):
    auth_resp = login(client, username=username, password="Password123!")
    context["headers"] = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}
    return context

@given(parsers.parse('the user "{username}" hasn\'t been assigned a household'))
def step_user_no_household(username):
    # This is a descriptive step; our fresh test DB ensures this.
    pass

@given(parsers.parse('a household named "{name}" does not exist'))
def step_no_household_exists(name):
    db = TestingSessionLocal()
    exists = db.query(Household).filter(Household.name == name).first()
    assert exists is None, f"Household {name} already exists!"
    db.close()

@given(parsers.parse('a household named "{name}" already exists in the system'))
def step_household_already_exists(name):
    db = TestingSessionLocal()
    if not db.query(Household).filter(Household.name == name).first():
        db.add(Household(name=name, invite_code=f"EXISTING_{name[:3]}"))
        db.commit()
    db.close()

@given(parsers.parse('the user "{username}" is not currently living in any household'))
def step_user_homeless(username):
    """
    Verifies that the user exists and is not currently associated with any household in the database.
    """
    db = TestingSessionLocal()

    #Get the user
    user = db.query(UserModel).filter(UserModel.username == username).first()
    assert user is not None, f"Pre-condition failed: User {username} not found in DB."

    #check for any record in the membership table
    #we check for any membership where 'left_at' is None (meaning they are currently 'in')
    active_membership = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == user.id,
        HouseholdMember.left_at is None
    ).first()

    assert active_membership is None, f"Pre-condition failed: User {username} is already linked to a household!"

    db.close()

@given(parsers.parse('the user "{username}" is already living in the household "{current_home}"'))
def step_user_already_in_home(username, current_home):
    db = TestingSessionLocal()
    #create the home
    hh = Household(name=current_home, invite_code="HOME123")
    db.add(hh)
    db.flush()
    #link user to it
    user = db.query(UserModel).filter(UserModel.username == username).first()
    db.add(HouseholdMember(user_id=user.id, household_id=hh.id, is_admin=True))
    db.commit()
    db.close()

# ── WHEN ──────────────────────────────────────────────────────────────────

@when(parsers.parse('requesting the addition of household "{name}"'), target_fixture="context")
def when_request_add_household(client, context, name):
    payload = {"name": name}
    context["response"] = client.post("/api/v1/households/", json=payload, headers=context["headers"])
    return context

@when(parsers.parse('requesting the addition of household "{name}" with address "{address}"'), target_fixture="context")
def when_request_add_with_address(client, context, name, address):
    payload = {"name": name, "address": address}
    context["response"] = client.post("/api/v1/households/", json=payload, headers=context["headers"])
    return context

# ── THEN ──────────────────────────────────────────────────────────────────

@then(parsers.parse('a household named "{name}" should be created successfully'))
def then_household_created(context, name):
    assert context["response"].status_code == 201
    assert context["response"].json()["name"] == name

@then(parsers.parse('a household named "{name}" with address "{address}" should be created successfully'))
def then_household_created_with_addr(context, name, address):
    assert context["response"].status_code == 201
    data = context["response"].json()
    assert data["name"] == name
    assert data["address"] == address

@then(parsers.parse('the message "{message}" is issued'))
def then_message_issued(context, message):
    if context["response"].status_code == 201:
        assert message == "Success"
    else:
        detail = context["response"].json()["detail"]
        assert detail == message

@then(parsers.parse('a binding record should link User "{username}" to Household "{name}"'), target_fixture="context")
def then_verify_binding(username, name, context):
    db = TestingSessionLocal()
    user = db.query(UserModel).filter(UserModel.username == username).first()
    hh = db.query(Household).filter(Household.name == name).first()
    binding = db.query(HouseholdMember).filter_by(user_id=user.id, household_id=hh.id).first()

    assert binding is not None
    context["current_binding"] = binding # Store for the "And the binding..." steps
    db.close()
    return context

@then('the binding should have LiveIn = true')
def then_binding_live_in(context):
    assert context["current_binding"].left_at is None

@then('the binding should have IsAdmin = true')
def then_binding_is_admin(context):
    assert context["current_binding"].is_admin is True

@then(parsers.parse('the user "{username}" should still not live in any household'))
def then_still_homeless(username):
    db = TestingSessionLocal()
    user = db.query(UserModel).filter(UserModel.username == username).first()
    active = db.query(HouseholdMember).filter_by(user_id=user.id, left_at=None).first()
    assert active is None
    db.close()

@then(parsers.parse('the old binding record should still link User "{username}" to Household "{current_home}"'))
def then_old_binding_persists(username, current_home, context):
    db = TestingSessionLocal()
    user = db.query(UserModel).filter(UserModel.username == username).first()
    hh = db.query(Household).filter(Household.name == current_home).first()
    binding = db.query(HouseholdMember).filter_by(user_id=user.id, household_id=hh.id).first()
    assert binding is not None

    context["current_binding"] = binding  #share the record with the next step
    db.close()

    db.close()

@then(parsers.parse('no binding record should exist between User "{username}" and Household "{new_home}"'))
def then_no_new_binding(username, new_home):
    db = TestingSessionLocal()
    user = db.query(UserModel).filter(UserModel.username == username).first()
    hh = db.query(Household).filter(Household.name == new_home).first()
    if hh: # If the house was created but shouldn't have been
        binding = db.query(HouseholdMember).filter_by(user_id=user.id, household_id=hh.id).first()
        assert binding is None
    db.close()
