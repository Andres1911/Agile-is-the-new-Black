import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.models.models import (
    Expense,
    ExpenseShare,
    ExpenseStatus,
    Household,
    HouseholdMember,
    VoteStatus,
)
from app.models.models import User as UserModel
from tests.conftest import login
from tests.conftest import register as register_user

scenarios("features/ID021_Auto_Validate_Expense.feature")


@pytest.fixture()
def context():
    return {}


def get_table_dicts(datatable):
    keys = datatable[0]
    return [dict(zip(keys, row, strict=False)) for row in datatable[1:]]


# ── GIVEN steps ───────────────────────────────────────────────────────────


@given(parsers.parse('household "{hh_name}" exists with members'), target_fixture="context")
def setup_household_with_members(client, db, hh_name, context, datatable):
    rows = get_table_dicts(datatable)
    hh = Household(name=hh_name, invite_code=f"INV_{hh_name[:3].upper()}")
    db.add(hh)
    db.commit()
    db.refresh(hh)
    context["hh_id"] = hh.id
    context["members"] = {}

    for row in rows:
        username = row["member"]
        register_user(
            client,
            username=username,
            email=f"{username.lower()}@test.com",
            password="Password123!",
        )
        user = db.query(UserModel).filter(UserModel.username == username).first()
        is_admin = row["role"].upper() == "ADMIN"
        db.add(HouseholdMember(user_id=user.id, household_id=hh.id, is_admin=is_admin))
        context["members"][username] = user.id

    db.commit()
    return context


@given(
    parsers.parse('user "{creator}" has an existing expense with the following details'),
    target_fixture="context",
)
def setup_expense(db, creator, context, datatable):
    rows = get_table_dicts(datatable)
    row = rows[0]
    creator_id = context["members"][creator]
    expense = Expense(
        description=row["description"],
        amount=float(row["amount"]),
        status=ExpenseStatus[row["status"]],
        creator_id=creator_id,
        household_id=context["hh_id"],
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    context["expense_id"] = expense.id
    context["expense_description"] = row["description"]
    return context


@given(
    parsers.parse("the expense has the following expense shares"),
    target_fixture="context",
)
def setup_shares(db, context, datatable):
    rows = get_table_dicts(datatable)
    # Clear any existing shares for this expense
    db.query(ExpenseShare).filter(ExpenseShare.expense_id == context["expense_id"]).delete()
    db.commit()

    for row in rows:
        user_id = context["members"][row["payer"]]
        share = ExpenseShare(
            expense_id=context["expense_id"],
            user_id=user_id,
            amount_owed=float(row["amount_owed"]),
            vote_status=VoteStatus[row["vote_status"]],
        )
        db.add(share)
    db.commit()
    return context


@given(parsers.parse('"{username}" is logged in'), target_fixture="context")
def step_login(client, username, context):
    auth_resp = login(client, username=username, password="Password123!")
    context["headers"] = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}
    context["logged_in_user"] = username
    return context


# ── WHEN steps ────────────────────────────────────────────────────────────


@when(
    parsers.parse('"{member}" accepts the expense share for "{description}"'),
    target_fixture="context",
)
def member_accepts(client, db, member, description, context):
    auth_resp = login(client, username=member, password="Password123!")
    headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}
    context["response"] = client.post(
        f"/api/v1/expenses/{context['expense_id']}/respond-share",
        json={"decision": "accept"},
        headers=headers,
    )
    return context


@when(
    parsers.parse('"{member}" changes their vote to accepted for "{description}"'),
    target_fixture="context",
)
def member_changes_vote(client, db, member, description, context):
    auth_resp = login(client, username=member, password="Password123!")
    headers = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}
    context["response"] = client.post(
        f"/api/v1/expenses/{context['expense_id']}/respond-share",
        json={"decision": "accept"},
        headers=headers,
    )
    return context


# ── THEN steps ────────────────────────────────────────────────────────────


@then(parsers.parse('the system automatically updates the status of "{description}" to "{status}"'))
def check_finalized(db, description, status, context):
    db.expire_all()
    expense = db.query(Expense).filter(Expense.id == context["expense_id"]).first()
    assert expense.status == ExpenseStatus[status]


@then(parsers.parse('the status of "{description}" remains "{status}"'))
def check_unchanged(db, description, status, context):
    db.expire_all()
    expense = db.query(Expense).filter(Expense.id == context["expense_id"]).first()
    assert expense.status == ExpenseStatus[status]


@then(parsers.parse('the system displays success message "{message}"'))
def check_message(context, message):
    assert context["response"].status_code == 200
    assert context["response"].json()["detail"] == message
