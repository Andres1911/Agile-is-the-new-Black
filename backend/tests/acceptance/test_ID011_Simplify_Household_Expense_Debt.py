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

# Link to the feature file
scenarios("features/ID011_Simplify_Household_Expense_Debt.feature")


@pytest.fixture()
def context():
    """Fixture to share state between steps."""
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def _get_house(db, name):
    return db.query(Household).filter(Household.name == name).first()


def _get_user(db, username):
    return db.query(User).filter(User.username == username).first()


def _clear_expenses(db, household_id):
    """Remove all expenses (and their shares) for a given household."""
    expense_ids = [
        row[0] for row in db.query(Expense.id).filter(Expense.household_id == household_id).all()
    ]
    if expense_ids:
        db.query(ExpenseShare).filter(ExpenseShare.expense_id.in_(expense_ids)).delete(
            synchronize_session=False
        )
        db.query(Expense).filter(Expense.id.in_(expense_ids)).delete(synchronize_session=False)
    db.flush()


def _seed_debt(db, house, debtor, creditor, amount_str):
    """
    Represent a single net debt as an Expense (paid by creditor) +
    an unpaid ExpenseShare (owed by debtor).
    """
    expense = Expense(
        household_id=house.id,
        creator_id=creditor.id,
        amount=float(amount_str),
        description=f"{debtor.username} owes {creditor.username}",
        status=ExpenseStatus.PENDING,
    )
    db.add(expense)
    db.flush()

    db.add(
        ExpenseShare(
            expense_id=expense.id,
            user_id=debtor.id,
            amount_owed=float(amount_str),
            paid_amount=0.0,
            is_paid=False,
            vote_status=VoteStatus.ACCEPTED,
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# GIVEN
# ─────────────────────────────────────────────────────────────────────────────


@given(
    parsers.parse('household "{household_name}" exists with members'),
    target_fixture="context",
)
def given_household_with_members(db, household_name, datatable, context):
    """
    Create the household and seed every member listed in the Gherkin table.
    Table column: | member |
    """
    house = _get_house(db, household_name)
    if not house:
        house = Household(name=household_name, invite_code="MAPLE123")
        db.add(house)
        db.flush()

    context["household_name"] = household_name
    context["household_id"] = house.id

    for row in datatable[1:]:  # skip header
        member_name = row[0]

        # Use direct DB insert instead of HTTP call to avoid sqlite3 locking
        from app.core.security import get_password_hash

        user = _get_user(db, member_name)
        if not user:
            user = User(
                username=member_name,
                email=f"{member_name.lower()}@test.com",
                password_hash=get_password_hash("Password123!"),
                full_name=member_name,
            )
            db.add(user)
            db.flush()

        already_member = (
            db.query(HouseholdMember)
            .filter(
                HouseholdMember.user_id == user.id,
                HouseholdMember.household_id == house.id,
                HouseholdMember.left_at.is_(None),
            )
            .first()
        )
        if not already_member:
            db.add(HouseholdMember(user_id=user.id, household_id=house.id, is_admin=False))

    db.commit()
    return context


@given(parsers.parse("the following net debts exist between members"))
def given_net_debts_exist(db, datatable, context):
    """
    Seed debt rows from the Gherkin table.
    Table columns: | debtor | creditor | amountCAD |
    Each debt is modelled as an Expense created by the creditor
    with an unpaid ExpenseShare assigned to the debtor.
    """
    house = _get_house(db, context["household_name"])
    _clear_expenses(db, house.id)

    for row in datatable[1:]:
        debtor_name, creditor_name, amount_str = row
        debtor = _get_user(db, debtor_name)
        creditor = _get_user(db, creditor_name)
        _seed_debt(db, house, debtor, creditor, amount_str)

    db.commit()


@given(
    parsers.parse('user "{username}" is authenticated as a household member'),
    target_fixture="context",
)
def given_user_authenticated(db, username, context):
    from app.core.security import create_access_token

    # Generate token directly without HTTP call
    token = create_access_token(data={"sub": username})
    context["auth_headers"] = {"Authorization": f"Bearer {token}"}
    context["acting_user"] = username
    return context


@given(parsers.parse("no outstanding debts exist between members"))
def given_no_debts(db, context):
    house = _get_house(db, context["household_name"])
    _clear_expenses(db, house.id)
    db.commit()


@given(
    parsers.parse('user "{username}" is not a member of household "{household_name}"'),
    target_fixture="context",
)
def given_user_not_a_member(client, db, username, household_name, context):
    # Create user directly in DB and generate token
    from app.core.security import create_access_token, get_password_hash

    user = _get_user(db, username)
    if not user:
        user = User(
            username=username,
            email=f"{username.lower()}@test.com",
            password_hash=get_password_hash("Password123!"),
            full_name=username,
        )
        db.add(user)
        db.flush()

    # Create token directly without HTTP call
    token = create_access_token(data={"sub": username})
    context["auth_headers"] = {"Authorization": f"Bearer {token}"}
    context["acting_user"] = username
    context["household_name"] = household_name

    # Ensure no active membership exists for this user in the target household
    user = _get_user(db, username)
    house = _get_house(db, household_name)
    if user and house:
        db.query(HouseholdMember).filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.household_id == house.id,
            HouseholdMember.left_at.is_(None),
        ).delete()
        db.commit()

    return context


# ─────────────────────────────────────────────────────────────────────────────
# WHEN
# ─────────────────────────────────────────────────────────────────────────────


@when(parsers.parse('"{username}" requests to simplify household debts'))
def when_user_requests_simplify(client, context, username):
    household_name = context["household_name"]
    resp = client.post(
        f"/api/v1/households/{household_name}/debts/simplify",
        headers=context["auth_headers"],
    )
    context["response"] = resp


@when(parsers.parse('"{username}" attempts to simplify household debts'))
def when_non_member_attempts_simplify(client, context, username):
    # Same endpoint — the system should reject the request
    when_user_requests_simplify(client, context, username)


# ─────────────────────────────────────────────────────────────────────────────
# THEN
# ─────────────────────────────────────────────────────────────────────────────


@then(parsers.parse("the system calculates the net balances between all members"))
def then_net_balances_calculated(context):
    # A 200 response confirms the simplification logic was executed
    assert context["response"].status_code == 200


@then(parsers.parse("the system removes the following debts"))
def then_debts_removed(db, datatable, context):
    """Verify that every debt listed in the table no longer exists as an unpaid share."""
    house = _get_house(db, context["household_name"])

    for row in datatable[1:]:
        debtor_name, creditor_name, amount_str = row
        debtor = _get_user(db, debtor_name)
        creditor = _get_user(db, creditor_name)

        share = (
            db.query(ExpenseShare)
            .join(Expense, Expense.id == ExpenseShare.expense_id)
            .filter(
                Expense.household_id == house.id,
                Expense.creator_id == creditor.id,
                ExpenseShare.user_id == debtor.id,
                ExpenseShare.is_paid.is_(False),
            )
            .first()
        )
        assert share is None, (
            f"Expected debt {debtor_name} → {creditor_name} ${amount_str} "
            f"to be removed, but an unpaid share still exists."
        )


@then(parsers.parse("no outstanding debts remain between any members"))
def then_no_debts_remain(db, context):
    house = _get_house(db, context["household_name"])
    unpaid = (
        db.query(ExpenseShare)
        .join(Expense, Expense.id == ExpenseShare.expense_id)
        .filter(Expense.household_id == house.id, ExpenseShare.is_paid.is_(False))
        .all()
    )
    assert len(unpaid) == 0, f"Expected 0 outstanding debts, but found {len(unpaid)}."


@then(parsers.parse("the system offsets the circular portion of {amount} CAD"))
def then_circular_portion_offset(context, amount):
    """
    Verify the API response body reports the expected offset amount.
    The remaining-debts step will confirm the exact DB state.
    """
    assert context["response"].status_code == 200
    resp_body = context["response"].json()
    offset = float(resp_body.get("offset_amount", 0))
    assert offset == float(amount), f"Expected offset of {amount} CAD, got {offset}."


@then(parsers.parse("the following debts remain"))
def then_debts_remain(db, datatable, context):
    """Verify that exactly the listed debts (and no others) are still unpaid."""
    house = _get_house(db, context["household_name"])

    expected = set()
    for row in datatable[1:]:
        debtor_name, creditor_name, amount_str = row
        debtor = _get_user(db, debtor_name)
        creditor = _get_user(db, creditor_name)
        expected.add((debtor.id, creditor.id, float(amount_str)))

    rows = (
        db.query(ExpenseShare, Expense)
        .join(Expense, Expense.id == ExpenseShare.expense_id)
        .filter(Expense.household_id == house.id, ExpenseShare.is_paid.is_(False))
        .all()
    )
    actual = {(share.user_id, expense.creator_id, expense.amount) for share, expense in rows}

    assert actual == expected, f"Debt mismatch.\n  Expected: {expected}\n  Actual:   {actual}"


@then(parsers.parse("the system removes the intermediate debt"))
def then_intermediate_debt_removed(db, datatable, context):
    """Chain simplification — intermediate debts are removed just like any other."""
    then_debts_removed(db, datatable, context)


@then(parsers.parse("the system creates a simplified debt"))
def then_simplified_debt_created(db, datatable, context):
    """Verify each debt listed in the table now exists as an unpaid share."""
    house = _get_house(db, context["household_name"])

    for row in datatable[1:]:
        debtor_name, creditor_name, amount_str = row
        debtor = _get_user(db, debtor_name)
        creditor = _get_user(db, creditor_name)

        share = (
            db.query(ExpenseShare)
            .join(Expense, Expense.id == ExpenseShare.expense_id)
            .filter(
                Expense.household_id == house.id,
                Expense.creator_id == creditor.id,
                ExpenseShare.user_id == debtor.id,
                ExpenseShare.amount_owed == float(amount_str),
                ExpenseShare.is_paid.is_(False),
            )
            .first()
        )
        assert share is not None, (
            f"Expected simplified debt {debtor_name} → {creditor_name} "
            f"${amount_str} to exist, but it was not found."
        )


@then(parsers.parse("the system determines no circular or chain simplifications exist"))
def then_no_simplification_possible(context):
    assert context["response"].status_code == 200
    resp_body = context["response"].json()
    assert resp_body.get("simplifications_applied", -1) == 0, (
        "Expected zero simplifications to be applied."
    )


@then(parsers.parse("all debts remain unchanged"))
def then_all_debts_unchanged(db, context):
    """
    Debts are independent — none should have been removed or altered.
    We just confirm at least one unpaid share still exists.
    """
    house = _get_house(db, context["household_name"])
    unpaid = (
        db.query(ExpenseShare)
        .join(Expense, Expense.id == ExpenseShare.expense_id)
        .filter(Expense.household_id == house.id, ExpenseShare.is_paid.is_(False))
        .all()
    )
    assert len(unpaid) > 0, "Expected debts to remain unchanged, but none were found."


@then(parsers.parse("the system performs no changes"))
def then_no_changes_performed(db, context):
    house = _get_house(db, context["household_name"])
    expenses = db.query(Expense).filter(Expense.household_id == house.id).all()
    assert len(expenses) == 0, f"Expected no expenses to exist, but found {len(expenses)}."


@then(parsers.parse("the system rejects the request"))
def then_request_rejected(context):
    assert context["response"].status_code in [401, 403], (
        f"Expected 401 or 403, got {context['response'].status_code}."
    )


@then(parsers.parse('the system displays message "{message}"'))
def then_success_message_displayed(context, message):
    assert context["response"].status_code == 200
    resp_body = context["response"].json()
    assert message.lower() in resp_body.get("message", "").lower(), (
        f"Expected message containing '{message}', got: '{resp_body.get('message')}'"
    )


@then(parsers.parse('the system displays error message "{message}"'))
def then_error_message_displayed(context, message):
    assert context["response"].status_code in [401, 403]
    resp_body = context["response"].json()
    assert message.lower() in resp_body.get("detail", "").lower(), (
        f"Expected error detail containing '{message}', got: '{resp_body.get('detail')}'"
    )
