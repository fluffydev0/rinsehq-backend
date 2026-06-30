# rinsehq-api

FastAPI backend for the RinseHQ laundry management system. Clean architecture with swappable repositories, JWT auth, and SQLite by default.

## Architecture

```
src/rinsehq/
├── domain/           # Entities & repository interfaces
├── application/      # Use cases & DTOs
├── infrastructure/   # SQLAlchemy, JWT, DI
└── presentation/     # FastAPI routers & schemas
```

## Getting started

```bash
cd rinsehq-api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn rinsehq.main:app --reload --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API docs.

### Demo credentials

- Email: `demo@rinsehq.com`
- Password: `Demo1234!`

## API (v1)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health` | — | Liveness |
| POST | `/api/v1/auth/signup` | — | Register |
| POST | `/api/v1/auth/login` | — | JWT login |
| GET | `/api/v1/auth/me` | Bearer | Current user |
| GET | `/api/v1/orders` | Bearer | List orders |
| POST | `/api/v1/orders` | Bearer | Create order |
| GET | `/api/v1/orders/{id}` | Bearer | Order detail |
| PATCH | `/api/v1/orders/{id}` | Bearer | Update order |
| GET | `/api/v1/dashboard/summary` | Bearer | Status counts |

## Scripts

| Command | Description |
|---------|-------------|
| `uvicorn rinsehq.main:app --reload` | Dev server |
| `alembic upgrade head` | Run migrations |
| `pytest` | Run tests |

## Configuration

See `.env.example` for `DATABASE_URL`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `CORS_ORIGINS`, and `SEED_DEMO_DATA`.
# rinsehq-backend
# rinsehq-backend
