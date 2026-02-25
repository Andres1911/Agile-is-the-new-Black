import tempfile
from pathlib import Path
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base, get_db
from main import app
from app.models.models import User, Household, HouseholdMember, Expense, ExpenseShare, ExpenseStatus, VoteStatus
from app.core.security import get_password_hash, create_access_token

# Setup test DB
test_db_path = Path(tempfile.gettempdir()) / "test_cycle_debug.db"
url = f"sqlite:///{test_db_path}"
engine = create_engine(url, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create tables and client
Base.metadata.create_all(bind=engine)
client = TestClient(app)

# Create test data
db = TestingSessionLocal()

# Create users
alice = User(username="Alice", email="alice@test.com", password_hash=get_password_hash("pass"), full_name="Alice")
bob = User(username="Bob", email="bob@test.com", password_hash=get_password_hash("pass"), full_name="Bob")
cara = User(username="Cara", email="cara@test.com", password_hash=get_password_hash("pass"), full_name="Cara")
db.add_all([alice, bob, cara])
db.flush()

# Create household
house = Household(name="TestHouse", invite_code="TEST123")
db.add(house)
db.flush()

# Add members
db.add(HouseholdMember(user_id=alice.id, household_id=house.id))
db.add(HouseholdMember(user_id=bob.id, household_id=house.id))
db.add(HouseholdMember(user_id=cara.id, household_id=house.id))
db.flush()

# Create circular debts with ACCEPTED status
# Bob owes Alice 10
exp1 = Expense(household_id=house.id, creator_id=alice.id, amount=10, description="test", status=ExpenseStatus.PENDING)
db.add(exp1)
db.flush()
share1 = ExpenseShare(expense_id=exp1.id, user_id=bob.id, amount_owed=10, paid_amount=0, is_paid=False, vote_status=VoteStatus.ACCEPTED)
db.add(share1)

# Alice owes Cara 10
exp2 = Expense(household_id=house.id, creator_id=cara.id, amount=10, description="test", status=ExpenseStatus.PENDING)
db.add(exp2)
db.flush()
share2 = ExpenseShare(expense_id=exp2.id, user_id=alice.id, amount_owed=10, paid_amount=0, is_paid=False, vote_status=VoteStatus.ACCEPTED)
db.add(share2)

# Cara owes Bob 10
exp3 = Expense(household_id=house.id, creator_id=bob.id, amount=10, description="test", status=ExpenseStatus.PENDING)
db.add(exp3)
db.flush()
share3 = ExpenseShare(expense_id=exp3.id, user_id=cara.id, amount_owed=10, paid_amount=0, is_paid=False, vote_status=VoteStatus.ACCEPTED)
db.add(share3)

db.commit()

print("BEFORE simplification:")
shares = db.query(ExpenseShare).all()
for share in shares:
    exp = db.query(Expense).filter(Expense.id == share.expense_id).first()
    print(f"  Share {share.id}: user={share.user_id}, creator={exp.creator_id}, is_paid={share.is_paid}")

# Make the request
token = create_access_token(data={"sub": "Alice"})
resp = client.post(
    "/api/v1/households/TestHouse/debts/simplify",
    headers={"Authorization": f"Bearer {token}"},
)

print("\nResponse status:", resp.status_code)
body = resp.json()
print("debts_fully_simplified_count:", body.get("debts_fully_simplified_count"))

print("\nAFTER simplification:")
# Need to refresh the session to see changes
db.expunge_all()
shares = db.query(ExpenseShare).all()
for share in shares:
    exp = db.query(Expense).filter(Expense.id == share.expense_id).first()
    print(f"  Share {share.id}: user={share.user_id}, creator={exp.creator_id}, is_paid={share.is_paid}")

db.close()
