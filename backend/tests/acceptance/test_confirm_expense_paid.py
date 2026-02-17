"""Step definitions for ID010_Confirm_expense_is_paid.feature."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.models.models import Expense, ExpenseShare, ExpenseStatus, User
from tests.conftest import auth_header as get_auth_header
from tests.conftest import create_expense as api_create_expense
from tests.conftest import register as register_user

scenarios("features/ID010_Confirm_expense_is_paid.feature")


def get_table_dicts(datatable):
    """Convert list-of-lists datatable to list of dicts (first row = keys)."""
    if not datatable or len(datatable) < 2:
        return []
    keys = [c.strip() for c in datatable[0]]
    return [dict(zip(keys, row, strict=True)) for row in datatable[1:]]


@pytest.fixture()
def context():
    return {"expense_ids": {}}


# ── GIVEN ───────────────────────────────────────────────────────────────────


@given(parsers.parse('household "{household_name}" exists with members'))
def given_household_with_members(client, db, household_name, datatable):
    from app.models.models import Household, HouseholdMember

    rows = get_table_dicts(datatable) if datatable else []
    names = [row["member"].strip() for row in rows] if rows else ["Alice", "Bob", "Cara"]

    for name in names:
        register_user(
            client,
            email=f"{name.lower()}@test.com",
            username=name,
            password="Password123!",
            full_name=name,
        )
    users = [db.query(User).filter(User.username == n).first() for n in names]
    household = Household(
        name=household_name,
        invite_code="MAPLE101",
        description="Test",
    )
    db.add(household)
    db.flush()
    for u in users:
        db.add(
            HouseholdMember(
                user_id=u.id, household_id=household.id, is_admin=(u.username == names[0])
            )
        )
    db.commit()


@given(parsers.parse('user "{username}" has created the following expense'))
def given_alice_created_expense(client, db, context, username, datatable):
    from app.models.models import HouseholdMember

    data = get_table_dicts(datatable)[0]
    expense_id_key = data["expenseId"].strip()
    description = data["description"].strip()
    amount_cad = float(data["amountCAD"])
    # date not used by API

    headers = get_auth_header(client, username=username, password="Password123!")
    user = db.query(User).filter(User.username == username).first()
    membership = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.user_id == user.id, HouseholdMember.left_at.is_(None))
        .first()
    )
    household_id = membership.household_id
    users_in_house = (
        db.query(User)
        .join(HouseholdMember, HouseholdMember.user_id == User.id)
        .filter(HouseholdMember.household_id == household_id, HouseholdMember.left_at.is_(None))
        .all()
    )
    name_to_id = {u.username: u.id for u in users_in_house}
    # Default split for EXP-101: Bob 20, Cara 40 (from feature Background)
    if expense_id_key == "EXP-101":
        manual_shares = [
            {"user_id": name_to_id["Bob"], "amount": 20.0},
            {"user_id": name_to_id["Cara"], "amount": 40.0},
        ]
    elif expense_id_key == "EXP-102":
        manual_shares = [{"user_id": name_to_id["Bob"], "amount": 30.0}]
    else:
        manual_shares = [
            {"user_id": uid, "amount": amount_cad / len(users_in_house)}
            for uid in name_to_id.values()
        ]

    payload = {
        "description": description,
        "amount": amount_cad,
        "category": "Grocery",
        "split_evenly": False,
        "include_creator": False,
        "manual_shares": manual_shares,
    }
    resp = api_create_expense(client, headers, payload)
    assert resp.status_code == 201, resp.text
    expense = (
        db.query(Expense)
        .filter(Expense.creator_id == user.id, Expense.household_id == household_id)
        .order_by(Expense.id.desc())
        .first()
    )
    context["expense_ids"][expense_id_key] = expense.id


@given(parsers.parse('expense "{expense_id}" has the following expense shares'))
def given_expense_has_shares(db, context, expense_id, datatable):
    """Verify (or set) expense shares match table."""
    eid = context["expense_ids"][expense_id]
    expected = get_table_dicts(datatable)
    db.expire_all()
    shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == eid).all()
    for row in expected:
        participant = row["participant"].strip()
        share_cad = float(row["shareCAD"])
        outstanding = float(row["outstandingCAD"])
        status = row["status"].strip()
        user = db.query(User).filter(User.username == participant).first()
        share = next((s for s in shares if s.user_id == user.id), None)
        assert share is not None, f"No share for {participant}"
        assert abs(share.amount_owed - share_cad) < 0.01
        assert abs((share.amount_owed - share.paid_amount) - outstanding) < 0.01
        if status == "Paid":
            assert share.is_paid
        elif status == "Unpaid":
            assert share.paid_amount == 0
        elif status == "Partially Paid":
            assert 0 < share.paid_amount < share.amount_owed


@given(
    parsers.parse('user "{username}" is authenticated as a household member'),
    target_fixture="context",
)
def given_user_authenticated(client, username, context):
    context["auth_headers"] = get_auth_header(client, username=username, password="Password123!")
    context["current_user"] = username
    return context


@given(
    parsers.parse(
        '"{username}" has already confirmed payment of his expense share for expense "{expense_id}"'
    )
)
def given_bob_already_confirmed(client, context, username, expense_id):
    eid = context["expense_ids"][expense_id]
    headers = get_auth_header(client, username=username, password="Password123!")
    resp = client.post(
        f"/api/v1/expenses/{eid}/confirm-payment",
        json={"amount": 20.0},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


@given(
    parsers.parse(
        '"{username}" has already confirmed payment of her expense share for expense "{expense_id}"'
    )
)
def given_cara_already_confirmed(client, context, username, expense_id):
    eid = context["expense_ids"][expense_id]
    headers = get_auth_header(client, username=username, password="Password123!")
    resp = client.post(
        f"/api/v1/expenses/{eid}/confirm-payment",
        json={"amount": 20.0},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


# ── WHEN ───────────────────────────────────────────────────────────────────


@when(
    parsers.parse(
        '"{username}" confirms payment of his expense share for expense "{expense_id}" with amount {amount} CAD'
    )
)
def when_confirm_payment_male(client, context, username, expense_id, amount):
    eid = context["expense_ids"][expense_id]
    headers = context["auth_headers"]
    context["response"] = client.post(
        f"/api/v1/expenses/{eid}/confirm-payment",
        json={"amount": float(amount)},
        headers=headers,
    )


@when(
    parsers.parse(
        '"{username}" confirms payment of her expense share for expense "{expense_id}" with amount {amount} CAD'
    )
)
def when_confirm_payment_female(client, context, username, expense_id, amount):
    eid = context["expense_ids"][expense_id]
    headers = context["auth_headers"]
    context["response"] = client.post(
        f"/api/v1/expenses/{eid}/confirm-payment",
        json={"amount": float(amount)},
        headers=headers,
    )


@when(parsers.parse('"{username}" attempts to confirm payment for expense "{expense_id}"'))
def when_attempt_confirm_no_amount(client, context, username, expense_id):
    eid = context["expense_ids"][expense_id]
    headers = context["auth_headers"]
    context["response"] = client.post(
        f"/api/v1/expenses/{eid}/confirm-payment",
        json={"amount": 30.0},
        headers=headers,
    )


@when(
    parsers.parse(
        '"{username}" attempts to confirm payment of his expense share for expense "{expense_id}" with amount {amount} CAD'
    )
)
def when_attempt_confirm_male(client, context, username, expense_id, amount):
    eid = context["expense_ids"][expense_id]
    headers = context["auth_headers"]
    context["response"] = client.post(
        f"/api/v1/expenses/{eid}/confirm-payment",
        json={"amount": float(amount)},
        headers=headers,
    )


# ── THEN ───────────────────────────────────────────────────────────────────


@then(parsers.parse("the system records the payment"))
def then_system_records_payment(db, context, datatable):
    """Verify 200 response and, if table provided, that the payment is reflected in DB (payer's share)."""
    assert context["response"].status_code == 200
    assert context["response"].json().get("detail") == "Payment recorded"
    if not datatable or len(datatable) < 2:
        return
    rows = get_table_dicts(datatable)
    db.expire_all()
    for row in rows:
        payer = row.get("payer", "").strip()
        expense_id_key = row.get("expenseId", "").strip()
        amount_cad = float(row.get("amountCAD", 0))
        eid = context["expense_ids"][expense_id_key]
        user = db.query(User).filter(User.username == payer).first()
        assert user is not None, f"Payer {payer} not found"
        share = (
            db.query(ExpenseShare)
            .filter(ExpenseShare.expense_id == eid, ExpenseShare.user_id == user.id)
            .first()
        )
        assert share is not None, f"No share for payer {payer} on expense {expense_id_key}"
        assert share.paid_amount >= amount_cad, (
            f"Payment not recorded: {payer} share has paid_amount {share.paid_amount}, expected at least {amount_cad}"
        )


@then(parsers.parse('expense "{expense_id}" has the following updated expense shares'))
def then_expense_has_updated_shares(db, context, expense_id, datatable):
    eid = context["expense_ids"][expense_id]
    expected = get_table_dicts(datatable)
    db.expire_all()
    shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == eid).all()
    for row in expected:
        participant = row["participant"].strip()
        share_cad = float(row["shareCAD"])
        outstanding = float(row["outstandingCAD"])
        status = row["status"].strip()
        user = db.query(User).filter(User.username == participant).first()
        share = next((s for s in shares if s.user_id == user.id), None)
        assert share is not None, f"No share for {participant}"
        assert abs(share.amount_owed - share_cad) < 0.01
        assert abs((share.amount_owed - share.paid_amount) - outstanding) < 0.01
        if status == "Paid":
            assert share.is_paid
        elif status == "Unpaid":
            assert share.paid_amount == 0
        elif status == "Partially Paid":
            assert 0 < share.paid_amount < share.amount_owed


@then(parsers.parse('expense "{expense_id}" status is "{status}"'))
def then_expense_status(db, context, expense_id, status):
    eid = context["expense_ids"][expense_id]
    db.expire_all()
    expense = db.query(Expense).filter(Expense.id == eid).first()
    expected = status.replace(" ", "_").upper()
    assert expense.status == ExpenseStatus[expected]


@then("the system rejects the payment confirmation")
def then_reject_payment(context):
    assert context["response"].status_code == 400


@then(parsers.parse('the system displays error message "{message}"'))
def then_error_message(context, message):
    detail = context["response"].json().get("detail", "")
    assert message.lower() in detail.lower()


@then(parsers.parse('expense "{expense_id}" expense shares remain unchanged'))
def then_expense_shares_unchanged(db, context, expense_id, datatable):
    eid = context["expense_ids"][expense_id]
    expected = get_table_dicts(datatable)
    db.expire_all()
    shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == eid).all()
    for row in expected:
        participant = row["participant"].strip()
        outstanding = float(row["outstandingCAD"])
        user = db.query(User).filter(User.username == participant).first()
        share = next((s for s in shares if s.user_id == user.id), None)
        assert share is not None
        assert abs((share.amount_owed - share.paid_amount) - outstanding) < 0.01


@then(
    parsers.parse(
        '"{username}" expense share for expense "{expense_id}" remains unchanged with outstanding {outstanding} CAD'
    )
)
def then_share_unchanged(db, context, username, expense_id, outstanding):
    eid = context["expense_ids"][expense_id]
    user = db.query(User).filter(User.username == username).first()
    db.expire_all()
    share = (
        db.query(ExpenseShare)
        .filter(ExpenseShare.expense_id == eid, ExpenseShare.user_id == user.id)
        .first()
    )
    assert share is not None
    assert abs((share.amount_owed - share.paid_amount) - float(outstanding)) < 0.01, (
        f"Expected outstanding {outstanding}, got {share.amount_owed - share.paid_amount}"
    )
