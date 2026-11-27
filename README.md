# Household Expense Tracker

A team project for ECSE 428 that helps household members split shared expenses, review their shares, and track outstanding payments. Built with a FastAPI backend and a Flutter frontend.

## Project highlights

- JWT registration and login.
- Household creation, invite-code joining, member lists, and expense history.
- Equal or manual expense splitting, share acceptance or rejection, dispute resolution, and payment confirmation.
- Recurring-expense definitions and generation of due charges.
- Receipt-image parsing with OCR.
- Backend unit tests and Gherkin acceptance scenarios.

These features are represented in the source; this is a course application, not a production financial service. Payment confirmation records a share as paid rather than processing a bank transaction.

## Architecture

| Layer | Technologies | Entry points |
| --- | --- | --- |
| Interface | Flutter, Dart, Provider | [Screens](frontend/lib/screens), [API client](frontend/lib/services/api_service.dart) |
| HTTP API | Python 3.12+, FastAPI, Pydantic | [Application](backend/main.py), [routes](backend/app/api) |
| Persistence | SQLAlchemy, SQLite by default | [Models](backend/app/models/models.py), [database](backend/app/db/database.py) |
| Services | Recurrence calculations, Pillow, pytesseract | [Services](backend/app/services) |
| Verification | pytest, pytest-bdd, Ruff | [Tests](backend/tests), [CI](.github/workflows/ci.yml) |

The backend registers authentication, user, household, and expense routers under `/api/v1`. SQLite tables and lightweight schema migrations are initialized at application startup.

## Run the backend

Install Python 3.12+ and uv. From the repository root:

```bash
cd backend
uv sync --all-extras
cp .env.example .env
```

In PowerShell, use `Copy-Item .env.example .env`. Set a fresh local `SECRET_KEY` in `.env` before use; the checked-in default is a placeholder. Keep `.env` out of Git.

```bash
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open [interactive API documentation](http://localhost:8000/docs) to inspect request schemas and try endpoints. The health endpoint is [localhost:8000/health](http://localhost:8000/health).

Receipt OCR also requires the Tesseract executable on your system path. HEIC/HEIF decoding additionally needs the optional `pillow-heif` package; it is not declared in the current project dependencies.

## Run the frontend

The repository contains Flutter source and `pubspec.yaml`, but no generated platform runner directories. With a compatible Flutter SDK installed, generate the runner for your intended platform locally:

```bash
cd frontend
flutter create --platforms=android .
flutter pub get
```

Review the generated files before committing them. Configure `baseUrl` in [the API client](frontend/lib/services/api_service.dart) for the device you are using. Its default is `http://localhost:8000/api/v1`; a physical device needs a reachable backend address.

```bash
flutter devices
flutter run -d <device-id>
```

Platform setup and frontend/backend integration still require validation. The client imports `dart:io`, so browser support should not be assumed.

## Explore the implementation

| Workflow | Code |
| --- | --- |
| Authentication | [auth.py](backend/app/api/auth.py) |
| Household membership and debt simplification | [households.py](backend/app/api/households.py) |
| Splitting, voting, payment confirmation, and receipt scanning | [expenses.py](backend/app/api/expenses.py) |
| Recurrence scheduling and charge generation | [recurring_expenses.py](backend/app/services/recurring_expenses.py) |
| Receipt text and amount extraction | [receipt_parser.py](backend/app/services/receipt_parser.py) |

Use the generated API documentation as the endpoint reference. Some frontend helper methods target routes that differ from the backend, including the leave-household flow; inspect both sides when extending a feature.

## Tests and quality checks

From `backend/`:

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```

Acceptance scenarios are in [tests/acceptance/features](backend/tests/acceptance/features); unit tests are in [tests/unit](backend/tests/unit). GitHub Actions configures linting, formatting, and tests on pushes and pull requests to `main`. The workflow runs tests only after preceding checks succeed; the presence of CI is not a claim that the latest run passes.

## Scope and credits

This is a collaborative ECSE 428 project. Repository ownership does not imply sole authorship; the [commit history](https://github.com/Andres1911/Agile-is-the-new-Black/commits/main/) records contributions.

Use synthetic household and receipt data for demonstrations. No deployment hardening or cross-platform verification is claimed. Recurring charges are generated through application/API logic; no background scheduler is configured in the inspected application entry point.

The repository does not currently include a standalone license. Course context does not itself grant redistribution rights.

