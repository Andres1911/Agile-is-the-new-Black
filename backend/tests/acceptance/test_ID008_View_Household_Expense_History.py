from datetime import UTC, datetime, timedelta

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.models.models import Expense, Household, HouseholdMember
from app.models.models import User as UserModel
from tests.conftest import login
from tests.conftest import register as register_user

# link the Feature file
scenarios("features/ID008_View_Household_Expense_History.feature")


@pytest.fixture()
def context():
    return {}


def get_table_dicts(datatable):
    """Converts the list-style datatable into a list of dictionaries"""
    keys = datatable[0]
    return [dict(zip(keys, row, strict=False)) for row in datatable[1:]]


# ── GIVEN steps ───────────────────────────────────────────────────────────


@given(
    parsers.parse('a user with username "{username}" exists in the system'),
    target_fixture="context",
)
def given_user_exists(client, username, context):
    register_user(
        client, username=username, email=f"{username.lower()}@test.com", password="Password123!"
    )
    context["username"] = username
    return context


@given(parsers.parse('a household named "{name}" exists in the system'), target_fixture="context")
def step_household_exists(db, name, context):
    hh = db.query(Household).filter(Household.name == name).first()
    if not hh:
        hh = Household(name=name, invite_code=f"INV_{name[:3].upper()}")
        db.add(hh)
        db.commit()
        db.refresh(hh)
    context["hh_id"] = hh.id
    return context


@given(parsers.parse('"{username}" is a member of "{hh_name}"'))
def step_user_is_member(db, username, hh_name):
    user = db.query(UserModel).filter(UserModel.username == username).first()
    hh = db.query(Household).filter(Household.name == hh_name).first()
    if not db.query(HouseholdMember).filter_by(user_id=user.id, household_id=hh.id).first():
        db.add(HouseholdMember(user_id=user.id, household_id=hh.id, left_at=None))
        db.commit()


@given(parsers.parse('the following expenses exist for "{hh_name}"'))
def step_expenses_exist(db, hh_name, context, datatable):
    user = db.query(UserModel).filter(UserModel.username == context["username"]).first()
    hh = db.query(Household).filter(Household.name == hh_name).first()

    table_rows = get_table_dicts(datatable)

    for i, row in enumerate(table_rows):
        expense = Expense(
            description=row["Description"],
            amount=float(row["Amount"]),
            household_id=hh.id,
            creator_id=user.id,
            date=datetime.now(UTC) + timedelta(seconds=i),  # Ensures sort order
        )
        db.add(expense)
    db.commit()


@given(parsers.parse('the user "{username}" is logged in'), target_fixture="context")
@given(parsers.parse('"{username}" is logged in'), target_fixture="context")
def step_login(client, username, context):
    auth_resp = login(client, username=username, password="Password123!")
    context["headers"] = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}
    return context


@given(parsers.parse('"{hh_name}" has no recorded expenses'))
def step_no_expenses(db, hh_name):
    hh = db.query(Household).filter(Household.name == hh_name).first()
    db.query(Expense).filter_by(household_id=hh.id).delete()
    db.commit()


@given(parsers.parse('"{username}" is not a member of "{hh_name}"'), target_fixture="context")
def step_not_member(db, username, hh_name, context):
    user = db.query(UserModel).filter(UserModel.username == username).first()
    hh = db.query(Household).filter(Household.name == hh_name).first()
    db.query(HouseholdMember).filter_by(user_id=user.id, household_id=hh.id).delete()
    db.commit()
    return context


# ── WHEN steps ────────────────────────────────────────────────────────────


@when(
    parsers.parse('"{username}" requests the expense history for "{hh_name}"'),
    target_fixture="context",
)
def step_request_history(client, db, username, hh_name, context):
    hh = db.query(Household).filter(Household.name == hh_name).first()
    context["response"] = client.get(
        f"/api/v1/households/{hh.id}/expenses", headers=context.get("headers", {})
    )
    return context


# ── THEN steps ────────────────────────────────────────────────────────────


@then(parsers.parse("a list of {count:d} expenses should be returned"))
def step_verify_count(context, count):
    assert context["response"].status_code == 200
    assert len(context["response"].json()) == count


@then(parsers.parse('the {position} expense should be "{desc}" with amount {amt:f}'))
def step_verify_expense(context, position, desc, amt):
    data = context["response"].json()
    idx = 0 if position == "first" else 1
    assert data[idx]["description"] == desc
    assert abs(float(data[idx]["amount"]) - amt) < 0.01


@then("an empty list should be returned")
def step_empty_list(context):
    assert context["response"].status_code == 200
    assert context["response"].json() == []


@then(parsers.parse('the message "{message}" is issued'))
def step_verify_message(context, message):
    resp_data = context["response"].json()

    # If it's a list (like an empty history), check if it's empty
    if isinstance(resp_data, list) and (not resp_data and message == "No expenses found"):
        return  # Success

    # If it's a dict (like an error), check the detail
    detail = resp_data.get("detail", "") if isinstance(resp_data, dict) else str(resp_data)
    assert message in str(detail)


@then("no expense data should be returned")
def step_no_data(context):
    assert context["response"].status_code >= 400
