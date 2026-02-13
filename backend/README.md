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
- **uv** for dependency management & lockfile
- **ruff** for linting & formatting

## Setup

> **Prerequisite:** Install [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

```bash
cd backend

# Create .venv and install everything (runtime + dev) from uv.lock
uv sync --all-extras

# Run the server
uv run python main.py
```

Or with hot reload:
```bash
uv run uvicorn main:app --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
uv run pytest -v
```

## Linting & Formatting

```bash
# Check for issues
uv run ruff check .

# Auto-fix what's fixable
uv run ruff check --fix .

# Format all files
uv run ruff format .
```

## Project Structure

```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   ├── auth.py       # Authentication endpoints
│   │   ├── expenses.py   # Expense management (placeholder)
│   │   └── households.py # Household management (placeholder)
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration settings
│   │   └── security.py   # Security utilities (hashing, JWT)
│   ├── db/               # Database configuration
│   │   └── database.py   # SQLAlchemy setup
│   ├── models/           # Database models
│   │   └── models.py     # User, Household, Expense, ExpenseShare
│   └── schemas/          # Pydantic schemas
│       └── schemas.py    # Request/response schemas
├── main.py               # Application entry point
├── pyproject.toml        # Project config, deps, ruff & pytest settings
├── uv.lock               # Lockfile (committed — reproducible installs)
├── requirements.txt      # Fallback pip requirements
└── test_main.py          # Unit tests
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
