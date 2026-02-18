from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import Household, HouseholdMember
from app.models.models import User as UserModel
from app.schemas.schemas import HouseholdMemberWithUser

router = APIRouter()


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
