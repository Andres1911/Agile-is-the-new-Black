import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from app.models.models import Expense, ExpenseShare, ExpenseStatus, Household, HouseholdMember, User, VoteStatus
from datetime import UTC, datetime


# Link to the feature file
scenarios("features/ID016_Resolve_Disputed_Expense.feature")


@pytest.fixture()
def context():
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# GIVEN STEPS (Setup)
# ─────────────────────────────────────────────────────────────────────────────

@given(parsers.parse('"{username}" is logged in'))
def user_logged_in_placeholder(username):
    # This step is satisfied because when_resolve_expense generates
    # the token dynamically using the username provided in the feature file.
    pass

@given(parsers.parse('household "{household_name}" exists with members'), target_fixture="context")
def given_household_with_roles(db, household_name, datatable, context):
    house = db.query(Household).filter(Household.name == household_name).first()
    if not house:
        house = Household(name=household_name, invite_code="MAPLE123")
        db.add(house)
        db.flush()


    context["household_id"] = house.id
    context["household_name"] = household_name


    for row in datatable[1:]:  # | member | role |
        member_name, role = row
        user = db.query(User).filter(User.username == member_name).first()
        if not user:
            from app.core.security import get_password_hash
            user = User(
                username=member_name,
                email=f"{member_name.lower()}@test.com",
                password_hash=get_password_hash("Password123!"),
                full_name=member_name
            )
            db.add(user)
            db.flush()


        # Update or create membership with specific role
        membership = db.query(HouseholdMember).filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == house.id
        ).first()


        is_admin = (role.upper() == "ADMIN")


        if not membership:
            db.add(HouseholdMember(user_id=user.id, household_id=house.id, is_admin=is_admin))
        else:
            membership.is_admin = is_admin


    db.commit()
    return context


@given(parsers.parse('user "{username}" has an existing expense with the following details'))
def given_existing_disputed_expense(db, username, datatable, context):
    user = db.query(User).filter(User.username == username).first()
    rows = datatable[1:] # | description | amount | status |
    desc, amt, status = rows[0]


    expense = Expense(
        description=desc,
        amount=float(amt),
        status=ExpenseStatus[status.upper()],
        household_id=context["household_id"],
        creator_id=user.id,
        date=datetime.now(UTC)
    )
    db.add(expense)
    db.flush()
    context["current_expense_id"] = expense.id
    db.commit()


@given(parsers.parse('the expense has the following expense shares'))
def given_expense_shares(db, datatable, context):
    for row in datatable[1:]: # | payer | amount_owed | vote_status |
        payer_name, amount, vote_status = row
        payer = db.query(User).filter(User.username == payer_name).first()


        share = ExpenseShare(
            expense_id=context["current_expense_id"],
            user_id=payer.id,
            amount_owed=float(amount),
            paid_amount=0.0,
            is_paid=False,
            vote_status=VoteStatus[vote_status.upper()]
        )
        db.add(share)
    db.commit()


@given(parsers.parse('"{username}" has expense "{description}" with status "{status}"'))
def given_specific_expense_status(db, username, description, status, context):
    user = db.query(User).filter(User.username == username).first()

    # Safely handle the feature file typo where they wrote "ACCEPTED" instead of "FINALIZED"
    safe_status = status.upper()
    if safe_status == "ACCEPTED":
        safe_status = "FINALIZED"

    expense = Expense(
        description=description,
        amount=10.0, # Placeholder
        status=ExpenseStatus[safe_status],
        household_id=context["household_id"],
        creator_id=user.id,
        date=datetime.now(UTC)
    )
    db.add(expense)
    db.flush()
    context["current_expense_id"] = expense.id
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# WHEN STEPS (Actions)
# ─────────────────────────────────────────────────────────────────────────────


@when(parsers.parse('"{username}" marks the disputed expense "{description}" as "{decision}"'))
@when(parsers.parse('"{username}" attempts to mark the disputed expense "{description}" as "{decision}"'))
@when(parsers.parse('"{username}" attempts to mark the expense "{description}" as "{decision}"'))
def when_resolve_expense(client, context, username, description, decision):
    # Retrieve the expense by description from context or DB
    expense_id = context["current_expense_id"]


    # Same authentication pattern as teammates
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": username})
    headers = {"Authorization": f"Bearer {token}"}


    response = client.post(
        f"/api/v1/expenses/{expense_id}/resolve",
        json={"decision": decision.upper()},
        headers=headers
    )
    context["response"] = response


# ─────────────────────────────────────────────────────────────────────────────
# THEN STEPS (Assertions)
# ─────────────────────────────────────────────────────────────────────────────


@then(parsers.parse('the system updates the status of "{description}" to "{status}"'))
def then_check_expense_status(db, description, status):
    expense = db.query(Expense).filter(Expense.description == description).first()
    expected = status.upper()

    # Safely get the Enum to prevent KeyErrors if a string doesn't exist
    try:
        expected_enum = ExpenseStatus[expected]
    except KeyError:
        expected_enum = getattr(ExpenseStatus, expected, expected)

    assert expense.status == expected_enum or expense.status.name == expected


@then(parsers.parse('the vote status for all payers is forced to "{status}"'))
def then_check_all_shares_status(db, context, status):
    shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == context["current_expense_id"]).all()
    for share in shares:
        assert share.vote_status == VoteStatus[status.upper()]


@then(parsers.parse('the system displays success message "{message}"'))
def then_success_msg(context, message):
    assert context["response"].status_code == 200
    assert message in context["response"].json()["detail"]


@then(parsers.parse('the system displays error message "{message}"'))
def then_error_msg(context, message):
    assert context["response"].status_code in [400, 403]
    assert message in context["response"].json()["detail"]


@then("the system rejects the action")
def then_reject_action(context):
    assert context["response"].status_code in [400, 403]


@then(parsers.parse('the expense status remains "{status}"'))
def then_status_unchanged(db, context, status):
    db.expire_all() # Refresh from DB
    expense = db.query(Expense).filter(Expense.id == context["current_expense_id"]).first()

    # Safely handle the feature file typo here as well
    expected_status = status.upper()
    if expected_status == "ACCEPTED":
        expected_status = "FINALIZED"

    assert expense.status == ExpenseStatus[expected_status]
