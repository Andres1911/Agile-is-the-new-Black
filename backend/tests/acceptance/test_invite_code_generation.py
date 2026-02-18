import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.core.invite_codes import (
    DEFAULT_INVITE_CODE_LENGTH,
    INVITE_CODE_ALPHABET,
    generate_unique_invite_code,
)
from app.models.models import Household

scenarios("features/ID004_Generate_Unique_Invite_Code.feature")


class HouseholdCreateError(Exception):
    pass


@pytest.fixture
def context():
    return {}


def _ensure_household(db, name: str, invite_code: str):
    existing = db.query(Household).filter(Household.name == name).first()
    if existing:
        existing.invite_code = invite_code
        db.commit()
        return existing

    h = Household(name=name, invite_code=invite_code)
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


def _candidate_fn_from_context(ctx):
    # Sequence-driven candidates (for collision tests)
    if "candidate_sequence" in ctx:

        def _fn(_length: int) -> str:
            # pop(0) ensures firstCandidate then secondCandidate
            return ctx["candidate_sequence"].pop(0)

        return _fn

    # Fixed candidate (for “always collide” error flow)
    if "fixed_candidate" in ctx:

        def _fn(_length: int) -> str:
            return ctx["fixed_candidate"]

        return _fn

    return None


def _create_household(db, ctx, household_name: str):
    candidate_fn = _candidate_fn_from_context(ctx)
    max_attempts = ctx.get("max_attempts", 1000)

    try:
        code = generate_unique_invite_code(
            db,
            length=DEFAULT_INVITE_CODE_LENGTH,
            max_attempts=max_attempts,
            candidate_fn=candidate_fn,
        )
    except RuntimeError as e:
        raise HouseholdCreateError(
            "Cannot create household: Unable to generate a unique invite code"
        ) from e

    h = Household(name=household_name, invite_code=code)
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


# ── Given ────────────────────────────────────────────────────────────────


@given(parsers.parse('user "{username}" is authenticated'))
def user_is_authenticated(context, username):
    # For this feature, we don't need real auth tokens (no household API endpoint).
    # We store it anyway so the scenario reads naturally.
    context["current_user"] = username


@given(parsers.parse('household "{household_name}" exists with invite code "{invite_code}"'))
def household_exists_with_invite_code(db, household_name, invite_code):
    _ensure_household(db, household_name, invite_code)


@given(
    parsers.parse(
        'the invite code generator will propose codes "{first_candidate}" then "{second_candidate}"'
    )
)
def generator_proposes_two_codes(context, first_candidate, second_candidate):
    context["candidate_sequence"] = [first_candidate, second_candidate]
    context["max_attempts"] = 2


@given(parsers.parse('the invite code generator will propose code "{colliding_code}"'))
def generator_proposes_one_code(context, colliding_code):
    # Force failure: only 1 attempt, and it collides.
    context["fixed_candidate"] = colliding_code
    context["max_attempts"] = 1


# ── When ─────────────────────────────────────────────────────────────────


@when(parsers.parse('"{username}" creates household "{household_name}"'))
def create_household_normal(db, context, username, household_name):
    context["created_household"] = _create_household(db, context, household_name)
    context["create_error"] = None


@when(parsers.parse('"{username}" attempts to create household "{household_name}"'))
def create_household_attempt(db, context, username, household_name):
    try:
        context["created_household"] = _create_household(db, context, household_name)
        context["create_error"] = None
    except HouseholdCreateError as e:
        context["created_household"] = None
        context["create_error"] = str(e)


# ── Then ─────────────────────────────────────────────────────────────────


@then(parsers.parse('household "{household_name}" is created'))
def household_is_created(db, household_name):
    assert db.query(Household).filter(Household.name == household_name).first() is not None


@then(parsers.parse('household "{household_name}" has an invite code'))
def household_has_invite_code(db, household_name):
    h = db.query(Household).filter(Household.name == household_name).first()
    assert h is not None
    assert isinstance(h.invite_code, str)
    assert h.invite_code != ""


@then("the invite code is 8 characters long")
def invite_code_is_correct_length(context):
    code = context["created_household"].invite_code
    assert len(code) == DEFAULT_INVITE_CODE_LENGTH


@then("the invite code contains only allowed characters")
def invite_code_has_allowed_chars(context):
    code = context["created_household"].invite_code
    assert all(c in INVITE_CODE_ALPHABET for c in code)


@then(parsers.parse('the invite code is not "{forbidden_code}"'))
def invite_code_is_not_value(context, forbidden_code):
    code = context["created_household"].invite_code
    assert code != forbidden_code


@then(parsers.parse('household "{household_name}" has invite code "{expected_code}"'))
def household_has_exact_invite_code(db, household_name, expected_code):
    h = db.query(Household).filter(Household.name == household_name).first()
    assert h is not None
    assert h.invite_code == expected_code


@then("the system rejects the household creation")
def creation_is_rejected(context):
    assert context["created_household"] is None
    assert context["create_error"] is not None


@then(parsers.parse('the system displays error message "{expected_message}"'))
def error_message_matches(context, expected_message):
    assert context["create_error"] == expected_message
