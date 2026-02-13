# Expense Tracker

ECSE 428 - A household expense tracking application built with FastAPI (Python) backend and Flutter frontend.

## Overview

This expense tracker allows users to:
- Register and authenticate (JWT)
- Create and manage households (with invite codes)
- Track shared expenses with splits & voting
- Categorize expenses
- View expense history

> **Status:** The domain model (SQLAlchemy models + Pydantic schemas) is fully implemented.
> Only the **Auth API** is wired up so far — Household, Expense and ExpenseShare endpoints will be added incrementally.

## Technology Stack

### Backend
- **Python 3.x** - Programming language
- **FastAPI** - Modern web framework for building APIs
- **SQLAlchemy** - SQL toolkit and ORM
- **SQLite** - Database (can be switched to PostgreSQL/MySQL)
- **JWT** - Authentication
- **Pydantic** - Data validation

### Frontend
- **Flutter** - Cross-platform mobile framework
- **Dart** - Programming language
- **Provider** - State management
- **HTTP** - API client

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # API route handlers
│   │   │   ├── auth.py
│   │   │   ├── expenses.py
│   │   │   └── households.py
│   │   ├── core/         # Core functionality
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── db/           # Database configuration
│   │   │   └── database.py
│   │   ├── models/       # SQLAlchemy models
│   │   │   └── models.py
│   │   └── schemas/      # Pydantic schemas
│   │       └── schemas.py
│   ├── main.py           # FastAPI application entry point
│   ├── requirements.txt  # Python dependencies
│   └── test_main.py      # Backend tests
│
└── frontend/
    ├── lib/
    │   ├── models/       # Data models
    │   │   ├── expense.dart
    │   │   ├── household.dart
    │   │   └── user.dart
    │   ├── screens/      # UI screens
    │   │   ├── login_screen.dart
    │   │   └── home_screen.dart
    │   ├── services/     # API services
    │   │   └── api_service.dart
    │   └── main.dart     # Flutter app entry point
    └── pubspec.yaml      # Flutter dependencies
```

## Setup Instructions

### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server**
   ```bash
   python main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --reload
   ```

5. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install Flutter dependencies**
   ```bash
   flutter pub get
   ```

3. **Update API URL**
   - Edit `lib/services/api_service.dart`
   - Change `baseUrl` to your backend URL (default: `http://localhost:8000/api/v1`)

4. **Run the app**
   ```bash
   flutter run
   ```

   For specific platform:
   ```bash
   flutter run -d chrome        # Web
   flutter run -d android       # Android
   flutter run -d ios           # iOS
   ```

## API Endpoints

### Authentication (implemented)
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user (returns JWT)
- `GET /api/v1/auth/me` - Get current user

### Expenses (coming soon)
_Endpoints will be added with splitting, voting & status logic._

### Households (coming soon)
_Endpoints will be added with invite-code join, admin roles, etc._

## Running Tests

### Backend Tests
```bash
cd backend
pytest test_main.py -v
```

## Features

### Implemented
- User registration and JWT authentication
- Domain model with full association-class pattern
  - `User`, `Household`, `HouseholdMember` (admin flag, join/leave timestamps)
  - `Expense` with `ExpenseStatus` (PENDING / FINALIZED / DISPUTED)
  - `ExpenseShare` with `VoteStatus` (PENDING / ACCEPTED / REJECTED) + `is_paid`
- Unique invite codes on Households
- Pydantic v2 schemas for all models

### Coming Next
- Household CRUD with invite-code join flow
- Expense CRUD with automatic share splitting
- Voting / agreement workflow on shares
- Settlement tracking (mark shares as paid)

### Future Enhancements
- Budget tracking and alerts
- Expense analytics and reports
- Export data to CSV/PDF
- Recurring expenses
- Receipt photo uploads
- Push notifications
- Search and filter expenses

## Database Schema

### Users
| Column | Type | Notes |
|---|---|---|
| id | Integer | PK |
| username | String | Unique |
| email | String | Unique |
| password_hash | String | bcrypt |
| full_name | String | |
| is_active | Boolean | default True |
| created_at | DateTime | UTC |

### Households
| Column | Type | Notes |
|---|---|---|
| id | Integer | PK |
| name | String | |
| description | String | |
| invite_code | String | Unique |
| address | String | |
| created_at | DateTime | UTC |

### HouseholdMembers (Association Class)
| Column | Type | Notes |
|---|---|---|
| user_id | Integer | PK, FK → Users |
| household_id | Integer | PK, FK → Households |
| is_admin | Boolean | default False |
| joined_at | DateTime | UTC |
| left_at | DateTime | nullable |

### Expenses
| Column | Type | Notes |
|---|---|---|
| id | Integer | PK |
| amount | Float | |
| description | String | |
| category | String | |
| date | DateTime | UTC |
| status | ExpenseStatus | PENDING / FINALIZED / DISPUTED |
| creator_id | Integer | FK → Users |
| household_id | Integer | FK → Households |

### ExpenseShares
| Column | Type | Notes |
|---|---|---|
| id | Integer | PK |
| expense_id | Integer | FK → Expenses |
| user_id | Integer | FK → Users |
| amount_owed | Float | |
| paid_amount | Float | |
| is_paid | Boolean | Settlement flag |
| vote_status | VoteStatus | PENDING / ACCEPTED / REJECTED |

## Development

### Backend Development
- FastAPI provides automatic API documentation at `/docs`
- Use `uvicorn main:app --reload` for hot reloading during development
- Follow PEP 8 style guidelines for Python code

### Frontend Development
- Use `flutter run` with hot reload enabled
- Follow Dart style guidelines
- Test on multiple devices/emulators

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is created for ECSE 428 course.
