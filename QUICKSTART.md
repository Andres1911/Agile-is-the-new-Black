# Quick Start Guide

Get the Expense Tracker running locally in under 5 minutes.

## Prerequisites

| Tool | Min version | Install |
|------|-------------|---------|
| **uv** | 0.10+ | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Python** | 3.12+ | `uv python install 3.14` (or use your system Python) |
| **Flutter** | latest | [flutter.dev/docs/get-started/install](https://flutter.dev/docs/get-started/install) |
| **Git** | any | — |

> **Why uv?** It creates the virtualenv, resolves dependencies, and writes a
> lockfile (`uv.lock`) so every teammate gets the exact same packages. No more
> "works on my machine."

---

## Backend Setup

```bash
cd backend

# 1 — Create .venv + install ALL deps (runtime + dev) from the lockfile
uv sync --all-extras

# 2 — (optional) Configure secrets
cp .env.example .env        # then edit .env

# 3 — Run the server
uv run python main.py
```

The API is now live:
- **API root:** http://localhost:8000
- **Interactive docs:** http://localhost:8000/docs

### Useful commands

```bash
# Run tests
uv run pytest -v

# Lint
uv run ruff check .

# Auto-format
uv run ruff format .

# Add a new runtime dependency
uv add <package>

# Add a dev-only dependency
uv add --optional dev <package>

# Re-lock after editing pyproject.toml manually
uv lock
```

> `uv run` automatically uses the project's `.venv` — no need to `source
> .venv/bin/activate` (though you still can if you prefer).

---

## Frontend Setup

```bash
cd frontend

# 1 — Install Flutter packages
flutter pub get

# 2 — Update API URL if needed
#     Edit lib/services/api_service.dart → baseUrl

# 3 — Run
flutter run              # default device
flutter run -d chrome    # web
flutter run -d android   # Android emulator
flutter run -d ios       # iOS simulator
```

---

## Testing

### Backend

```bash
cd backend
uv run pytest -v
```

### Manual API Testing

1. Open http://localhost:8000/docs
2. **Register** a new user
3. **Login** to get a JWT token
4. Click **Authorize** and paste the token
5. Try the available endpoints

---

## Troubleshooting

### "Port already in use"
```bash
lsof -ti:8000 | xargs kill -9
```

### "Database locked" (SQLite)
```bash
cd backend && rm -f expense_tracker.db && uv run python main.py
```

### Dependency mismatch between teammates
```bash
cd backend
uv lock          # regenerate the lockfile
uv sync --all-extras   # reinstall everything
```

### Frontend can't reach the backend
- Make sure the backend is running on http://localhost:8000
- Android emulator: use `http://10.0.2.2:8000` instead of `localhost`
- iOS simulator: `localhost` usually works; otherwise use your machine's IP

---

## Project Tooling at a Glance

| Concern | Tool | Config lives in |
|---------|------|-----------------|
| Dependency management | **uv** | `pyproject.toml` + `uv.lock` |
| Linting | **ruff** | `[tool.ruff]` in `pyproject.toml` |
| Formatting | **ruff format** | `[tool.ruff.format]` in `pyproject.toml` |
| Testing | **pytest** | `[tool.pytest.ini_options]` in `pyproject.toml` |

---

## Next Steps

- Browse the full [README.md](README.md)
- Explore API docs at `/docs`
- Check [backend/README.md](backend/README.md) for architecture details
- Customise settings in `.env`
