# Quick Start Guide

This guide helps you quickly set up and run the Expense Tracker application.

## Prerequisites

- Python 3.8+ installed
- Flutter SDK installed (for mobile app)
- Git

## Backend Setup (5 minutes)

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment (optional):**
   ```bash
   cp .env.example .env
   # Edit .env and change SECRET_KEY and other settings
   ```

5. **Run the server:**
   ```bash
   python main.py
   ```

   The API will be available at:
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Frontend Setup (5 minutes)

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Get Flutter dependencies:**
   ```bash
   flutter pub get
   ```

3. **Update API URL (if needed):**
   - Open `lib/services/api_service.dart`
   - Change `baseUrl` if your backend is not at `http://localhost:8000`

4. **Run the app:**
   ```bash
   flutter run
   ```

   Or for specific platform:
   ```bash
   flutter run -d chrome    # Web
   flutter run -d android   # Android
   flutter run -d ios       # iOS
   ```

## Testing the Application

### Test the Backend API

```bash
cd backend
source venv/bin/activate
pytest test_main.py -v
```

### Manual API Testing

1. Open http://localhost:8000/docs
2. Try the endpoints:
   - Register a new user
   - Login to get a token
   - Use "Authorize" button to add your token
   - Create expenses and households

### Test the Mobile App

1. Run the Flutter app
2. Register a new account
3. Add expenses
4. Create a household
5. View your data

## Quick Feature Demo

1. **User Registration:**
   - Open the app
   - Click "Don't have an account? Register"
   - Fill in the form and register

2. **Add an Expense:**
   - After logging in, you'll see the Expenses tab
   - Click the + button
   - Enter amount, description, category
   - Click "Add"

3. **Create a Household:**
   - Go to Households tab
   - Click the + button
   - Enter name and description
   - Click "Add"

4. **Add Household Expense:**
   - In Expenses tab, click + button
   - Fill in expense details
   - Select a household from dropdown
   - Click "Add"

## Troubleshooting

### Backend Issues

**Port already in use:**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

**Database locked:**
```bash
# Remove database and restart
rm expense_tracker.db
python main.py
```

### Frontend Issues

**Dependencies issue:**
```bash
flutter clean
flutter pub get
```

**Cannot connect to backend:**
- Ensure backend is running on http://localhost:8000
- Check `lib/services/api_service.dart` has correct URL
- For mobile emulator, use `http://10.0.2.2:8000` (Android) or your machine's IP

## Next Steps

- Read the full README.md for detailed documentation
- Explore the API documentation at /docs
- Check backend/README.md for API details
- Check frontend/README.md for Flutter app details
- Customize the configuration in .env file

## Common Tasks

**Add a new expense category:**
- Just type it when creating an expense

**Share household with another user:**
- Currently requires user ID (future: search by email)
- Use POST /api/v1/households/{id}/members/{user_id}

**Export data:**
- Use the API to get JSON data (future: CSV export)

## Support

For issues or questions:
1. Check the documentation
2. Review the API docs at /docs
3. Check the GitHub issues
