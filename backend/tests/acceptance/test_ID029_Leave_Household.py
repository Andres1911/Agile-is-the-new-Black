import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.models.models import (
    Expense,
    ExpenseShare,
    Household,
    HouseholdMember,
    User,
    VoteStatus,
)
from tests.conftest import auth_header as get_auth_header
from tests.conftest import register as register_user

# 1. Bind Feature file
scenarios("features/ID029_Leave_Household.feature")


@pytest.fixture()
def context():
    """Shared context"""
    return {}


# ── GIVEN steps ───────────────────────────────────────────────────────────


@given(parsers.parse('a user with username "{username}" already exists in the system'))
def given_user_exists(client, db, username, context):
    register_user(
        client,
        email=f"{username.lower()}@test.com",
        username=username,
        password="Password123!",
        full_name=username,
    )


@given(parsers.parse('the user "{username}" is logged in'), target_fixture="context")
def given_user_logged_in(client, username, context):
    context["auth_headers"] = get_auth_header(client, username=username, password="Password123!")
    context["current_user"] = username
    return context


@given(parsers.parse('the user "{username}" is living in the household "{household_name}"'))
def given_user_living_in_household(db, username, household_name, context):
    user = db.query(User).filter(User.username == username).first()

    household = db.query(Household).filter(Household.name == household_name).first()
    if not household:
        invite_code = household_name[:6].upper().replace(" ", "") + "123"
        household = Household(
            name=household_name,
            invite_code=invite_code,
            description="Test Household",
        )
        db.add(household)
        db.flush()

    # Check if membership already exists
    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == household.id,
        )
        .first()
    )
    if not membership:
        db.add(HouseholdMember(user_id=user.id, household_id=household.id, is_admin=False))

    db.commit()
    context["household_name"] = household_name


@given(parsers.parse('the user "{username}" has no outstanding balance in "{household_name}"'))
def given_user_has_no_outstanding_balance(db, username, household_name, context):
    # No outstanding expenses — nothing to do
    pass


@given(parsers.parse('the user "{username}" has a debt of "{amount}" to another member'))
def given_user_has_debt(db, username, amount, context):
    user = db.query(User).filter(User.username == username).first()
    household = db.query(Household).filter(Household.name == context["household_name"]).first()

    # Create a creditor user if needed
    creditor_username = f"creditor_{username.lower()}"
    creditor = db.query(User).filter(User.username == creditor_username).first()
    if not creditor:
        from app.core.security import get_password_hash

        creditor = User(
            username=creditor_username,
            email=f"{creditor_username}@test.com",
            password_hash=get_password_hash("Password123!"),
            full_name=creditor_username,
        )
        db.add(creditor)
        db.flush()

    # Add creditor to household if needed
    creditor_membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == creditor.id,
            HouseholdMember.household_id == household.id,
        )
        .first()
    )
    if not creditor_membership:
        db.add(HouseholdMember(user_id=creditor.id, household_id=household.id, is_admin=False))
        db.flush()

    # Create expense by creditor that user owes money on
    expense = Expense(
        description="Outstanding debt",
        amount=float(amount),
        creator_id=creditor.id,
        household_id=household.id,
    )
    db.add(expense)
    db.flush()

    share = ExpenseShare(
        expense_id=expense.id,
        user_id=user.id,
        amount_owed=float(amount),
        paid_amount=0.0,
        is_paid=False,
        vote_status=VoteStatus.ACCEPTED,
    )
    db.add(share)
    db.commit()


@given(parsers.parse('the user "{username}" is an admin with IsAdmin = true'))
def given_user_is_admin(db, username, context):
    user = db.query(User).filter(User.username == username).first()
    household = db.query(Household).filter(Household.name == context["household_name"]).first()

    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == household.id,
        )
        .first()
    )
    if membership:
        membership.is_admin = True
        db.commit()


@given(parsers.parse('the household "{household_name}" has other active members'))
def given_household_has_other_members(db, household_name, context):
    household = db.query(Household).filter(Household.name == household_name).first()

    # Add a second non-admin member if none exist
    from app.core.security import get_password_hash

    other_username = f"other_{household_name[:4].lower().replace(' ', '')}"
    other_user = db.query(User).filter(User.username == other_username).first()
    if not other_user:
        other_user = User(
            username=other_username,
            email=f"{other_username}@test.com",
            password_hash=get_password_hash("Password123!"),
            full_name=other_username,
        )
        db.add(other_user)
        db.flush()

    other_membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == other_user.id,
            HouseholdMember.household_id == household.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )
    if not other_membership:
        db.add(HouseholdMember(user_id=other_user.id, household_id=household.id, is_admin=False))
        db.commit()


# ── WHEN steps ────────────────────────────────────────────────────────────


@when(
    parsers.parse('the user requests to leave the household "{household_name}"'),
    target_fixture="context",
)
def when_leave_household(client, household_name, context):
    context["response"] = client.post(
        "/api/v1/households/me/leave",
        headers=context["auth_headers"],
    )
    return context


# ── THEN steps ────────────────────────────────────────────────────────────


@then(parsers.parse('the message "{message}" is issued'))
def then_message_issued(context, message):
    data = context["response"].json()
    # Check either success message in body or error detail
    if context["response"].status_code == 200:
        assert "successfully left" in data["message"].lower()
    else:
        assert message.lower() in data["detail"].lower()


@then(
    parsers.parse(
        'the binding record linking User "{username}" to Household "{household_name}" should have LiveIn = false'
    )
)
def then_user_live_in_false(db, username, household_name):
    user = db.query(User).filter(User.username == username).first()
    household = db.query(Household).filter(Household.name == household_name).first()

    db.expire_all()
    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == household.id,
        )
        .first()
    )
    assert membership is not None
    assert membership.left_at is not None


@then(
    parsers.parse(
        'the binding record linking User "{username}" to Household "{household_name}" should have LiveIn = true'
    )
)
def then_user_live_in_true(db, username, household_name):
    user = db.query(User).filter(User.username == username).first()
    household = db.query(Household).filter(Household.name == household_name).first()

    db.expire_all()
    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == household.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )
    assert membership is not None


@then(
    parsers.parse(
        'the binding record linking User "{username}" to Household "{household_name}" should have IsAdmin = true and LiveIn = true'
    )
)
def then_user_still_admin_and_live_in(db, username, household_name):
    user = db.query(User).filter(User.username == username).first()
    household = db.query(Household).filter(Household.name == household_name).first()

    db.expire_all()
    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == household.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )
    assert membership is not None
    assert membership.is_admin is True
