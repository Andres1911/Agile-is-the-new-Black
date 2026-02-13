# API Usage Examples

> **Note:** Only the Authentication API is currently implemented.
> Household and Expense endpoints will be documented as they are built.

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
  "is_active": true,
  "created_at": "2026-02-12T12:00:00"
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

Response:
```json
{
  "id": 1,
  "email": "john@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2026-02-12T12:00:00"
}
```

## Using with Python

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Register
requests.post(f"{BASE_URL}/auth/register", json={
    "email": "john@example.com",
    "username": "johndoe",
    "password": "securepassword123",
    "full_name": "John Doe",
})

# Login
response = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": "johndoe", "password": "securepassword123"},
)
token = response.json()["access_token"]

# Authenticated request
headers = {"Authorization": f"Bearer {token}"}
me = requests.get(f"{BASE_URL}/auth/me", headers=headers).json()
print(me)
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 400 Bad Request
```json
{
  "detail": "Email already registered"
}
```

## Pagination

For endpoints that support it (coming soon), use query parameters:

```bash
curl -X GET "http://localhost:8000/api/v1/expenses/?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Parameters:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100)
