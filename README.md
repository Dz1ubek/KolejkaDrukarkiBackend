# FastAPI REST API Boilerplate

A modern, clean, and modular boilerplate for building REST APIs with FastAPI, Pydantic v2, SQLAlchemy (SQLite), and Uvicorn on Windows 11 / Python 3.13.

---

## 📁 Project Structure

```text
KolejkaDrukarkiBackend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application factory and entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic Settings & environment variables
│   │   └── security.py             # Password hashing (bcrypt) & JWT (pyjwt) utilities
│   ├── db/
│   │   ├── __init__.py
│   │   └── session.py              # SQLite engine, SessionLocal, get_db, init_db
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py                 # SQLAlchemy User model & UserRole enum
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── item.py                 # Item Pydantic schemas
│   │   └── user.py                 # User & Token Pydantic schemas
│   └── api/
│       ├── __init__.py
│       ├── deps.py                 # get_db, get_current_user, get_current_active_admin
│       └── v1/
│           ├── __init__.py
│           ├── router.py           # V1 API router aggregation
│           └── endpoints/
│               ├── __init__.py
│               ├── health.py       # Health check endpoint (/api/v1/health)
│               └── items.py        # Example CRUD endpoints (/api/v1/items)
├── tests/
│   ├── __init__.py
│   ├── test_api.py                 # API endpoints test suite
│   └── test_db_and_security.py     # SQLite, User model, bcrypt & JWT test suite
├── .env                            # Active environment configuration
├── .env.example                    # Template environment file
├── .gitignore
├── requirements.txt                # Python dependencies
└── README.md
```

---

## 🚀 Quick Start

### 1. Activate the Virtual Environment

In PowerShell on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

*(If you encounter execution policy restrictions, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once)*

Or in Command Prompt (`cmd`):

```cmd
.\.venv\Scripts\activate.bat
```

### 2. Start the Development Server

Run with Uvicorn auto-reload enabled:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Alternatively, run directly via Python:

```powershell
python -m app.main
```

The SQLite database (`kolejka.db`) and tables are initialized automatically on startup.

The server will start at:
- **API Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Tests

Execute all unit tests with `pytest`:

```powershell
pytest
```

---

## ⚙️ Configuration & Security

Environment variables are loaded from `.env` using `pydantic-settings`:

- `PROJECT_NAME`: Name displayed in Swagger docs
- `ENVIRONMENT`: `development` | `production`
- `DEBUG`: Boolean flag (`True` / `False`)
- `HOST`: Server host IP (default: `127.0.0.1`)
- `PORT`: Server port (default: `8000`)
- `DATABASE_URL`: Database connection string (`sqlite:///./kolejka.db`)
- `SECRET_KEY`: JWT secret key
- `ALGORITHM`: Token signing algorithm (`HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Expiration time for access tokens
- `CORS_ORIGINS`: JSON list of permitted origins
