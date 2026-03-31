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
from tests.conftest import auth_header, register

scenarios("features/ID015_Accept_Or_Decline_Requested_Expense.feature")


@pytest.fixture()
def context():
    return {}


def get_table_dicts(datatable):
    keys = datatable[0]
    return [dict(zip(keys, row, strict=False)) for row in datatable[1:]]


@given(parsers.parse('household "{household_name}" exists with members'), target_fixture="context")
def given_household_exists_with_members(client, db, household_name, datatable, context):
    household = Household(name=household_name, invite_code=f"{household_name[:3].upper()}101")
    db.add(household)
    db.commit()
    db.refresh(household)

    context["household_id"] = household.id
    context["members"] = {}

    for row in get_table_dicts(datatable):
        username = row["member"]
        register(
            client,
            email=f"{username.lower()}@test.com",
            username=username,
            password="Password123!",
            full_name=username,
        )
        user = db.query(User).filter(User.username == username).first()
        context["members"][username] = user.id
        db.add(
            HouseholdMember(
                user_id=user.id,
                household_id=household.id,
                is_admin=(username == "Alice"),
            )
        )
        db.commit()

    return context


@given(parsers.parse('user "{creator}" has created the following expense'), target_fixture="context")
def given_user_has_created_expense(db, creator, datatable, context):
    row = get_table_dicts(datatable)[0]
    expense = Expense(
        description=row["description"],
        amount=float(row["amountCAD"]),
        status=ExpenseStatus[row["status"]],
        creator_id=context["members"][creator],
        household_id=context["household_id"],
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)

    context["expense_id"] = expense.id
    context["expense_description"] = expense.description
    return context


@given("that expense has the following expense shares", target_fixture="context")
def given_expense_has_shares(db, datatable, context):
    expense_id = context["expense_id"]
    db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense_id).delete()
    db.commit()

    for row in get_table_dicts(datatable):
        outstanding = float(row["outstandingCAD"])
        share_amount = float(row["shareCAD"])
        paid_amount = round(share_amount - outstanding, 2)
        share = ExpenseShare(
            expense_id=expense_id,
            user_id=context["members"][row["participant"]],
            amount_owed=share_amount,
            paid_amount=paid_amount,
            is_paid=outstanding <= 0,
            vote_status=VoteStatus[row["vote_status"]],
        )
        db.add(share)

    db.commit()
    return context


@given(parsers.parse('"{username}" is logged in'), target_fixture="context")
def given_user_logged_in(client, username, context):
    context["headers"] = auth_header(client, username=username, password="Password123!")
    context["active_user"] = username
    return context


@given(parsers.parse('"{username}" has "{decision}" share for "{description}"'), target_fixture="context")
def given_user_already_voted(db, username, decision, description, context):
    expense = db.query(Expense).filter(Expense.description == description).first()
    share = (
        db.query(ExpenseShare)
        .filter(
            ExpenseShare.expense_id == expense.id,
            ExpenseShare.user_id == context["members"][username],
        )
        .first()
    )
    share.vote_status = VoteStatus[decision]

    all_shares = db.query(ExpenseShare).filter(ExpenseShare.expense_id == expense.id).all()
    expense.status = (
        ExpenseStatus.FINALIZED
        if all(s.vote_status == VoteStatus.ACCEPTED for s in all_shares)
        else ExpenseStatus.DISPUTED
        if any(s.vote_status == VoteStatus.REJECTED for s in all_shares)
        else ExpenseStatus.PENDING
    )
    db.commit()
    return context


@when(parsers.parse('"{username}" "{decision}" the share for "{description}"'), target_fixture="context")
def when_user_responds_to_share(client, db, username, decision, description, context):
    expense = db.query(Expense).filter(Expense.description == description).first()
    api_decision = "accept" if decision == "ACCEPTED" else "decline"
    context["response"] = client.post(
        f"/api/v1/expenses/{expense.id}/respond-share",
        json={"decision": api_decision},
        headers=context["headers"],
    )
    return context


@when(parsers.parse('"{username}" attempts to "{decision}" the share for "{description}"'), target_fixture="context")
def when_user_attempts_invalid_response(client, db, username, decision, description, context):
    expense = db.query(Expense).filter(Expense.description == description).first()
    api_decision = "accept" if decision == "ACCEPTED" else "decline"
    context["response"] = client.post(
        f"/api/v1/expenses/{expense.id}/respond-share",
        json={"decision": api_decision},
        headers=context["headers"],
    )
    return context


@then(parsers.parse('the status for the "{description}" expense should be "{status}"'))
def then_expense_status_should_be(db, description, status):
    expense = db.query(Expense).filter(Expense.description == description).first()
    assert expense.status == ExpenseStatus[status]


@then(parsers.parse('the expense shares for "{description}" should be as follows'))
def then_expense_shares_should_match(db, description, datatable):
    expense = db.query(Expense).filter(Expense.description == description).first()
    expected_rows = get_table_dicts(datatable)

    shares = (
        db.query(ExpenseShare, User)
        .join(User, User.id == ExpenseShare.user_id)
        .filter(ExpenseShare.expense_id == expense.id)
        .order_by(User.username.asc())
        .all()
    )

    actual_rows = []
    for share, user in shares:
        actual_rows.append(
            {
                "participant": user.username,
                "shareCAD": f"{float(share.amount_owed):.2f}",
                "outstandingCAD": f"{float(share.amount_owed - share.paid_amount):.2f}",
                "vote_status": share.vote_status.value,
            }
        )

    expected_normalized = sorted(expected_rows, key=lambda row: row["participant"])
    actual_normalized = sorted(actual_rows, key=lambda row: row["participant"])
    assert actual_normalized == expected_normalized


@then(parsers.parse('the system should return an error message "{message}"'))
def then_error_message_should_match(context, message):
    assert context["response"].status_code == 400
    assert context["response"].json()["detail"] == message
