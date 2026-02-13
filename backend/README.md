# Expense Tracker Backend

FastAPI-based REST API for the expense tracker application.

## Features

- JWT-based authentication (register / login / me)
- Domain model with association-class pattern (HouseholdMember)
- Expense splitting via ExpenseShare
- Voting logic (VoteStatus) on shares
- Invite-code based household joining
- SQLite database (easily switchable to PostgreSQL/MySQL)
- Automatic OpenAPI documentation

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python main.py
```

Or using uvicorn:
```bash
uvicorn main:app --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

Run tests with pytest:
```bash
pytest test_main.py -v
```

## Project Structure

```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   ├── auth.py       # Authentication endpoints
│   │   ├── expenses.py   # Expense management endpoints
│   │   └── households.py # Household management endpoints
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration settings
│   │   └── security.py   # Security utilities (hashing, JWT)
│   ├── db/               # Database configuration
│   │   └── database.py   # SQLAlchemy setup
│   ├── models/           # Database models
│   │   └── models.py     # User, Household, Expense models
│   └── schemas/          # Pydantic schemas
│       └── schemas.py    # Request/response schemas
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── test_main.py         # Unit tests
```

## Environment Variables

Create a `.env` file in the backend directory:

```env
DATABASE_URL=sqlite:///./expense_tracker.db
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Database Models

### User
- id, username, email, password_hash, full_name, is_active, created_at

### Household
- id, name, description, invite_code (unique), address, created_at

### HouseholdMember (Association Class)
- user_id, household_id, is_admin, joined_at, left_at

### Expense
- id, amount, description, category, date, status (PENDING/FINALIZED/DISPUTED)
- creator_id (FK → Users), household_id (FK → Households)

### ExpenseShare
- id, expense_id, user_id, amount_owed, paid_amount, is_paid, vote_status (PENDING/ACCEPTED/REJECTED)

## API Endpoints Summary

### Authentication (implemented)
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user info

### Expenses (coming soon)
_Will include create/read/update/delete with splitting & voting._

### Households (coming soon)
_Will include CRUD, invite-code join, and admin role management._
