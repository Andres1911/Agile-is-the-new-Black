from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.models import Household as HouseholdModel, User as UserModel
from app.schemas.schemas import Household, HouseholdCreate, HouseholdWithMembers
from app.api.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=Household, status_code=status.HTTP_201_CREATED)
def create_household(
    household_in: HouseholdCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_household = HouseholdModel(
        **household_in.model_dump(),
        created_by=current_user.id
    )
    db_household.members.append(current_user)
    db.add(db_household)
    db.commit()
    db.refresh(db_household)
    return db_household


@router.get("/", response_model=List[HouseholdWithMembers])
def read_households(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    return current_user.households[skip:skip+limit]


@router.get("/{household_id}", response_model=HouseholdWithMembers)
def read_household(
    household_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    household = db.query(HouseholdModel).filter(HouseholdModel.id == household_id).first()
    if household is None:
        raise HTTPException(status_code=404, detail="Household not found")
    
    # Check if user is member
    if current_user not in household.members:
        raise HTTPException(status_code=403, detail="Not a member of this household")
    
    return household


@router.post("/{household_id}/members/{user_id}", response_model=HouseholdWithMembers)
def add_member_to_household(
    household_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    household = db.query(HouseholdModel).filter(HouseholdModel.id == household_id).first()
    if household is None:
        raise HTTPException(status_code=404, detail="Household not found")
    
    # Check if current user is the creator
    if household.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can add members")
    
    # Check if user exists
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already a member
    if user in household.members:
        raise HTTPException(status_code=400, detail="User already a member")
    
    household.members.append(user)
    db.commit()
    db.refresh(household)
    return household


@router.delete("/{household_id}/members/{user_id}", response_model=HouseholdWithMembers)
def remove_member_from_household(
    household_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    household = db.query(HouseholdModel).filter(HouseholdModel.id == household_id).first()
    if household is None:
        raise HTTPException(status_code=404, detail="Household not found")
    
    # Check if current user is the creator
    if household.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can remove members")
    
    # Check if user exists
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if member
    if user not in household.members:
        raise HTTPException(status_code=400, detail="User not a member")
    
    household.members.remove(user)
    db.commit()
    db.refresh(household)
    return household
