# Kolejka Drukarki 3D API

A modern, clean, and modular REST API backend for a 3D printer queue service with automated pricing, Stripe compatibility, and role-based access control. Built with FastAPI, Pydantic v2, SQLAlchemy 2.0 (SQLite), and Uvicorn on Windows 11 / Python 3.13.

---

## 📁 Project Structure

```text
KolejkaDrukarkiBackend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application factory and lifespan setup
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic Settings & environment variables
│   │   ├── pricing.py              # Server-side pricing formula calculation
│   │   └── security.py             # Password hashing (bcrypt) & JWT (pyjwt) utilities
│   ├── db/
│   │   ├── __init__.py
│   │   └── session.py              # SQLite engine, SessionLocal, get_db, init_db, first admin seed
│   ├── models/
│   │   ├── __init__.py
│   │   ├── print_job.py            # SQLAlchemy 2.0 PrintJob model, PrintStatus, PaymentStatus
│   │   └── user.py                 # SQLAlchemy 2.0 User model & UserRole enum
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Registration schema
│   │   ├── item.py                 # Item Pydantic schemas
│   │   ├── print_job.py            # Print job schemas (Response, Pagination, AdminUpdate, Estimate)
│   │   └── user.py                 # User, Token & Admin Pydantic schemas
│   └── api/
│       ├── __init__.py
│       ├── deps.py                 # get_db, get_current_user, get_current_active_admin
│       └── v1/
│           ├── __init__.py
│           ├── router.py           # V1 API router aggregation
│           └── endpoints/
│               ├── __init__.py
│               ├── admin.py        # Admin user management endpoints (/api/v1/admin/users)
│               ├── admin_prints.py # Admin print queue endpoints (/api/v1/admin/prints)
│               ├── auth.py         # Registration and login (/api/v1/auth)
│               ├── health.py       # Health check endpoint (/api/v1/health)
│               ├── items.py        # Example CRUD endpoints (/api/v1/items)
│               ├── prints.py       # User print order & file upload endpoints (/api/v1/prints)
│               └── users.py        # Authenticated user endpoints (/api/v1/users)
├── tests/
│   ├── __init__.py
│   ├── test_admin.py               # Admin endpoints & RBAC test suite
│   ├── test_api.py                 # Basic API endpoints test suite
│   ├── test_db_and_security.py     # SQLite, User model, bcrypt & JWT test suite
│   ├── test_prints.py              # Print orders, file upload, pricing & queue tests
│   └── test_user_endpoints.py      # Registration, login, and profile tests
├── uploads/                        # Dedicated directory for uploaded 3D models (gitignored)
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

The SQLite database (`kolejka.db`), storage folders, and initial admin account are created automatically on startup.

The server will start at:
- **API Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🔑 Initial Administrator Creation

On application startup, the system checks whether any admin account exists in the database. If not, it automatically seeds the first administrator using the credentials configured in `.env`:

* `FIRST_SUPERUSER_EMAIL="admin@kolejka.local"`
* `FIRST_SUPERUSER_USERNAME="admin"`
* `FIRST_SUPERUSER_PASSWORD="AdminPassword123!"`

---

## 🖨️ 3D Print Queue & Orders

### 1. User Print Order Endpoints (`/api/v1/prints`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/prints/estimate` | Calculate estimated price based on `estimated_weight_g` and `estimated_time_hours` |
| `POST` | `/api/v1/prints` | Upload 3D file (`multipart/form-data`) + metadata & submit print order |
| `GET` | `/api/v1/prints/my` | List current user's print jobs with pagination and status filter |
| `GET` | `/api/v1/prints/{print_id}` | Get details of a print job (owner or admin only) |
| `GET` | `/api/v1/prints/{print_id}/file` | Download the uploaded 3D model file (owner or admin only) |
| `DELETE` | `/api/v1/prints/{print_id}` | Cancel print order (only allowed if still `pending_review`) |

### 2. Admin Print Queue Endpoints (`/api/v1/admin/prints`)

*Requires Administrator token (`Authorization: Bearer <token>`).*

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/admin/prints/queue` | View all jobs in the queue with filters (`status`, `payment_status`, `user_id`, `search`) |
| `PATCH` | `/api/v1/admin/prints/{print_id}` | Update status (`ready_to_print`, `printing`, `completed`), payment status, notes, or correct `final_price` |
| `DELETE` | `/api/v1/admin/prints/{print_id}` | Delete print job from queue and remove stored file from disk |

---

## 💰 Automated Pricing Formula

Prices are stored and computed in integer **grosze** ($100\text{ grosze} = 1.00\text{ PLN}$) to prevent floating-point rounding errors and maintain full Stripe compatibility:

$$\text{Estimated Price} = \text{Base Fee} + (\text{Weight} \times \text{Cost per Gram}) + (\text{Time} \times \text{Cost per Hour})$$

Configurable in `.env`:
* `BASE_PRINT_FEE_GROSZE=500` (5.00 PLN)
* `COST_PER_GRAM_GROSZE=15` (0.15 PLN / g)
* `COST_PER_HOUR_GROSZE=300` (3.00 PLN / hour)

Admins can review orders in the queue and adjust `final_price` before or after payment.

---

## 💳 Stripe Readiness

The `print_jobs` table includes fields ready for Stripe integration:
* `payment_status`: `pending`, `paid`, `refunded`, `failed`
* `stripe_session_id`: Checkout session ID
* `stripe_payment_intent_id`: Payment intent ID
* `currency`: `PLN` (or `EUR`, `USD`)

---

## 🧪 Running Tests

Execute the full automated test suite with `pytest`:

```powershell
pytest
```
