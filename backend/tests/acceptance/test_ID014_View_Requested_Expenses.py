from datetime import UTC, datetime, timedelta

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.models.models import Expense, ExpenseShare, Household, HouseholdMember, User, VoteStatus
from tests.conftest import auth_header, register

scenarios("features/ID014_View_Requested_Expenses.feature")


@pytest.fixture()
def context():
    return {}


def get_table_dicts(datatable):
    keys = datatable[0]
    return [dict(zip(keys, row, strict=False)) for row in datatable[1:]]


def _get_user(db, username: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    assert user is not None, f"User '{username}' not found"
    return user


def _get_household(db, name: str) -> Household:
    household = db.query(Household).filter(Household.name == name).first()
    assert household is not None, f"Household '{name}' not found"
    return household


@given(
    parsers.parse('a user with username "{username}" exists in the system'),
    target_fixture="context",
)
def given_user_exists(client, username, context):
    register(
        client,
        username=username,
        email=f"{username.lower()}@test.com",
        password="Password123!",
        full_name=username,
    )
    return context


@given(parsers.parse('a household named "{name}" exists in the system'))
def given_household_exists(db, name):
    household = db.query(Household).filter(Household.name == name).first()
    if not household:
        household = Household(name=name, invite_code=f"{name[:3].upper()}101")
        db.add(household)
        db.commit()


@given(parsers.parse('"{username}" is a member of "{household_name}"'))
def given_household_member(db, username, household_name):
    user = _get_user(db, username)
    household = _get_household(db, household_name)

    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == household.id,
        )
        .first()
    )
    if not membership:
        db.add(HouseholdMember(user_id=user.id, household_id=household.id, left_at=None))
        db.commit()


@given(parsers.parse('the following requested expense shares exist for "{household_name}"'))
def given_requested_expense_shares(db, household_name, datatable):
    household = _get_household(db, household_name)
    rows = get_table_dicts(datatable)

    for i, row in enumerate(rows):
        description = row["ExpenseDescription"]
        payee = _get_user(db, row["Payee"])
        payer = _get_user(db, row["Payer"])
        amount_owed = float(row["AmountOwed"])
        vote_status = VoteStatus[row["VoteStatus"].upper()]

        expense = Expense(
            description=description,
            amount=amount_owed,
            household_id=household.id,
            creator_id=payee.id,
            date=datetime.now(UTC) + timedelta(seconds=i),
        )
        db.add(expense)
        db.flush()

        share = ExpenseShare(
            expense_id=expense.id,
            user_id=payer.id,
            amount_owed=amount_owed,
            paid_amount=0.0,
            is_paid=False,
            vote_status=vote_status,
        )
        db.add(share)

    db.commit()


@given(parsers.parse('the user "{username}" is logged in'), target_fixture="context")
@given(parsers.parse('"{username}" is logged in'), target_fixture="context")
def given_logged_in(client, username, context):
    context["headers"] = auth_header(client, username=username, password="Password123!")
    return context


@given(
    parsers.parse(
        'all requested expense shares for "{username}" in "{household_name}" are accepted'
    )
)
def given_all_requested_shares_accepted(db, username, household_name):
    user = _get_user(db, username)
    household = _get_household(db, household_name)

    shares = (
        db.query(ExpenseShare)
        .join(Expense, ExpenseShare.expense_id == Expense.id)
        .filter(
            Expense.household_id == household.id,
            ExpenseShare.user_id == user.id,
        )
        .all()
    )

    for share in shares:
        share.vote_status = VoteStatus.ACCEPTED

    db.commit()


@given(parsers.parse('"{username}" is not a member of any household'))
def given_not_member_any_household(db, username):
    user = _get_user(db, username)
    db.query(HouseholdMember).filter(HouseholdMember.user_id == user.id).delete()
    db.commit()


@when(
    parsers.parse('"{username}" requests his requested expenses using GET "{path}"'),
    target_fixture="context",
)
@when(
    parsers.parse('"{username}" requests requested expenses using GET "{path}"'),
    target_fixture="context",
)
def when_get_requested_expenses(client, path, context):
    if path.startswith("/expenses/"):
        path = "/api/v1" + path

    context["response"] = client.get(path, headers=context.get("headers", {}))
    return context


@then(parsers.parse("a list of {count:d} requested expenses should be returned"))
def then_requested_count(context, count):
    assert context["response"].status_code == 200
    assert len(context["response"].json()) == count


@then(parsers.parse('the first requested expense should be "{description}" with amount {amount:f}'))
def then_first_requested_expense(context, description, amount):
    data = context["response"].json()
    assert data[0]["description"] == description
    assert abs(float(data[0]["amount_requested"]) - amount) < 0.01


@then(parsers.parse('the requested expense should show creator "{username}"'))
def then_creator_username(context, username):
    data = context["response"].json()
    assert data[0]["creator_username"] == username


@then(parsers.parse('all returned requested expenses should have vote status "{status}"'))
def then_all_vote_status(context, status):
    data = context["response"].json()
    assert all(item["vote_status"] == status for item in data)


@then("an empty list of requested expenses should be returned")
def then_empty_requested_list(context):
    assert context["response"].status_code == 200
    assert context["response"].json() == []


@then(parsers.parse('the message "{message}" is issued'))
def then_message_issued(context, message):
    assert message in context["response"].json()["detail"]


@then("no requested expense data should be returned")
def then_no_requested_data(context):
    assert context["response"].status_code >= 400
