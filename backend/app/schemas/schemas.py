from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

from app.models.models import ExpenseStatus, VoteStatus


# ── User schemas ──────────────────────────────────────────────────────────


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── HouseholdMember schemas ──────────────────────────────────────────────


class HouseholdMemberBase(BaseModel):
    is_admin: bool = False


class HouseholdMemberCreate(HouseholdMemberBase):
    user_id: int
    household_id: int


class HouseholdMember(HouseholdMemberBase):
    user_id: int
    household_id: int
    joined_at: datetime
    left_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HouseholdMemberWithUser(HouseholdMember):
    """Includes the nested User object for richer responses."""
    user: User

    class Config:
        from_attributes = True


# ── Household schemas ────────────────────────────────────────────────────


class HouseholdBase(BaseModel):
    name: str
    description: Optional[str] = None
    address: Optional[str] = None


class HouseholdCreate(HouseholdBase):
    pass


class Household(HouseholdBase):
    id: int
    invite_code: str
    created_at: datetime

    class Config:
        from_attributes = True


class HouseholdWithMembers(Household):
    members: List[HouseholdMemberWithUser] = []

    class Config:
        from_attributes = True


# ── ExpenseShare schemas ─────────────────────────────────────────────────


class ExpenseShareBase(BaseModel):
    user_id: int
    amount_owed: float
    paid_amount: float = 0.0
    is_paid: bool = False
    vote_status: VoteStatus = VoteStatus.PENDING


class ExpenseShareCreate(ExpenseShareBase):
    pass


class ExpenseShare(ExpenseShareBase):
    id: int
    expense_id: int

    class Config:
        from_attributes = True


# ── Expense schemas ──────────────────────────────────────────────────────


class ExpenseBase(BaseModel):
    amount: float
    description: str
    category: Optional[str] = None
    date: Optional[datetime] = None


class ExpenseCreate(ExpenseBase):
    household_id: int
    shares: Optional[List[ExpenseShareCreate]] = None


class Expense(ExpenseBase):
    id: int
    status: ExpenseStatus
    creator_id: int
    household_id: int

    class Config:
        from_attributes = True


class ExpenseWithShares(Expense):
    shares: List[ExpenseShare] = []

    class Config:
        from_attributes = True


# ── Token schemas ────────────────────────────────────────────────────────


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
