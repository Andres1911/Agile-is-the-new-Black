# Expense Tracker

ECSE 428 - A household expense tracking application built with FastAPI (Python) backend and Flutter frontend.

## Overview

This expense tracker allows users to:
- Track personal expenses
- Create and manage households
- Share expenses within households
- Categorize expenses
- View expense history

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

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/me` - Get current user

### Expenses
- `POST /api/v1/expenses/` - Create expense
- `GET /api/v1/expenses/` - List user's expenses
- `GET /api/v1/expenses/{id}` - Get expense details
- `PUT /api/v1/expenses/{id}` - Update expense
- `DELETE /api/v1/expenses/{id}` - Delete expense
- `GET /api/v1/expenses/household/{household_id}` - List household expenses

### Households
- `POST /api/v1/households/` - Create household
- `GET /api/v1/households/` - List user's households
- `GET /api/v1/households/{id}` - Get household details
- `POST /api/v1/households/{id}/members/{user_id}` - Add member
- `DELETE /api/v1/households/{id}/members/{user_id}` - Remove member

## Running Tests

### Backend Tests
```bash
cd backend
pytest test_main.py -v
```

## Features

### Current Features
- User registration and authentication
- Personal expense tracking
- Household creation and management
- Multi-user household support
- Expense categorization
- CRUD operations for expenses and households

### Future Enhancements
- Expense splitting between household members
- Budget tracking and alerts
- Expense analytics and reports
- Export data to CSV/PDF
- Recurring expenses
- Receipt photo uploads
- Push notifications
- Search and filter expenses

## Database Schema

### Users Table
- id (Primary Key)
- email (Unique)
- username (Unique)
- hashed_password
- full_name
- created_at

### Households Table
- id (Primary Key)
- name
- description
- created_at
- created_by (Foreign Key to Users)

### Expenses Table
- id (Primary Key)
- amount
- description
- category
- date
- created_at
- user_id (Foreign Key to Users)
- household_id (Foreign Key to Households, Optional)

### Household Members (Association Table)
- user_id (Foreign Key to Users)
- household_id (Foreign Key to Households)

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
