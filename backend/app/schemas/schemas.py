from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Household schemas
class HouseholdBase(BaseModel):
    name: str
    description: Optional[str] = None


class HouseholdCreate(HouseholdBase):
    pass


class Household(HouseholdBase):
    id: int
    created_at: datetime
    created_by: int
    
    class Config:
        from_attributes = True


class HouseholdWithMembers(Household):
    members: List[User] = []
    
    class Config:
        from_attributes = True


# Expense schemas
class ExpenseBase(BaseModel):
    amount: float
    description: str
    category: Optional[str] = None
    date: Optional[datetime] = None


class ExpenseCreate(ExpenseBase):
    household_id: Optional[int] = None


class Expense(ExpenseBase):
    id: int
    created_at: datetime
    user_id: int
    household_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
