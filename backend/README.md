# Expense Tracker Backend

FastAPI-based REST API for the expense tracker application.

## Features

- JWT-based authentication
- User registration and login
- Personal expense management (CRUD operations)
- Household management
- Multi-user household support
- RESTful API design
- Automatic API documentation
- SQLite database (easily switchable to PostgreSQL/MySQL)

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
- id, email, username, hashed_password, full_name, created_at

### Household
- id, name, description, created_at, created_by
- Many-to-many relationship with Users

### Expense
- id, amount, description, category, date, created_at
- Belongs to a User
- Optionally belongs to a Household

## API Endpoints Summary

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get token
- `GET /api/v1/auth/me` - Get current user info

### Expenses
- `GET /api/v1/expenses/` - List expenses
- `POST /api/v1/expenses/` - Create expense
- `GET /api/v1/expenses/{id}` - Get expense
- `PUT /api/v1/expenses/{id}` - Update expense
- `DELETE /api/v1/expenses/{id}` - Delete expense
- `GET /api/v1/expenses/household/{household_id}` - List household expenses

### Households
- `GET /api/v1/households/` - List households
- `POST /api/v1/households/` - Create household
- `GET /api/v1/households/{id}` - Get household
- `POST /api/v1/households/{id}/members/{user_id}` - Add member
- `DELETE /api/v1/households/{id}/members/{user_id}` - Remove member
