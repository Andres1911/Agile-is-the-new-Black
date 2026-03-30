import enum
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.database import Base

# ---------------------------------------------------------------------------
# Enums (stored as String in the database via Enum(..., native_enum=False))
# ---------------------------------------------------------------------------


class ExpenseStatus(enum.StrEnum):
    PENDING = "PENDING"
    FINALIZED = "FINALIZED"
    DISPUTED = "DISPUTED"
    PARTIALLY_SETTLED = "PARTIALLY_SETTLED"
    FULLY_SETTLED = "FULLY_SETTLED"


class VoteStatus(enum.StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class RecurrenceUnit(enum.StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    household_memberships = relationship("HouseholdMember", back_populates="user")
    created_expenses = relationship("Expense", back_populates="creator")
    expense_shares = relationship("ExpenseShare", back_populates="user")


# ---------------------------------------------------------------------------
# Household
# ---------------------------------------------------------------------------


class Household(Base):
    __tablename__ = "households"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    invite_code = Column(String, unique=True, index=True, nullable=False)
    address = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    members = relationship("HouseholdMember", back_populates="household")
    expenses = relationship("Expense", back_populates="household")


# ---------------------------------------------------------------------------
# HouseholdMember  (Association Class - replaces old M2M table)
# ---------------------------------------------------------------------------


class HouseholdMember(Base):
    __tablename__ = "household_members"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"), primary_key=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.now(UTC))
    left_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="household_memberships")
    household = relationship("Household", back_populates="members")


# ---------------------------------------------------------------------------
# Expense
# ---------------------------------------------------------------------------


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String)
    date = Column(DateTime, default=lambda: datetime.now(UTC))
    status = Column(
        Enum(ExpenseStatus, native_enum=False),
        default=ExpenseStatus.PENDING,
        nullable=False,
    )

    # Foreign keys
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)

    # Relationships
    creator = relationship("User", back_populates="created_expenses")
    household = relationship("Household", back_populates="expenses")
    shares = relationship("ExpenseShare", back_populates="expense")


# ---------------------------------------------------------------------------
# ExpenseShare
# ---------------------------------------------------------------------------


class ExpenseShare(Base):
    __tablename__ = "expense_shares"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_owed = Column(Float, nullable=False, default=0.0)
    paid_amount = Column(Float, nullable=False, default=0.0)
    is_paid = Column(Boolean, default=False, nullable=False)
    vote_status = Column(
        Enum(VoteStatus, native_enum=False),
        default=VoteStatus.PENDING,
        nullable=False,
    )

    # Relationships
    expense = relationship("Expense", back_populates="shares")
    user = relationship("User", back_populates="expense_shares")


# ---------------------------------------------------------------------------
# RecurringExpense
# ---------------------------------------------------------------------------


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"

    id = Column(Integer, primary_key=True, index=True)

    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String)

    split_evenly = Column(Boolean, default=True, nullable=False)
    include_creator = Column(Boolean, default=True, nullable=False)

    interval = Column(Integer, nullable=False, default=1)
    unit = Column(Enum(RecurrenceUnit, native_enum=False), nullable=False)

    start_at = Column(DateTime, nullable=False)
    next_due_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=True)
    max_occurrences = Column(Integer, nullable=True)
    occurrences_generated = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC))

    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)

    creator = relationship("User")
    household = relationship("Household")
    template_shares = relationship(
        "RecurringExpenseShare",
        back_populates="recurring_expense",
        cascade="all, delete-orphan",
    )
    instances = relationship(
        "RecurringExpenseInstance",
        back_populates="recurring_expense",
        cascade="all, delete-orphan",
    )


class RecurringExpenseShare(Base):
    __tablename__ = "recurring_expense_shares"

    id = Column(Integer, primary_key=True, index=True)
    recurring_expense_id = Column(
        Integer, ForeignKey("recurring_expenses.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount_owed = Column(Float, nullable=False, default=0.0)

    recurring_expense = relationship("RecurringExpense", back_populates="template_shares")
    user = relationship("User")


class RecurringExpenseInstance(Base):
    __tablename__ = "recurring_expense_instances"
    __table_args__ = (
        UniqueConstraint("recurring_expense_id", "due_at", name="uq_recurring_due_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    recurring_expense_id = Column(
        Integer, ForeignKey("recurring_expenses.id"), nullable=False, index=True
    )
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False, index=True)
    occurrence_number = Column(Integer, nullable=False)
    due_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    recurring_expense = relationship("RecurringExpense", back_populates="instances")
    expense = relationship("Expense")
