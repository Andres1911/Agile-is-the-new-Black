# Expense Tracker Frontend

Flutter mobile application for expense tracking.

## Features

- User registration and login
- Personal expense tracking
- Household management
- Add, view, and delete expenses
- Create and manage households
- Material Design UI
- Cross-platform (iOS, Android, Web)

## Prerequisites

- Flutter SDK (>=3.0.0)
- Dart SDK
- Android Studio / Xcode (for mobile development)
- Running backend server

## Setup

1. Install dependencies:
```bash
flutter pub get
```

2. Configure API endpoint:
   - Edit `lib/services/api_service.dart`
   - Update `baseUrl` to point to your backend server
   - Default: `http://localhost:8000/api/v1`

3. Run the app:
```bash
flutter run
```

For specific platforms:
```bash
flutter run -d chrome        # Web
flutter run -d android       # Android
flutter run -d ios           # iOS
```

## Project Structure

```
frontend/
├── lib/
│   ├── models/              # Data models
│   │   ├── expense.dart     # Expense model
│   │   ├── household.dart   # Household model
│   │   └── user.dart        # User model
│   ├── screens/             # UI screens
│   │   ├── login_screen.dart  # Login & registration
│   │   └── home_screen.dart   # Main app screen
│   ├── services/            # API services
│   │   └── api_service.dart   # HTTP client for backend
│   └── main.dart            # App entry point
└── pubspec.yaml             # Flutter dependencies
```

## Screens

### Login Screen
- User authentication
- Registration form
- Input validation

### Home Screen
- Three tabs: Expenses, Households, Profile
- Bottom navigation
- Floating action buttons for adding items

#### Expenses Tab
- List of user's expenses
- Add new expenses
- Delete expenses
- Shows amount, description, category, and date

#### Households Tab
- List of user's households
- Create new households
- View household members

#### Profile Tab
- User profile information
- Logout functionality

## Dependencies

- `flutter`: Flutter SDK
- `http`: HTTP client for API requests
- `provider`: State management
- `shared_preferences`: Local storage for auth tokens
- `json_annotation`: JSON serialization
- `intl`: Date formatting

## Development

### Hot Reload
Flutter supports hot reload for fast development:
- Press `r` to hot reload
- Press `R` to hot restart
- Press `q` to quit

### Building for Production

Android:
```bash
flutter build apk --release
```

iOS:
```bash
flutter build ios --release
```

Web:
```bash
flutter build web --release
```

## API Integration

The app uses `ApiService` class to communicate with the backend:
- Authentication with JWT tokens
- Automatic token management
- Token stored in shared preferences
- All API calls include authentication headers

## Future Enhancements

- Expense editing
- Search and filter functionality
- Analytics and charts
- Receipt photo uploads
- Push notifications
- Dark mode support
- Offline support with local database
