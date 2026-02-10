from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.models import Expense as ExpenseModel, User as UserModel
from app.schemas.schemas import Expense, ExpenseCreate
from app.api.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=Expense, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense_in: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    db_expense = ExpenseModel(
        **expense_in.model_dump(),
        user_id=current_user.id
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


@router.get("/", response_model=List[Expense])
def read_expenses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    expenses = db.query(ExpenseModel).filter(
        ExpenseModel.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return expenses


@router.get("/{expense_id}", response_model=Expense)
def read_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    expense = db.query(ExpenseModel).filter(
        ExpenseModel.id == expense_id,
        ExpenseModel.user_id == current_user.id
    ).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.put("/{expense_id}", response_model=Expense)
def update_expense(
    expense_id: int,
    expense_in: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    expense = db.query(ExpenseModel).filter(
        ExpenseModel.id == expense_id,
        ExpenseModel.user_id == current_user.id
    ).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    for field, value in expense_in.model_dump().items():
        setattr(expense, field, value)
    
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    expense = db.query(ExpenseModel).filter(
        ExpenseModel.id == expense_id,
        ExpenseModel.user_id == current_user.id
    ).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    db.delete(expense)
    db.commit()
    return None


@router.get("/household/{household_id}", response_model=List[Expense])
def read_household_expenses(
    household_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # Verify user is member of household
    household = None
    for h in current_user.households:
        if h.id == household_id:
            household = h
            break
    
    if household is None:
        raise HTTPException(status_code=403, detail="Not a member of this household")
    
    expenses = db.query(ExpenseModel).filter(
        ExpenseModel.household_id == household_id
    ).offset(skip).limit(limit).all()
    return expenses
