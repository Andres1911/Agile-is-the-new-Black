# API Usage Examples

This document provides practical examples of how to use the Expense Tracker API.

## Authentication

### Register a New User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "username": "johndoe",
    "password": "securepassword123",
    "full_name": "John Doe"
  }'
```

Response:
```json
{
  "id": 1,
  "email": "john@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "created_at": "2024-01-01T12:00:00"
}
```

### Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=johndoe&password=securepassword123"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Save the `access_token` for subsequent requests.

### Get Current User

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Managing Expenses

### Create an Expense

```bash
curl -X POST "http://localhost:8000/api/v1/expenses/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 45.99,
    "description": "Grocery shopping",
    "category": "Food",
    "date": "2024-01-01T10:30:00"
  }'
```

### List All Expenses

```bash
curl -X GET "http://localhost:8000/api/v1/expenses/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get Single Expense

```bash
curl -X GET "http://localhost:8000/api/v1/expenses/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update an Expense

```bash
curl -X PUT "http://localhost:8000/api/v1/expenses/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 50.00,
    "description": "Grocery shopping (updated)",
    "category": "Food"
  }'
```

### Delete an Expense

```bash
curl -X DELETE "http://localhost:8000/api/v1/expenses/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Managing Households

### Create a Household

```bash
curl -X POST "http://localhost:8000/api/v1/households/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Family Home",
    "description": "Shared expenses for our family"
  }'
```

### List All Households

```bash
curl -X GET "http://localhost:8000/api/v1/households/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Get Household Details

```bash
curl -X GET "http://localhost:8000/api/v1/households/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response includes members:
```json
{
  "id": 1,
  "name": "Family Home",
  "description": "Shared expenses for our family",
  "created_at": "2024-01-01T12:00:00",
  "created_by": 1,
  "members": [
    {
      "id": 1,
      "email": "john@example.com",
      "username": "johndoe",
      "full_name": "John Doe",
      "created_at": "2024-01-01T12:00:00"
    }
  ]
}
```

### Add Member to Household

```bash
curl -X POST "http://localhost:8000/api/v1/households/1/members/2" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Remove Member from Household

```bash
curl -X DELETE "http://localhost:8000/api/v1/households/1/members/2" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Household Expenses

### Create a Household Expense

```bash
curl -X POST "http://localhost:8000/api/v1/expenses/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 150.00,
    "description": "Monthly rent",
    "category": "Housing",
    "household_id": 1
  }'
```

### List Household Expenses

```bash
curl -X GET "http://localhost:8000/api/v1/expenses/household/1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Using with Python

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Login
response = requests.post(
    f"{BASE_URL}/auth/login",
    data={
        "username": "johndoe",
        "password": "securepassword123"
    }
)
token = response.json()["access_token"]

# Headers for authenticated requests
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Create an expense
expense_data = {
    "amount": 25.50,
    "description": "Coffee",
    "category": "Food"
}
response = requests.post(
    f"{BASE_URL}/expenses/",
    json=expense_data,
    headers=headers
)
print(response.json())

# Get all expenses
response = requests.get(
    f"{BASE_URL}/expenses/",
    headers=headers
)
expenses = response.json()
print(f"Total expenses: {len(expenses)}")
```

## Using with JavaScript/Flutter

```javascript
const BASE_URL = "http://localhost:8000/api/v1";
let token = "";

// Login
async function login(username, password) {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData
  });
  
  const data = await response.json();
  token = data.access_token;
  return token;
}

// Create expense
async function createExpense(amount, description, category) {
  const response = await fetch(`${BASE_URL}/expenses/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      amount,
      description,
      category
    })
  });
  
  return await response.json();
}

// Usage
await login('johndoe', 'securepassword123');
const expense = await createExpense(25.50, 'Coffee', 'Food');
console.log(expense);
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 404 Not Found
```json
{
  "detail": "Expense not found"
}
```

### 400 Bad Request
```json
{
  "detail": "Email already registered"
}
```

## Rate Limiting

Currently, there are no rate limits. In production, consider implementing rate limiting using:
- FastAPI middleware
- Redis-based rate limiting
- API Gateway rate limits

## Pagination

For large datasets, use query parameters:

```bash
curl -X GET "http://localhost:8000/api/v1/expenses/?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Parameters:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100)
