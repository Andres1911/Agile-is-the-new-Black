"""Step definitions for ID004_Generate_Unique_Invite_Code.feature."""

import re
import secrets

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.core.invite_codes import generate_unique_invite_code
from app.models.models import Household, HouseholdMember, User

scenarios("features/ID004_Generate_Unique_Invite_Code.feature")

INVITE_CODE_RE = re.compile(r"^[A-Z0-9]{8}$")


@pytest.fixture()
def context():
    return {}


# ── helpers ──────────────────────────────────────────────────────────────


def _get_or_create_user(db, username: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user

    user = User(
        username=username,
        email=f"{username.lower()}@example.com",
        password_hash="test-hash",
        full_name=username,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _unique_seed_code(db) -> str:
    # Household.invite_code cannot be NULL, so we seed one when creating a household.
    # Keep it 8 chars + uppercase to avoid surprises.
    while True:
        code = ("SEED" + secrets.token_hex(2)).upper()  # 4 + 4 = 8 chars
        exists = db.query(Household).filter(Household.invite_code == code).first()
        if not exists:
            return code


def _get_or_create_household(db, household_name: str) -> Household:
    hh = db.query(Household).filter(Household.name == household_name).first()
    if hh:
        return hh

    hh = Household(name=household_name, invite_code=_unique_seed_code(db))
    db.add(hh)
    db.commit()
    db.refresh(hh)
    return hh


def _set_membership(db, user: User, household: Household, is_admin: bool) -> None:
    m = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == household.id,
        )
        .first()
    )

    if not m:
        m = HouseholdMember(user_id=user.id, household_id=household.id, is_admin=is_admin)
        db.add(m)
    else:
        m.is_admin = is_admin

    db.commit()


def _require_admin(db, username: str, household_name: str) -> Household:
    user = _get_or_create_user(db, username)
    household = _get_or_create_household(db, household_name)

    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == household.id,
        )
        .first()
    )

    if not membership or not membership.is_admin:
        raise PermissionError("Permission Denied: Admin rights required")

    return household


# ── GIVEN ───────────────────────────────────────────────────────────────


@given(parsers.parse('a user with username "{username}" already exists in the system'))
def given_user_exists(db, username):
    _get_or_create_user(db, username)


@given(parsers.parse('the user "{username}" is an Admin of the household "{household_name}"'))
def given_user_is_admin_of_household(db, username, household_name):
    user = _get_or_create_user(db, username)
    household = _get_or_create_household(db, household_name)
    _set_membership(db, user, household, is_admin=True)


@given(parsers.parse('the user "{username}" is logged in'), target_fixture="context")
def given_user_logged_in(context, username):
    context["current_user"] = username
    return context


@given(parsers.parse('no other household in the system uses the invite code "{manual_code}"'))
def given_no_household_uses_manual_code(db, manual_code):
    assert db.query(Household).filter(Household.invite_code == manual_code).first() is None


@given(parsers.parse('the user "{username}" not an Admin of the household "{household_name}"'))
def given_user_not_admin(db, username, household_name):
    user = _get_or_create_user(db, username)
    household = _get_or_create_household(db, household_name)
    _set_membership(db, user, household, is_admin=False)


# ── WHEN ────────────────────────────────────────────────────────────────


@when(
    parsers.parse(
        'the user requests to generate a random invite code for the household "{household_name}"'
    )
)
def when_generate_random_code(db, context, household_name):
    username = context["current_user"]
    household = _get_or_create_household(db, household_name)
    context["before_invite_code"] = household.invite_code

    try:
        household = _require_admin(db, username, household_name)
        new_code = generate_unique_invite_code(db)
        household.invite_code = new_code
        db.commit()

        context["message"] = "Success"
        context["generated_code"] = new_code
    except PermissionError as e:
        context["error"] = str(e)


@when(parsers.parse('the manual code "{manual_code}" is valid with at least 8 characters'))
def when_manual_code_valid(manual_code):
    assert len(manual_code) >= 8, "Test data error: ManualCode must be at least 8 chars"


@when(
    parsers.parse(
        'the user requests to set the invite code to "{manual_code}" for the household "{household_name}"'
    )
)
def when_set_manual_code(db, context, manual_code, household_name):
    username = context["current_user"]
    household = _get_or_create_household(db, household_name)
    context["before_invite_code"] = household.invite_code

    try:
        household = _require_admin(db, username, household_name)

        # Uniqueness rule (feature Given should guarantee this, but enforce anyway)
        if db.query(Household).filter(Household.invite_code == manual_code).first():
            raise ValueError("Invite code already in use")

        household.invite_code = manual_code
        db.commit()

        context["message"] = "Success"
        context["generated_code"] = manual_code
    except (PermissionError, ValueError) as e:
        context["error"] = str(e)


# ── THEN ────────────────────────────────────────────────────────────────


@then(
    parsers.parse('the household "{household_name}" should have the invite code as its attribute')
)
def then_household_has_generated_code(db, context, household_name):
    household = db.query(Household).filter(Household.name == household_name).first()
    assert household is not None

    code = household.invite_code
    assert code is not None
    assert INVITE_CODE_RE.fullmatch(code), f"Invite code '{code}' is not 8 chars A-Z/0-9"
    assert context.get("message") == "Success"


@then(
    parsers.parse(
        'the household "{household_name}" should have the invite code "{manual_code}" as its attribute'
    )
)
def then_household_has_manual_code(db, context, household_name, manual_code):
    household = db.query(Household).filter(Household.name == household_name).first()
    assert household is not None
    assert household.invite_code == manual_code
    assert context.get("message") == "Success"


@then(parsers.parse('the message "{message}" is issued'))
def then_message_success(context, message):
    assert context.get("message") == message
    assert "error" not in context


@then(parsers.parse('the invite code for household "{household_name}" should not be generated'))
def then_invite_code_not_generated(db, context, household_name):
    assert "error" in context, "Expected an error but none was recorded"
    household = db.query(Household).filter(Household.name == household_name).first()
    assert household is not None
    assert household.invite_code == context["before_invite_code"]


@then(parsers.parse('the error message "{error_msg}" is returned'))
def then_error_message_returned(context, error_msg):
    assert context.get("error") == error_msg
