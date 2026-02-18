from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.models import ExpenseStatus, VoteStatus

from typing import List, Optional

# ── User schemas ──────────────────────────────────────────────────────────


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str | None = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime


class PublicUser(BaseModel):
    """Public user schema for displaying user info to other household members.

    Only includes non-sensitive fields: id, username, and full_name.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str | None = None


# ── HouseholdMember schemas ──────────────────────────────────────────────


class HouseholdMemberBase(BaseModel):
    is_admin: bool = False


class HouseholdMemberCreate(HouseholdMemberBase):
    user_id: int
    household_id: int


class HouseholdMember(HouseholdMemberBase):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    household_id: int
    joined_at: datetime
    left_at: datetime | None = None


class HouseholdMemberWithUser(HouseholdMember):
    """Includes the nested User object for richer responses."""

    user: PublicUser


# ── Household schemas ────────────────────────────────────────────────────


class HouseholdBase(BaseModel):
    name: str
    description: str | None = None
    address: str | None = None


class HouseholdCreate(HouseholdBase):
    pass


class Household(HouseholdBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invite_code: str
    created_at: datetime


class HouseholdWithMembers(Household):
    members: list[HouseholdMemberWithUser] = []


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    expense_id: int


# ── Expense schemas ──────────────────────────────────────────────────────


class ExpenseBase(BaseModel):
    amount: float
    description: str
    category: str | None = None
    date: datetime | None = None


class ExpenseCreate(ExpenseBase):
    household_id: int
    shares: list[ExpenseShareCreate] | None = None


class Expense(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ExpenseStatus
    creator_id: int
    household_id: int


class ExpenseWithShares(Expense):
    shares: list[ExpenseShare] = []

class ManualShare(BaseModel):
    user_id: int
    amount: float

class ExpenseCreate(BaseModel):
    description: str
    amount: float
    category: str | None = None
    split_evenly: bool
    include_creator: bool
    manual_shares: Optional[List[ManualShare]] = None


# ── Token schemas ────────────────────────────────────────────────────────


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
