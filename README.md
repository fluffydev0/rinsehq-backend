# RinseHQ API

Laundry business management backend for the [rinsehq-dashboard](https://github.com/rinse-hq/rinsehq-dashboard) frontend.

## Stack

- **FastAPI** + Uvicorn
- **PostgreSQL** (Docker) / SQLite (tests)
- **SQLAlchemy 2** + Alembic
- **JWT** auth with multi-store RBAC
- **Gmail SMTP** for OTP / invites
- **Cloudinary** for onboarding file uploads
- **Paystack** for invoice payments

## Quick start

```bash
# Start PostgreSQL
docker compose up -d

# Configure environment
cp .env.example .env
# Edit .env with JWT_SECRET, SMTP, Cloudinary, Paystack keys

# Install & migrate
pip install -e ".[dev]"
alembic upgrade head

# Run API
uvicorn rinsehq.main:app --reload --port 8000
```

Frontend: `VITE_API_BASE_URL=http://localhost:8000/v1`

## API conventions

- Base path: `/v1`
- Responses: `{ "success": true, "data": T }` or `{ "success": false, "error": "..." }`
- Auth: `Authorization: Bearer <token>` (token issued after `POST /auth/select-store` or auto on single-store login)
- Amounts stored in **kobo** (integer); list views format as `N4,300`

## Demo accounts

When `SEED_DEMO_DATA=true`, these accounts are created (password: `Demo1234!`):

| Email | Role | Stores |
|-------|------|--------|
| demo@rinsehq.com | Owner | STR-001, STR-002, STR-003 |
| chioma@laundrycare.ng | Manager | STR-002, STR-003 |
| emeka@laundrycare.ng | Staff | STR-003 |
| fatima@laundrycare.ng | Viewer | STR-001, STR-002 |

## Environment variables

See [`.env.example`](.env.example) for the full list.

### Cloudinary setup

1. Create an account at [Cloudinary Console](https://console.cloudinary.com/)
2. Copy **Cloud name**, **API Key**, and **API Secret** from the dashboard
3. Set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` in `.env`
4. Optional: set `CLOUDINARY_FOLDER=rinsehq/onboarding`

### Gmail SMTP

1. Enable 2FA on your Google account
2. Create an [App Password](https://myaccount.google.com/apppasswords)
3. Set `SMTP_USER`, `SMTP_PASSWORD` (no spaces), `SMTP_FROM` in `.env`

## Architecture

```
presentation/  → FastAPI routers, Pydantic schemas
application/   → Use cases, DTOs
domain/        → Entities, repository protocols
infrastructure/→ SQLAlchemy, JWT, email, Cloudinary, Paystack
```

## Tests

```bash
PYTHONPATH=src pytest tests/ -q
```

## Main endpoints

| Area | Examples |
|------|----------|
| Auth | `POST /v1/auth/signup`, `/login`, `/select-store`, `/verify-email` |
| Stores | `GET /v1/stores`, `POST /v1/stores` |
| Orders | `GET/POST /v1/orders` |
| Dashboard | `GET /v1/dashboard/summary` |
| Services | `GET/POST /v1/services` |
| Invoices | `GET /v1/invoices/:id`, `POST /v1/invoices/:id/pay` |
| Account | `GET/PATCH /v1/account/personal` |
| Admins | `GET/POST /v1/admins` |
