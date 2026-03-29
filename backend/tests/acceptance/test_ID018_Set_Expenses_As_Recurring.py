from datetime import UTC, date, datetime

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.models.models import Expense, ExpenseShare, Household, HouseholdMember, User

from ..conftest import auth_header as get_auth_header
from ..conftest import register as register_user

scenarios("features/ID018_Set_Expenses_As_Recurring.feature")


@pytest.fixture()
def context():
    return {
        "split_evenly": True,
        "include_creator": True,
        "manual_shares": None,
        "interval": 1,
        "unit": None,
        "start_at": None,
        "end_at": None,
        "max_occurrences": None,
    }


def _parse_date_utc(date_str: str) -> datetime:
    # Feature files use YYYY-MM-DD
    if "T" not in date_str:
        d = date.fromisoformat(date_str)
        dt = datetime(d.year, d.month, d.day)
    else:
        dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _get_table_dicts(datatable):
    keys = datatable[0]
    return [dict(zip(keys, row, strict=False)) for row in datatable[1:]]


def _freq_to_unit(freq: str) -> str:
    mapping = {
        "daily": "DAILY",
        "weekly": "WEEKLY",
        "monthly": "MONTHLY",
        "yearly": "YEARLY",
    }
    key = freq.strip().lower()
    if key not in mapping:
        raise ValueError(f"Unsupported frequency: {freq}")
    return mapping[key]


@given(parsers.parse('household "{household_name}" exists with members'))
def given_household_exists_with_members(client, db, household_name, datatable):
    members = [row[0] for row in datatable[1:]]

    for name in members:
        register_user(
            client,
            email=f"{name.lower()}@test.com",
            username=name,
            password="Password123!",
            full_name=name,
        )

    users = db.query(User).filter(User.username.in_(members)).all()
    by_name = {u.username: u for u in users}

    hh = Household(name=household_name, invite_code="MAPLE123", description="Test Household")
    db.add(hh)
    db.flush()

    # Make Alice admin to satisfy admin-only recurring creation
    for name in members:
        db.add(
            HouseholdMember(
                user_id=by_name[name].id,
                household_id=hh.id,
                is_admin=(name == "Alice"),
            )
        )

    db.commit()


@given(parsers.parse('the user "{username}" is logged in'), target_fixture="context")
def given_user_logged_in(client, username, context):
    context["auth_headers"] = get_auth_header(client, username=username, password="Password123!")
    context["current_user"] = username
    return context


@when(parsers.parse('"{username}" specifies an expense with the following details'), target_fixture="context")
def when_specifies_expense_details(username, datatable, context):
    data = _get_table_dicts(datatable)[0]
    context["description"] = data["description"]
    context["amount"] = float(data["amountCAD"])
    return context


@when(
    parsers.parse('"{username}" specifies the expense among the following members'),
    target_fixture="context",
)
def when_specifies_manual_split(client, db, username, datatable, context):
    context["split_evenly"] = False

    users = db.query(User).all()
    name_to_id = {u.username: u.id for u in users}

    manual_shares = []
    for row in _get_table_dicts(datatable):
        manual_shares.append(
            {"user_id": name_to_id[row["payer"]], "amount": float(row["shareCAD"]) }
        )

    context["manual_shares"] = manual_shares
    context["include_creator"] = any(s["user_id"] == name_to_id[username] for s in manual_shares)

    return context


@when(
    parsers.parse('"{username}" specifies the expense split equally with include_self="{is_inclusive}"'),
    target_fixture="context",
)
def when_specifies_equal_split(client, username, is_inclusive, context):
    context["split_evenly"] = True
    context["manual_shares"] = None
    context["include_creator"] = is_inclusive.strip().lower() == "true"
    return context


@when(parsers.parse('"{username}" marks the expense as recurring'), target_fixture="context")
def when_marks_as_recurring(username, context):
    context["is_recurring"] = True
    return context


@when(parsers.parse('"{username}" selects frequency "{frequency}"'), target_fixture="context")
def when_selects_frequency(username, frequency, context):
    context["unit"] = _freq_to_unit(frequency)
    context["interval"] = 1
    return context


@when(parsers.parse('"{username}" selects start date "{date_str}"'), target_fixture="context")
def when_selects_start_date(username, date_str, context):
    context["start_at"] = _parse_date_utc(date_str)
    return context


@when(parsers.parse('"{username}" selects end date "{date_str}"'), target_fixture="context")
def when_selects_end_date(username, date_str, context):
    context["end_at"] = _parse_date_utc(date_str)
    return context


@when(parsers.parse('"{username}" selects number of occurrences "{occ}"'), target_fixture="context")
def when_selects_occurrences(username, occ, context):
    context["max_occurrences"] = int(occ)
    return context


@then("the recurring expense is created successfully")
def then_recurring_created_successfully(client, context):
    payload = {
        "description": context.get("description"),
        "amount": context.get("amount"),
        "category": None,
        "split_evenly": context.get("split_evenly"),
        "include_creator": context.get("include_creator"),
        "manual_shares": context.get("manual_shares"),
        "interval": context.get("interval"),
        "unit": context.get("unit"),
        "start_at": context.get("start_at").isoformat() if context.get("start_at") else None,
        "end_at": context.get("end_at").isoformat() if context.get("end_at") else None,
        "max_occurrences": context.get("max_occurrences"),
    }

    # Remove keys that are None to simulate missing fields for error-flow scenarios
    payload = {k: v for k, v in payload.items() if v is not None}

    resp = client.post("/api/v1/expenses/recurring", json=payload, headers=context["auth_headers"])
    context["response"] = resp
    assert resp.status_code == 201, resp.text


@then(parsers.parse('the system generates the following recurring charges'))
def then_system_generates_charges(db, context, datatable):
    assert context["response"].status_code == 201

    expected = _get_table_dicts(datatable)
    desc = expected[0]["description"]

    expenses = (
        db.query(Expense)
        .filter(Expense.description == desc)
        .order_by(Expense.date.asc())
        .all()
    )

    assert len(expenses) == len(expected)

    for exp, row in zip(expenses, expected, strict=False):
        assert exp.description == row["description"]
        assert abs(float(exp.amount) - float(row["amountCAD"])) == 0
        assert exp.date.date().isoformat() == row["date"]

    context["generated_expenses"] = expenses


@then(parsers.parse('the expense has "{n}" sets of the following expense shares'))
def then_expense_has_n_sets_of_shares(db, context, n, datatable):
    expenses = context.get("generated_expenses")
    assert expenses is not None
    assert len(expenses) == int(n)

    expected_rows = _get_table_dicts(datatable)
    name_to_user = {u.username: u for u in db.query(User).all()}

    for expense in expenses:
        shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense.id).all()
        assert len(shares) == len(expected_rows)

        by_user_id = {s.user_id: s for s in shares}
        for row in expected_rows:
            user = name_to_user[row["user"]]
            share = by_user_id[user.id]

            assert abs(float(share.amount_owed) - float(row["amount_owed"])) == 0
            assert abs(float(share.paid_amount) - float(row["paid_amount"])) == 0
            assert bool(share.is_paid) == (row["is_paid"].strip().lower() == "true")
            assert share.vote_status.value == row["vote_status"]


@then(parsers.parse('the message "{message}" is issued'))
def then_message_is_issued(context, message):
    resp = context.get("response")
    assert resp is not None
    assert resp.json().get("detail") == message


@then("the system rejects the recurring expense creation")
def then_system_rejects_creation(client, context):
    payload = {
        "description": context.get("description"),
        "amount": context.get("amount"),
        "category": None,
        "split_evenly": context.get("split_evenly"),
        "include_creator": context.get("include_creator"),
        "manual_shares": context.get("manual_shares"),
        "interval": context.get("interval"),
        "unit": context.get("unit"),
        "start_at": context.get("start_at").isoformat() if context.get("start_at") else None,
        "end_at": context.get("end_at").isoformat() if context.get("end_at") else None,
        "max_occurrences": context.get("max_occurrences"),
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    resp = client.post("/api/v1/expenses/recurring", json=payload, headers=context["auth_headers"])
    context["response"] = resp
    assert resp.status_code == 400, resp.text


@then(parsers.parse('the system displays error message "{message}"'))
def then_system_displays_error_message(context, message):
    resp = context.get("response")
    assert resp is not None
    assert resp.json().get("detail") == message
