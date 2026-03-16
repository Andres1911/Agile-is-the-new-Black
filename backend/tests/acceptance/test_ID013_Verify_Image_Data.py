import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from app.schemas.schemas import ExpenseCreate
from app.api.expenses import verify_and_modify_expense
from app.models.models import (
    Household,
    HouseholdMember,
    User
)
from ..conftest import auth_header as get_auth_header
from ..conftest import register as register_user

# 1. Bind the Feature file
scenarios("features/ID013_Verify_Image_Data.feature")

@pytest.fixture()
def ocr_context():
    """
    Shared context for OCR verification flow.
    """
    return {
        "expense_instance": None, # Holds the initial ExpenseCreate object
        "manual_amount": 0.0,
        "change_amount": False,
        "final_object": None,
        "error": None
    }

# -- Helper functions --

def get_table_dicts(datatable):
    """Convert list-format table to list of dictionaries"""
    keys = datatable[0]
    return [dict(zip(keys, row, strict=False)) for row in datatable[1:]]

# ── BACKGROUND / GIVEN steps for ID013 ───────────────────────────────────

@given(parsers.parse('a user with username "{username}" exists in the system'))
def given_user_exists(client, db, username):
    """
    Registers the user if they don't already exist.
    """
    existing_user = db.query(User).filter(User.username == username).first()
    if not existing_user:
        register_user(
            client,
            email=f"{username.lower()}@test.com",
            username=username,
            password="Password123!",
            full_name=username,
        )

@given(parsers.parse('a household named "{household_name}" exists in the system'))
def given_household_exists(db, household_name):
    """
    Creates the household entity in the database.
    """
    existing_h = db.query(Household).filter(Household.name == household_name).first()
    if not existing_h:
        new_household = Household(
            name=household_name, 
            invite_code="MAPLE123", 
            description="Test Household"
        )
        db.add(new_household)
        db.commit()

@given(parsers.parse('"{username}" is a member of "{household_name}"'))
def given_user_is_member(db, username, household_name):
    """
    Links the user to the household if the relationship doesn't exist.
    """
    user = db.query(User).filter(User.username == username).first()
    household = db.query(Household).filter(Household.name == household_name).first()
    
    membership = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == user.id, 
        HouseholdMember.household_id == household.id
    ).first()
    
    if not membership:
        db.add(HouseholdMember(user_id=user.id, household_id=household.id, is_admin=True))
        db.commit()

@given(parsers.parse('the user "{username}" is logged in'), target_fixture="ocr_context")
def given_user_logged_in(client, username, ocr_context):
    """
    Authenticates the user and stores the headers in the ocr_context.
    """
    ocr_context["auth_headers"] = get_auth_header(client, username=username, password="Password123!")
    ocr_context["current_user"] = username
    return ocr_context

# ── GIVEN steps ───────────────────────────────────────────────────────────

@given(parsers.parse('"{username}" has taken a photo of a receipt'))
def step_user_takes_photo(username):
    pass

@given(
    parsers.parse('the system has processed the image and extracted amount "{amount}" from the receipt'), 
    target_fixture="ocr_context"
)
def step_system_extracts_amount(amount, ocr_context):
    """
    Simulates the system creating an ExpenseCreate object with only the amount initialized.
    Other strings are set to empty or default as per uninitialized state logic.
    """
    ocr_context["expense_instance"] = ExpenseCreate(
        description="",  # Uninitialized/Default
        amount=float(amount),
        category=None,
        split_evenly=True, # Default
        include_creator=True # Default
    )
    return ocr_context

# ── WHEN steps ────────────────────────────────────────────────────────────

@when(
    parsers.parse('"{username}" modifies the extracted data with amount "{new_amount}"'), 
    target_fixture="ocr_context"
)
def step_user_modifies_amount(new_amount, ocr_context):
    """
    Sets the flag to indicate the user wants to override the OCR amount.
    """
    ocr_context["manual_amount"] = float(new_amount)
    ocr_context["change_amount"] = True
    return ocr_context

@when(
    parsers.parse('"{username}" confirms the extracted data with the following details'), 
    target_fixture="ocr_context"
)
def step_user_confirms_details(datatable, ocr_context):
    """
    Executes the logic layer to finalize the expense data.
    Ensures that manual overrides are applied if the change_amount flag is set.
    """
    data = get_table_dicts(datatable)[0]
    
    try:
        # FIX: Changed 'changeAmount' to 'change_amount' to match function definition
        ocr_context["final_object"] = verify_and_modify_expense(
            expense=ocr_context["expense_instance"],
            change_amount=ocr_context["change_amount"], # Must use snake_case
            amount=ocr_context["manual_amount"],
            description=data["description"],
            category=data.get("category")
        )
    except Exception as e:
        # Catch business logic errors (like amount <= 0) or validation errors
        ocr_context["error"] = str(e)

    return ocr_context

# ── THEN steps ────────────────────────────────────────────────────────────

@then(parsers.parse('the data has the following details'))
def step_verify_final_data(ocr_context, datatable):
    expected = get_table_dicts(datatable)[0]
    actual = ocr_context["final_object"]
    
    assert actual is not None, "Final object was not returned."
    assert abs(actual.amount - float(expected["amount"])) == 0
    assert actual.description == expected["description"]
    assert actual.category == expected["category"]

@then(parsers.parse('the system rejects the modification'))
def step_verify_rejection(ocr_context):
    # Verify that either the object wasn't created or an error was captured
    assert ocr_context["final_object"] is None or ocr_context["error"] is not None

@then(parsers.parse('the system displays error message "{error_msg}"'))
def step_verify_error_message(ocr_context, error_msg):
    assert error_msg.lower() in ocr_context["error"].lower()