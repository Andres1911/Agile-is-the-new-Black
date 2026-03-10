from datetime import UTC, datetime, timedelta

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from app.models.models import Expense, ExpenseShare, Household, HouseholdMember, User, VoteStatus
from tests.conftest import login
from tests.conftest import register as register_user

scenarios("features/ID009_View_Outstanding_Expenses.feature")


@pytest.fixture()
def context():
    return {}


def get_table_dicts(datatable):
    """Converts the list-style datatable into a list of dictionaries"""
    keys = datatable[0]
    return [dict(zip(keys, row, strict=False)) for row in datatable[1:]]


def _get_user(db, username: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    assert user is not None, f"User '{username}' not found"
    return user


def _get_or_create_user(db, username: str) -> User:
    """Get user or create if doesn't exist."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        from app.core.security import get_password_hash
        user = User(
            username=username,
            email=f"{username.lower()}@test.com",
            password_hash=get_password_hash("Password123!"),
            full_name=username,
        )
        db.add(user)
        db.flush()
    return user


def _get_household(db, name: str) -> Household:
    hh = db.query(Household).filter(Household.name == name).first()
    assert hh is not None, f"Household '{name}' not found"
    return hh


# ── GIVEN ────────────────────────────────────────────────────────────────


@given(
    parsers.parse('a user with username "{username}" exists in the system'),
    target_fixture="context",
)
def given_user_exists(client, username, context):
    register_user(
        client,
        username=username,
        email=f"{username.lower()}@test.com",
        password="Password123!",
        full_name=username,
    )
    return context


@given(parsers.parse('a household named "{name}" exists in the system'), target_fixture="context")
def given_household_exists(db, name, context):
    hh = db.query(Household).filter(Household.name == name).first()
    if not hh:
        hh = Household(name=name, invite_code=f"INV_{name[:3].upper()}")
        db.add(hh)
        db.commit()
        db.refresh(hh)
    return context


@given(parsers.parse('"{username}" is a member of "{hh_name}"'), target_fixture="context")
def given_household_member(db, username, hh_name, context):
    user = _get_user(db, username)
    hh = _get_household(db, hh_name)

    m = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.user_id == user.id, HouseholdMember.household_id == hh.id)
        .first()
    )
    if not m:
        db.add(HouseholdMember(user_id=user.id, household_id=hh.id, left_at=None))
        db.commit()
    return context


@given(
    parsers.parse('the following expense shares exist for "{hh_name}"'), target_fixture="context"
)
def given_expense_shares(db, hh_name, datatable, context):
    """
    Seed data so the endpoint can compute:
      Sum amount_owed where is_paid=False and vote_status=ACCEPTED
    Conventions used here (matches your existing tests):
      - Expense.creator_id represents the Payee (who paid)
      - ExpenseShare.user_id represents the Payer (who owes that share)
    """
    hh = _get_household(db, hh_name)
    rows = get_table_dicts(datatable)

    for i, row in enumerate(rows):
        desc = row["ExpenseDescription"]
        payee_name = row["Payee"]
        payer_name = row["Payer"]
        amount_owed = float(row["AmountOwed"])
        vote_status = VoteStatus[row["VoteStatus"].upper()]
        is_paid = row["IsPaid"].strip().lower() == "true"

        payee = _get_or_create_user(db, payee_name)
        payer = _get_or_create_user(db, payer_name)

        # Create an expense (date offset keeps deterministic ordering if needed)
        exp = Expense(
            description=desc,
            amount=amount_owed,
            household_id=hh.id,
            creator_id=payee.id,
            date=datetime.now(UTC) + timedelta(seconds=i),
        )
        db.add(exp)
        db.flush()  # gives exp.id

        share = ExpenseShare(
            expense_id=exp.id,
            user_id=payer.id,
            amount_owed=amount_owed,
            paid_amount=(amount_owed if is_paid else 0.0),
            is_paid=is_paid,
            vote_status=vote_status,
        )
        db.add(share)

    db.commit()
    return context


@given(parsers.parse('the user "{username}" is logged in'), target_fixture="context")
def given_logged_in(client, username, context):
    auth_resp = login(client, username=username, password="Password123!")
    assert auth_resp.status_code == 200
    context["headers"] = {"Authorization": f"Bearer {auth_resp.json()['access_token']}"}
    return context


@given(parsers.parse('all expense shares for "{username}" in "{hh_name}" are marked as paid'))
def given_all_shares_paid(db, username, hh_name):
    hh = _get_household(db, hh_name)
    user = _get_user(db, username)

    # Mark all shares where user is the payer
    payer_shares = (
        db.query(ExpenseShare)
        .join(Expense, ExpenseShare.expense_id == Expense.id)
        .filter(Expense.household_id == hh.id, ExpenseShare.user_id == user.id)
        .all()
    )
    for s in payer_shares:
        s.is_paid = True
        s.paid_amount = s.amount_owed

    # Mark all shares where user is the payee (expense creator)
    payee_shares = (
        db.query(ExpenseShare)
        .join(Expense, ExpenseShare.expense_id == Expense.id)
        .filter(Expense.household_id == hh.id, Expense.creator_id == user.id)
        .all()
    )
    for s in payee_shares:
        s.is_paid = True
        s.paid_amount = s.amount_owed

    db.commit()


@given(parsers.parse('"{username}" is logged in'), target_fixture="context")
def given_logged_in_alias(client, username, context):
    # Reuse same behavior
    return given_logged_in(client, username, context)


@given(parsers.parse('"{username}" is not a member of any household'))
def given_not_member_any_household(db, username):
    user = _get_user(db, username)
    db.query(HouseholdMember).filter(HouseholdMember.user_id == user.id).delete()
    db.commit()


# ── WHEN ────────────────────────────────────────────────────────────────


@when(
    parsers.parse('"{username}" requests her balances using GET "{path}"'), target_fixture="context"
)
@when(parsers.parse('"{username}" requests balances using GET "{path}"'), target_fixture="context")
def when_get_balances(client, username, path, context):
    # Normalize to /api/v1 like other acceptance tests do
    if path.startswith("/users/"):
        path = "/api/v1" + path

    context["response"] = client.get(path, headers=context.get("headers", {}))
    return context


# ── THEN ────────────────────────────────────────────────────────────────


@then(
    parsers.parse(
        'the household "{hh_name}" should show outstanding owed by "{username}" of {amt:f} CAD'
    )
)
def then_household_owed_by(context, hh_name, username, amt):
    assert context["response"].status_code == 200
    data = context["response"].json()

    # Expected response shape (your team can implement to match):
    # {"households":[{"name":"MapleHouse","owed_by_me":150.0,"owed_to_me":60.0}], "shares":[...]}
    households = data.get("households", [])
    hh = next((h for h in households if h.get("name") == hh_name), None)
    assert hh is not None, f"Household '{hh_name}' missing from response: {data}"

    assert abs(float(hh.get("owed_by_me", 0.0)) - amt) < 0.01


@then(
    parsers.parse(
        'the response should include {count:d} outstanding shares where payer is "{username}"'
    )
)
def then_count_payer_shares(context, count, username):
    assert context["response"].status_code == 200
    data = context["response"].json()
    shares = data.get("shares", [])
    payer_shares = [s for s in shares if s.get("payer") == username]
    assert len(payer_shares) == count


@then(parsers.parse('the response should not include shares with vote status not "ACCEPTED"'))
def then_no_non_accepted(context):
    assert context["response"].status_code == 200
    data = context["response"].json()
    shares = data.get("shares", [])
    assert all(s.get("vote_status") == "ACCEPTED" for s in shares), f"Found non-ACCEPTED: {shares}"


@then("the response should not include shares marked as paid")
def then_no_paid(context):
    assert context["response"].status_code == 200
    data = context["response"].json()
    shares = data.get("shares", [])
    assert all(s.get("is_paid") is False for s in shares), f"Found paid shares: {shares}"


@then(
    parsers.parse(
        'the household "{hh_name}" should show outstanding owed to "{username}" of {amt:f} CAD'
    )
)
def then_household_owed_to(context, hh_name, username, amt):
    assert context["response"].status_code == 200
    data = context["response"].json()

    households = data.get("households", [])
    hh = next((h for h in households if h.get("name") == hh_name), None)
    assert hh is not None, f"Household '{hh_name}' missing from response: {data}"

    assert abs(float(hh.get("owed_to_me", 0.0)) - amt) < 0.01


@then(
    parsers.parse(
        'the response should include {count:d} outstanding share where payee is "{username}"'
    )
)
@then(
    parsers.parse(
        'the response should include {count:d} outstanding shares where payee is "{username}"'
    )
)
def then_count_payee_shares(context, count, username):
    assert context["response"].status_code == 200
    data = context["response"].json()
    shares = data.get("shares", [])
    payee_shares = [s for s in shares if s.get("payee") == username]
    assert len(payee_shares) == count


@then(parsers.parse('the response should include a summary for household "{hh_name}"'))
def then_has_summary(context, hh_name):
    assert context["response"].status_code == 200
    data = context["response"].json()
    households = data.get("households", [])
    hh = next((h for h in households if h.get("name") == hh_name), None)
    assert hh is not None
    # "summary" could be the household object itself; this step just confirms it exists.


@then(parsers.parse('the summary total outstanding owed by "{username}" should be {amt:f} CAD'))
def then_summary_total_owed_by(context, username, amt):
    assert context["response"].status_code == 200
    data = context["response"].json()

    # If multiple households exist, your API can include a global total as well.
    # Here we prefer the sum across all households in the response.
    households = data.get("households", [])
    total = sum(float(h.get("owed_by_me", 0.0)) for h in households)
    assert abs(total - amt) < 0.01


@then(parsers.parse('the summary total outstanding owed to "{username}" should be {amt:f} CAD'))
def then_summary_total_owed_to(context, username, amt):
    assert context["response"].status_code == 200
    data = context["response"].json()

    households = data.get("households", [])
    total = sum(float(h.get("owed_to_me", 0.0)) for h in households)
    assert abs(total - amt) < 0.01


@then(parsers.parse('the message "{message}" is issued'))
def then_message(context, message):
    resp_data = context["response"].json()

    # Keep same pattern as ID008 test
    detail = resp_data.get("detail", "") if isinstance(resp_data, dict) else str(resp_data)
    assert message in str(detail)


@then("no balance data should be returned")
def then_no_balance_data(context):
    assert context["response"].status_code >= 400
