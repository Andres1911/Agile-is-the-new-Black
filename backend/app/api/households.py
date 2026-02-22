import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import Household, HouseholdMember
from app.models.models import User as UserModel
from app.schemas.schemas import Household as HouseholdSchema
from app.schemas.schemas import HouseholdCreate, HouseholdMemberWithUser

router = APIRouter()


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
    invite_code = str(uuid.uuid4())[:8].upper()
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
