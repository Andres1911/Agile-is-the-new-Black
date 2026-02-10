from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base

# Association table for many-to-many relationship between users and households
household_members = Table(
    'household_members',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('household_id', Integer, ForeignKey('households.id'), primary_key=True)
)


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    households = relationship("Household", secondary=household_members, back_populates="members")
    expenses = relationship("Expense", back_populates="user")


class Household(Base):
    __tablename__ = "households"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    members = relationship("User", secondary=household_members, back_populates="households")
    expenses = relationship("Expense", back_populates="household")


class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    household_id = Column(Integer, ForeignKey('households.id'))
    
    # Relationships
    user = relationship("User", back_populates="expenses")
    household = relationship("Household", back_populates="expenses")
