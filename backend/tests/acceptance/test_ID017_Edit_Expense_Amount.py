import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.models.models import (
    Expense,
    ExpenseShare,
    ExpenseStatus,
    Household,
    HouseholdMember,
    User,
    VoteStatus,
)

from ..conftest import auth_header as get_auth_header
from ..conftest import register as register_user

# 1. Bind Feature file
scenarios("features/ID017_Edit_Expense_Amount.feature")


@pytest.fixture()
def context():
    """Shared context"""
    return {}


# -- Helper functions --


def get_table_dicts(datatable):
    """Convert list-format table to list of dictionaries"""
    keys = datatable[0]
    return [dict(zip(keys, row, strict=False)) for row in datatable[1:]]


# ── GIVEN steps ───────────────────────────────────────────────────────────


@given(parsers.parse('household "{household_name}" exists with members'))
def given_household_with_members(client, db, household_name, context):
    names = ["Alice", "Bob", "Cara"]
    user_objects = []

    for name in names:
        register_user(
            client,
            email=f"{name.lower()}@test.com",
            username=name,
            password="Password123!",
            full_name=name,
        )
        user = db.query(User).filter(User.username == name).first()
        user_objects.append(user)

    alice, bob, cara = user_objects

    new_household = Household(
        name=household_name, invite_code="MAPLE123", description="Test Household"
    )
    db.add(new_household)
    db.flush()

    db.add(HouseholdMember(user_id=alice.id, household_id=new_household.id, is_admin=True))
    db.add(HouseholdMember(user_id=bob.id, household_id=new_household.id, is_admin=False))
    db.add(HouseholdMember(user_id=cara.id, household_id=new_household.id, is_admin=False))
    db.commit()

    context["household_name"] = household_name


@given(parsers.parse('user "{username}" is logged in'), target_fixture="context")
def given_user_logged_in(client, username, context):
    context["auth_headers"] = get_auth_header(client, username=username, password="Password123!")
    context["current_user"] = username
    return context


@given(
    parsers.parse('"{username}" has an existing expense with the following details'),
    target_fixture="context",
)
def given_existing_expense(db, username, datatable, context):
    data = get_table_dicts(datatable)[0]
    user = db.query(User).filter(User.username == username).first()

    membership = db.query(HouseholdMember).filter(HouseholdMember.user_id == user.id).first()

    category = data.get("category")
    if not category or category == "None":
        category = None

    status_str = data.get("status", "PENDING")
    status = ExpenseStatus[status_str.upper()]

    expense = Expense(
        description=data["description"],
        amount=float(data["amount"]),
        category=category,
        creator_id=user.id,
        household_id=membership.household_id,
        status=status,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    context["expense"] = expense
    context["expense_id"] = expense.id
    return context


@given("the expense has the following expense shares")
def given_expense_shares(db, datatable, context):
    expense = context["expense"]
    rows = get_table_dicts(datatable)

    for row in rows:
        user = db.query(User).filter(User.username == row["payer"]).first()
        share = ExpenseShare(
            expense_id=expense.id,
            user_id=user.id,
            amount_owed=float(row["amount_owed"]),
            paid_amount=float(row["paid_amount"]),
            is_paid=row["is_paid"].strip().lower() == "true",
            vote_status=VoteStatus[row["vote_status"].strip().upper()],
        )
        db.add(share)
    db.commit()


@given(parsers.parse('"{username}" leaves household "{household_name}"'))
def given_user_leaves_household(db, username, household_name):
    user = db.query(User).filter(User.username == username).first()
    household = db.query(Household).filter(Household.name == household_name).first()
    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == household.id,
        )
        .first()
    )
    from datetime import UTC, datetime

    membership.left_at = datetime.now(UTC)
    db.commit()


# ── WHEN steps ────────────────────────────────────────────────────────────


@when(
    parsers.parse('"{username}" edits the expense amount to "{new_amount}"'),
    target_fixture="context",
)
def when_edit_expense_amount(username, new_amount, context):
    context["new_amount"] = float(new_amount)
    return context


@when(
    parsers.parse('"{username}" manually updates the expense shares with the following amounts'),
    target_fixture="context",
)
def when_manual_resplit(client, db, username, datatable, context):
    rows = get_table_dicts(datatable)
    manual_shares = []
    for row in rows:
        user = db.query(User).filter(User.username == row["payer"]).first()
        manual_shares.append({"user_id": user.id, "amount": float(row["amount_owed"])})

    payload = {
        "amount": context["new_amount"],
        "split_evenly": False,
        "include_self": False,
        "manual_shares": manual_shares,
    }

    context["response"] = client.put(
        f"/api/v1/expenses/{context['expense_id']}/edit-amount",
        json=payload,
        headers=context["auth_headers"],
    )
    return context


@when(
    parsers.parse('"{username}" resplits the expense equally with include_self="{include_self}"'),
    target_fixture="context",
)
def when_equal_resplit(client, username, include_self, context):
    payload = {
        "amount": context["new_amount"],
        "split_evenly": True,
        "include_self": include_self.lower() == "true",
    }

    context["response"] = client.put(
        f"/api/v1/expenses/{context['expense_id']}/edit-amount",
        json=payload,
        headers=context["auth_headers"],
    )
    return context


# ── THEN steps ────────────────────────────────────────────────────────────


@then(
    parsers.parse(
        'the system updates that expense for "{username}" in "{h_name}" with amount "{amount}"'
    )
)
def then_verify_expense_updated(db, context, username, h_name, amount):
    assert context["response"].status_code == 200

    user = db.query(User).filter(User.username == username).first()
    household = db.query(Household).filter(Household.name == h_name).first()

    db.expire_all()
    expense = db.query(Expense).filter(Expense.id == context["expense_id"]).first()

    assert expense is not None
    assert expense.creator_id == user.id
    assert expense.household_id == household.id
    assert abs(expense.amount - float(amount)) == 0

    context["last_expense"] = expense


@then(
    parsers.parse(
        'the description "{desc}", category "{cat}", and status "{status}" remain unchanged'
    )
)
def then_verify_unchanged_fields(db, context, desc, cat, status):
    db.expire_all()
    expense = db.query(Expense).filter(Expense.id == context["expense_id"]).first()

    assert expense.description == desc

    expected_category = None if cat == "None" else cat
    assert expense.category == expected_category

    expected_status = ExpenseStatus[status.upper()]
    assert expense.status == expected_status


@then("the expense has the following expense shares")
def then_verify_expense_shares(db, context, datatable):
    expense_id = context["expense_id"]
    expected_shares = get_table_dicts(datatable)

    db.expire_all()
    actual_shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).all()

    assert len(actual_shares) == len(expected_shares), (
        f"Share count mismatch: Expected {len(expected_shares)}, got {len(actual_shares)}"
    )

    for expected in expected_shares:
        user = db.query(User).filter(User.username == expected["payer"]).first()
        assert user is not None

        actual = next((s for s in actual_shares if s.user_id == user.id), None)
        assert actual is not None, f"No share found for user: {user.username}"

        assert abs(actual.amount_owed - float(expected["amount_owed"])) == 0, (
            f"amount_owed mismatch for {user.username}: expected {expected['amount_owed']}, got {actual.amount_owed}"
        )
        assert abs(actual.paid_amount - float(expected["paid_amount"])) == 0, (
            f"paid_amount mismatch for {user.username}"
        )

        expected_is_paid = expected["is_paid"].strip().lower() == "true"
        assert actual.is_paid == expected_is_paid, f"is_paid mismatch for {user.username}"

        expected_vote = VoteStatus[expected["vote_status"].strip().upper()]
        assert actual.vote_status == expected_vote, (
            f"vote_status mismatch for {user.username}: expected {expected_vote}, got {actual.vote_status}"
        )


@then(parsers.parse("the system rejects the expense modification"))
def then_check_rejection(context):
    assert context["response"].status_code == 400


@then(parsers.parse('the system displays error message "{error_msg}"'))
def then_check_error_message(context, error_msg):
    detail = context["response"].json()["detail"]
    assert error_msg.lower() in detail.lower()
