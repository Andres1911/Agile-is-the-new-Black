from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.invite_codes import generate_unique_invite_code
from app.db.database import get_db
from app.models.models import Expense, Household, HouseholdMember
from app.models.models import User as UserModel
from app.schemas.schemas import Expense as ExpenseSchema
from app.schemas.schemas import Household as HouseholdSchema
from app.schemas.schemas import HouseholdCreate, HouseholdMemberWithUser

router = APIRouter()

# This is a helper method, currently only used by the frontend to get the list of active household members for the current user, but could be useful for other purposes in the future as well
@router.get("/me/active-household-members")
def get_current_user_active_household_members(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # Find which household the current user is active in
    membership = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == current_user.id,
        HouseholdMember.left_at.is_(None)
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="No active household found")

    # Fetch all users in that household
    users = db.query(UserModel).join(
        HouseholdMember, HouseholdMember.user_id == UserModel.id
    ).filter(
        HouseholdMember.household_id == membership.household_id,
        HouseholdMember.left_at.is_(None)
    ).all()

    return {
        "household_id": membership.household_id,
        "members": [
            {"id": u.id, "username": u.username, "full_name": u.full_name}
            for u in users
        ]
    }


@router.post("/", response_model=HouseholdSchema, status_code=status.HTTP_201_CREATED)
def create_household(
    household_in: HouseholdCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Create a Household

    Rules:
    - User that creates the household is automatically set as the admin of this household
    - Have to make sure that household name doesnt previously exist
    - User that creates a new household should not be currently registered in a household
    """

    # Check for duplicate name
    existing_hh = db.query(Household).filter(Household.name == household_in.name).first()
    if existing_hh:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name already exists")

    # Check if user is already an active member elsewhere
    active_membership = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.user_id == current_user.id, HouseholdMember.left_at.is_(None))
        .first()
    )

    if active_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already registered as living in another household",
        )

    # Create the Household
    invite_code = generate_unique_invite_code(db)
    new_household = Household(
        name=household_in.name,
        description=household_in.description,
        address=household_in.address,
        invite_code=invite_code,
    )
    db.add(new_household)
    db.flush()

    # Create the Admin Binding
    new_member = HouseholdMember(
        user_id=current_user.id, household_id=new_household.id, is_admin=True
    )
    db.add(new_member)

    db.commit()
    db.refresh(new_household)

    return new_household


@router.get("/{household_id}/members", response_model=list[HouseholdMemberWithUser])
def get_household_members(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Return the list of members for a household.

    Rules:
    - The household must exist.
    - The requesting user must be an active member of that household.
    """
    # Check household exists
    household = db.query(Household).filter(Household.id == household_id).first()
    if household is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found",
        )

    # Check requesting user is a member
    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == current_user.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this household",
        )

    # Return all active members of the household
    members = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.left_at.is_(None),
        )
        .all()
    )
    return members


@router.get("/{household_id}/expenses", response_model=list[ExpenseSchema])
def get_household_expense_history(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Return the history of expenses for a household.

    Rules:
    - The household must exist.
    - The requesting user must be an active member of that household.
    - Return list sorted by date (newest first).
    """
    # Check household exists
    household = db.query(Household).filter(Household.id == household_id).first()
    if household is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found",
        )

    # check requesting user is an active member
    membership = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == current_user.id,
            HouseholdMember.left_at.is_(None),
        )
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this household",
        )

    # Return all expenses for the household
    # .order_by(Expense.date.desc()) ensures the history view shows recent items first
    expenses = (
        db.query(Expense)
        .filter(Expense.household_id == household_id)
        .order_by(Expense.date.desc())
        .all()
    )

    return expenses
