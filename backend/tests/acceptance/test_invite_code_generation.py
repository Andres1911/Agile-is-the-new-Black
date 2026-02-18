"""Step definitions for ID004_Generate_Unique_Invite_Code.feature."""

import re

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.core.invite_codes import generate_unique_invite_code
from app.models.models import Household

scenarios("features/ID004_Generate_Unique_Invite_Code.feature")


@pytest.fixture()
def context():
    return {}


# ── GIVEN ───────────────────────────────────────────────────────────────


@given("the system has no existing households")
def given_no_households(db):
    assert db.query(Household).count() == 0


@given(parsers.parse('a household exists with invite code "{code}"'))
def given_household_exists(db, code):
    db.add(Household(name="Seed", invite_code=code))
    db.commit()


@given(
    parsers.parse('the invite code generator will propose codes "{first}" then "{second}"'),
    target_fixture="context",
)
def given_proposed_codes(context, first, second):
    context["proposed_codes"] = [first, second]
    return context


# ── WHEN ────────────────────────────────────────────────────────────────


@when("a unique invite code is generated", target_fixture="context")
def when_generate_code(db, context):
    context["invite_code"] = generate_unique_invite_code(db)
    return context


@when(
    "a unique invite code is generated using the proposed codes",
    target_fixture="context",
)
def when_generate_code_with_proposals(db, context):
    proposed = list(context.get("proposed_codes", []))
    assert proposed, "Test data error: proposed_codes must be present"

    def candidate_fn(_len: int) -> str:
        return proposed.pop(0)

    context["invite_code"] = generate_unique_invite_code(db, candidate_fn=candidate_fn)
    return context


# ── THEN ────────────────────────────────────────────────────────────────


@then(parsers.parse("the invite code should be {n:d} characters long"))
def then_length(context, n):
    assert len(context["invite_code"]) == n


@then("the invite code should contain only uppercase letters and digits")
def then_charset(context):
    code = context["invite_code"]
    assert code == code.upper()
    assert re.fullmatch(r"[A-Z0-9]+", code)


@then(parsers.parse('the invite code should not equal "{code}"'))
def then_not_equal(context, code):
    assert context["invite_code"] != code


@then(parsers.parse('the invite code should equal "{code}"'))
def then_equal(context, code):
    assert context["invite_code"] == code
