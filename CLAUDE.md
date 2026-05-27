# CLAUDE.md

## Project Overview

Diet Health App — AI-powered nutrition and meal planning SPA.

- **Backend**: FastAPI (async) + SQLAlchemy + SQLite (`backend/`)
- **Frontend**: Vanilla JS SPA, single `index.html` + `admin.html` (`frontend/`)
- **AI**: Qwen/DeepSeek API for meal generation and questionnaire analysis
- **Auth**: JWT (HS256), user login by nickname → openid

## Project Structure

```
backend/
  app/
    main.py              # FastAPI app, lifespan, routes, static mount
    core/
      config.py          # Settings from .env (DATABASE_URL, JWT_SECRET, QWEN_API_KEY)
      database.py        # async engine, session, Base, get_db, init_db (+safe migrations)
      security.py        # JWT create/verify, get_current_user dependency
    models/              # SQLAlchemy ORM models (User, MealPlan, DailyMeal, Ingredient, etc.)
    schemas/__init__.py  # All Pydantic schemas in one file
    api/v1/
      user.py            # login, profile, preferences, questionnaire, location
      meal.py            # meal plan CRUD, generate, swap, shopping list, orders
      health.py          # health records, monthly report
      ingredient.py      # ingredient CRUD
      admin.py           # admin dashboard (supermarket, delivery, users)
    services/
      ai_service.py      # DeepSeek/Qwen API calls, prompt builders
      nutrition.py       # Calorie/macro calculations
frontend/
  index.html             # Main SPA (login, goal, home, health, shopping, mine)
  admin.html             # Admin dashboard (standalone page)
```

## Stack & Conventions

- **Python 3.12+**, all async endpoints (`async def`)
- **SQLite** via `aiosqlite`, connection string in `.env`
- **Encoding**: UTF-8. The codebase had GB18030 double-encoding corruption — always use UTF-8 when editing Chinese text
- **Pydantic v2**: `model_config = {"from_attributes": True}` for ORM mode
- **JWT**: Tokens store `{"sub": str(user.id)}`, 720h expiry
- **Frontend auth**: Token in `localStorage.token`, sent as `Authorization: Bearer <token>` header
- **openid format**: `user_<nickname>` (new) or `user_<nickname>_<timestamp>` (old, backward compat)

## Running the App

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend served at `http://localhost:8000/`, admin at `http://localhost:8000/admin`.

## Key Patterns

- **Login backward compat**: If exact openid match fails, try `LIKE 'user_<name>_%'` to find old-format users, migrate their openid to new format
- **Safe migrations**: Column additions wrapped in try/except in `init_db()` — avoids errors on re-run
- **AI calls**: `call_deepseek(prompt, task_name, max_tokens)` with JSON extraction via `extract_json()`
- **Admin check**: Frontend checks `currentUser.is_admin === 1`, backend routes check user.is_admin
- **Order locking**: Confirmed orders within 2 days of delivery date are locked (read-only in UI)

## Files to Never Commit

- `_fix_all.py` (temporary encoding fix script)
- `*.db` (database files)
- `.env` (secrets)
