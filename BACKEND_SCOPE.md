# RinseHQ API — Backend Scope & Feature Inventory

> **Version:** 0.1.0  
> **Purpose:** Full breakdown of the current backend implementation to support the next phase — integrating [Nomba](https://developer.nomba.com/docs/introduction/welcome-to-nomba) as the payment gateway and service provider.  
> **Last updated:** July 2026  
> **Codebase size:** ~90 files | **Endpoints:** 61 (60 route handlers + 1 webhook) | **Background workers:** None

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [API Conventions](#5-api-conventions)
6. [Authentication & Authorization](#6-authentication--authorization)
7. [Complete API Endpoint Reference](#7-complete-api-endpoint-reference)
8. [Database Schema](#8-database-schema)
9. [Business Logic & Use Cases](#9-business-logic--use-cases)
10. [Order & Invoice Lifecycle](#10-order--invoice-lifecycle)
11. [Current Payment Integration (Paystack)](#11-current-payment-integration-paystack)
12. [Nomba Integration Readiness](#12-nomba-integration-readiness)
13. [Configuration & Environment Variables](#13-configuration--environment-variables)
14. [Infrastructure & Deployment](#14-infrastructure--deployment)
15. [Testing](#15-testing)
16. [Known Gaps & Technical Debt](#16-known-gaps--technical-debt)
17. [Appendix A: Nomba Authentication Flow](#appendix-a-nomba-authentication-flow)
18. [Appendix B: Complete File Index](#appendix-b-complete-file-index)
19. [Appendix C: Frontend API Contract](#appendix-c-frontend-api-contract)

---

## 1. Project Overview

**RinseHQ API** is a laundry business management backend built for the [rinsehq-dashboard](https://github.com/rinse-hq/rinsehq-dashboard) frontend. It provides:

- Multi-store laundry business management
- Staff RBAC (role-based access control) per store
- Order creation, pricing, invoicing, and payment collection
- Service catalog and business onboarding
- Dashboard analytics (orders, revenue)
- Customer management
- Sub-admin / team management

**Target market:** Nigeria (`country` default `nigeria` on business profiles, amounts in **kobo**, VAT default 7.5%).

**Current payment provider:** Paystack (partially implemented; demo mode when not configured).

**Planned payment provider:** Nomba — Accept Payments (Checkout / Charge API), webhooks, and potentially Transfers.

### 1.1 System Context

```mermaid
flowchart LR
    subgraph clients [Clients]
        Dashboard[rinsehq-dashboard]
        CustomerPage[Public invoice page]
    end
    subgraph api [RinseHQ API]
        FastAPI[FastAPI /v1]
    end
    subgraph data [Data]
        PG[(PostgreSQL)]
    end
    subgraph external [External Services]
        SMTP[Gmail SMTP]
        Cloudinary[Cloudinary]
        Paystack[Paystack API]
        Nomba[Nomba API - planned]
    end
    Dashboard -->|JWT Bearer| FastAPI
    CustomerPage -->|Public invoice/pay| FastAPI
    FastAPI --> PG
    FastAPI --> SMTP
    FastAPI --> Cloudinary
    FastAPI --> Paystack
    FastAPI -.->|next phase| Nomba
    Paystack -->|webhook| FastAPI
    Nomba -.->|webhook planned| FastAPI
```

---

## 2. Architecture

The codebase follows **clean / hexagonal architecture** with four layers:

```
┌─────────────────────────────────────────────────────────────┐
│  presentation/     FastAPI routers, Pydantic schemas, mappers │
├─────────────────────────────────────────────────────────────┤
│  application/      Use cases, DTOs, pricing services         │
├─────────────────────────────────────────────────────────────┤
│  domain/           Entities, repository protocols, service   │
│                    interfaces (EmailService, StorageService) │
├─────────────────────────────────────────────────────────────┤
│  infrastructure/   SQLAlchemy repos, JWT, SMTP, Cloudinary,   │
│                    Paystack client, DI, seed data            │
└─────────────────────────────────────────────────────────────┘
```

**Dependency direction:** `presentation → application → domain ← infrastructure`

- **Domain** defines *what* the business needs (entities, repository interfaces).
- **Application** orchestrates use cases (signup, create order, finalize order).
- **Infrastructure** implements persistence and external services.
- **Presentation** exposes HTTP endpoints and maps to/from API schemas.

**Entry point:** `src/rinsehq/main.py` — creates FastAPI app, CORS, lifespan (DB init, Render config validation), mounts `/v1` router.

### 2.1 Layer Dependency Diagram

```mermaid
flowchart TB
    subgraph presentation [Presentation Layer]
        Routers[api/v1 routers]
        Schemas[Pydantic schemas + mappers]
        Helpers[unwrap_result]
    end
    subgraph application [Application Layer]
        UseCases[use_cases/]
        DTOs[dtos/]
        Pricing[order_pricing.py]
    end
    subgraph domain [Domain Layer]
        Entities[entities/]
        RepoProtocols[repositories/]
        ServiceProtocols[services/]
    end
    subgraph infrastructure [Infrastructure Layer]
        SQLRepos[sqlalchemy_*_repository]
        Paystack[paystack_client]
        JWT[jwt + passwords]
        DI[di.py]
    end
    Routers --> UseCases
    Routers --> SQLRepos
    Routers --> Paystack
    UseCases --> RepoProtocols
    UseCases --> Entities
    SQLRepos --> RepoProtocols
    SQLRepos --> Entities
    Paystack -.->|planned protocol| ServiceProtocols
```

### 2.2 Request Lifecycle

```mermaid
sequenceDiagram
    participant Client
    participant Router as FastAPI Router
    participant DI as Depends di.py
    participant UC as UseCase or Repo
    participant DB as SQLAlchemy Session
    Client->>Router: HTTP request
    Router->>DI: get_current_user / require_permission
    DI->>DB: Load user / store assignment
    Router->>UC: Execute business logic
    UC->>DB: Query / mutate
    UC-->>Router: Result or entity
    Router-->>Client: ApiResponse envelope
```

**Note:** Payment and webhook routes bypass use cases — they call `PaystackClient` and repositories directly from the presentation layer (technical debt for Nomba refactor).

### 2.3 Middleware

Only **CORS** is configured (`main.py`). No custom auth middleware — authentication is entirely via FastAPI `Depends()`.

| Middleware | File | Behavior |
|------------|------|----------|
| CORSMiddleware | `main.py` | `allow_origins` from settings, credentials, all methods/headers |
| HTTPException handler | `main.py` | Normalizes errors to `{ success: false, error: "..." }` |

**Not present:** rate limiting, request logging, token blacklist, `RequestValidationError` custom handler.

---

## 3. Technology Stack

| Layer | Technology | Version / Notes |
|-------|------------|-----------------|
| Language | Python | 3.12.8 (`.python-version`, `runtime.txt`, `Dockerfile`) |
| Web framework | FastAPI | ≥0.115.0 |
| ASGI server | Uvicorn | ≥0.32.0 `[standard]` |
| ORM | SQLAlchemy | ≥2.0.36 |
| Migrations | Alembic | ≥1.14.0 |
| Database (prod/dev) | PostgreSQL | 16 (`docker-compose.yml`) |
| Database (tests) | SQLite | In-memory (`StaticPool`) |
| DB driver | psycopg | ≥3.2.0 (`postgresql+psycopg://`) |
| Validation | Pydantic | ≥2.10.0 + pydantic-settings ≥2.6.0 |
| Auth | JWT (PyJWT, HS256) | Stateless bearer tokens |
| Password hashing | bcrypt | ≥4.0.0 |
| Email | Gmail SMTP | OTP verification, password reset, admin invites |
| File storage | Cloudinary | ≥1.41.0 — onboarding uploads |
| Payments | Paystack | Initialize, webhook, refund via httpx |
| HTTP client | httpx | ≥0.28.0 |
| Testing | pytest ≥8.3, pytest-asyncio ≥0.24 | `asyncio_mode = auto` |
| Deployment | Render | `scripts/start.sh` (migrate + uvicorn) |
| Container | Docker | API image; Compose runs Postgres only |
| Background jobs | — | **None** (no Celery, RQ, Redis, APScheduler) |

---

## 4. Project Structure

```
rinsehq-api/                          # ~90 files total
├── src/rinsehq/
│   ├── main.py                          # FastAPI app factory
│   ├── config.py                        # Settings (env vars)
│   ├── seed_cli.py                      # CLI wrapper for seeding
│   │
│   ├── presentation/
│   │   ├── api/v1/                      # 15 router modules (see §7)
│   │   │   ├── router.py                # Aggregates all v1 routers
│   │   │   ├── auth.py                  # 10 handlers
│   │   │   ├── stores.py                # 7 handlers
│   │   │   ├── onboarding.py            # 4 handlers
│   │   │   ├── dashboard.py             # 4 handlers
│   │   │   ├── orders.py                # 5 handlers
│   │   │   ├── customers.py             # 1 handler
│   │   │   ├── invoices.py              # 3 handlers + webhook
│   │   │   ├── transactions.py          # 3 handlers
│   │   │   ├── services.py              # 9 handlers
│   │   │   ├── account.py               # 4 handlers
│   │   │   ├── admins.py                # 4 handlers
│   │   │   ├── health.py                # 1 handler
│   │   │   └── placeholders.py          # 5 stub handlers
│   │   ├── schemas/
│   │   │   ├── envelope.py              # ApiResponse, PaginationMeta
│   │   │   ├── mappers.py               # Entity → camelCase dicts
│   │   │   ├── auth.py, order.py        # Legacy — not imported
│   │   └── helpers.py                   # unwrap_result → HTTP errors
│   │
│   ├── application/
│   │   ├── use_cases/                   # 9 modules (see §9)
│   │   ├── services/order_pricing.py
│   │   └── dtos/                        # auth, order, common (Result types)
│   │
│   ├── domain/
│   │   ├── entities/                    # 8 entity modules
│   │   ├── repositories/                # 4 protocol modules
│   │   └── services/                    # EmailService, StorageService protocols
│   │
│   └── infrastructure/
│       ├── db/                          # base, models, session, id_generator
│       ├── repositories/                # 4 SQLAlchemy implementations
│       ├── auth/                        # SessionContext, permissions
│       ├── security/                    # JWT, bcrypt
│       ├── email/                         # SMTP + NoOp
│       ├── storage/                     # Cloudinary + local placeholder
│       ├── payments/paystack_client.py  # ← Replace/extend for Nomba
│       ├── di.py
│       └── seed.py
│
├── alembic/versions/                    # 001 → 002 → 003
├── tests/                               # 6 test modules + conftest + helpers
├── scripts/start.sh
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 5. API Conventions

| Convention | Value |
|------------|-------|
| Base path | `/v1` |
| Success response | `{ "success": true, "data": T, "meta"?: { total, page, limit } }` |
| Error response | `{ "success": false, "error": "message" }` |
| Auth header | `Authorization: Bearer <jwt>` |
| Monetary amounts | **Integer kobo** (₦1 = 100 kobo). Display formatting is frontend responsibility. |
| Pagination | `?page=1&limit=20` with `meta.total` |
| API docs | `/docs` (Swagger), `/redoc` |

**Exception:** `GET /v1/health` returns raw `{"status": "ok"}` without the envelope.

### 5.1 Error Handling

**Global handler** (`main.py`): All `HTTPException` responses normalized to `{ success: false, error: "..." }`. If `exc.detail` is already a dict with `"success"`, passes through unchanged.

**Use-case errors** (`presentation/helpers.py` `unwrap_result`):

| Error pattern | HTTP status |
|---------------|-------------|
| `"already exists"` / `"already verified"` | 409 Conflict |
| `"Invalid email or password"` / `"not authenticated"` | 401 Unauthorized |
| `"not found"` | 404 Not Found |
| `"access"` (permission) | 403 Forbidden |
| Default | 400 Bad Request |

**Not handled:** Pydantic `RequestValidationError` (422 uses FastAPI default), unhandled exceptions (500 stack trace).

---

## 6. Authentication & Authorization

### 6.1 Auth Flow

```mermaid
sequenceDiagram
    participant User
    participant API as RinseHQ API
    participant Email as SMTP
    User->>API: POST /auth/signup
    API->>Email: Send 6-digit OTP
    User->>API: POST /auth/verify-email
    User->>API: POST /auth/login
    alt Single store
        API-->>User: JWT with store_id + permission
    else Multiple stores
        API-->>User: JWT without store_id + store list
        User->>API: POST /auth/select-store
        API-->>User: JWT with store_id + permission
    end
    User->>API: GET /auth/me
    API-->>User: User + store session context
```

| Step | Endpoint | Result |
|------|----------|--------|
| Register | `POST /v1/auth/signup` | Creates user + main store, sends 6-digit OTP |
| Verify | `POST /v1/auth/verify-email` | Marks `email_verified = true` |
| Login | `POST /v1/auth/login` | Returns accessible stores; auto-issues token if only 1 store |
| Select store | `POST /v1/auth/select-store` | Issues JWT with `store_id` claim |
| Session | `GET /v1/auth/me` | Current user + store context |

**Password flows:** change password (authenticated), forgot password (OTP email), reset password (OTP + new password).

**Logout:** `POST /v1/auth/logout` → 204 No Content. Stateless — no server-side token invalidation.

### 6.2 JWT Payload

```json
{
  "sub": "<user_uuid>",
  "store_id": "STR-001",
  "permission": "full_admin",
  "exp": 1234567890
}
```

- **User-only token:** Issued on login when user has multiple stores (no `store_id` yet).
- **Session token:** Issued after `select-store` or auto on single-store login.

### 6.3 RBAC (Role-Based Access Control)

**Permission levels:** `full_admin`, `manager`, `staff`, `viewer`

**Capabilities:**

| Capability | full_admin | manager | staff | viewer |
|------------|:----------:|:-------:|:-----:|:------:|
| orders | ✓ | ✓ | ✓ | ✓ (read-only) |
| services | ✓ | ✓ | — | ✓ (read-only) |
| transactions | ✓ | ✓ | — | ✓ (read-only) |
| reports | ✓ | ✓ | — | ✓ (read-only) |
| settings | ✓ | — | — | — |
| adminManagement | ✓ | — | — | — |

- `viewer` is **read-only** — POST/PUT/PATCH/DELETE blocked by `require_permission`.
- Custom permissions can override defaults per assignment (`custom_permissions` JSON on `store_assignments`).
- Store roles: `owner`, `manager`, `sub_admin`.

### 6.4 Dependency Injection (Auth)

**File:** `src/rinsehq/infrastructure/di.py`

| Dependency | Type alias | Purpose |
|------------|------------|---------|
| `get_db_session` | `DbSession` | SQLAlchemy session with auto commit/rollback |
| `get_current_user` | `CurrentUser` | Bearer JWT → `User` entity (store not required) |
| `get_session_context` | `CurrentSession` | JWT must include valid `store_id` + store assignment |
| `require_permission("X")` | — | Session + capability check + read-only guard |
| `require_any_permission("X", "Y")` | — | OR check (e.g. services list) |

**Repository factories:** `get_auth_repository`, `get_store_repository`, `get_order_repository`, `get_catalog_repository`, `get_billing_repository`, `get_account_repository`.

### 6.5 Public vs Authenticated Endpoints

| Access level | Endpoints |
|--------------|-----------|
| **Public (no auth)** | `GET /health`, all `/auth/*` except `/me`, `change-password`, `select-store`; `GET /invoices/{id}`, `POST /invoices/{id}/pay`; `POST /webhooks/paystack`; all placeholder routes |
| **User token (no store)** | `POST /auth/select-store`, onboarding routes with `CurrentUser` |
| **Session token (store-scoped)** | Dashboard, account, most store reads, `GET /invoices/{id}/payment-link` |
| **Permission-gated** | Orders, services, transactions, admins, store mutations |

**Security note for Nomba:** Invoice view and pay endpoints are **public** — anyone with the invoice UUID can view and initiate payment. Payment references must be unguessable; webhook signature verification is critical.

---

## 7. Complete API Endpoint Reference

**Total: 61 endpoints** (60 `@router` handlers + 1 `@webhook_router` handler).

### 7.0 Router Module Summary

| Module | Handlers | Prefix | Primary dependencies |
|--------|:--------:|--------|---------------------|
| `health.py` | 1 | `/health` | None |
| `auth.py` | 10 | `/auth` | Auth repo, email service, JWT |
| `stores.py` | 7 | `/stores` | Store repo, auth repo |
| `onboarding.py` | 4 | `/onboarding` | Store/catalog/account repos, storage |
| `dashboard.py` | 4 | `/dashboard` | Order repo, billing repo |
| `orders.py` | 5 | `/orders` | Order repo, use cases |
| `customers.py` | 1 | `/customers` | Catalog repo |
| `invoices.py` | 3 | `/invoices` | Billing repo, PaystackClient |
| `invoices.py` (webhook) | 1 | `/webhooks` | Billing repo, order repo, PaystackClient |
| `transactions.py` | 3 | `/transactions` | Billing repo, PaystackClient |
| `services.py` | 9 | `/services` | Catalog repo |
| `account.py` | 4 | `/account` | Account repo |
| `admins.py` | 4 | `/admins` | Account repo, email service |
| `placeholders.py` | 5 | *(root)* | None (stubs) |

### 7.1 Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/health` | Public | Health check `{"status": "ok"}` |

### 7.2 Auth (`/v1/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/signup` | Public | Register user, create main store, send email OTP |
| POST | `/login` | Public | Validate credentials; list stores; auto-token if 1 store |
| POST | `/select-store` | User | Issue store-scoped JWT |
| POST | `/verify-email` | Public | Verify 6-digit OTP |
| POST | `/resend-verification` | Public | Resend verification OTP |
| POST | `/logout` | Public | 204 No Content |
| POST | `/change-password` | User | Change password with current password |
| POST | `/forgot-password` | Public | Send reset OTP (silent if email unknown) |
| POST | `/reset-password` | Public | Reset password with OTP |
| GET | `/me` | Session | Current session user with store context |

### 7.3 Stores (`/v1/stores`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/accessible` | User | All stores user can access |
| GET | `` | Session | Stores owned by current user |
| GET | `/{store_id}` | Session | Store detail |
| POST | `` | Perm(settings) | Create store |
| PATCH | `/{store_id}` | Perm(settings) | Update store |
| GET | `/{store_id}/assignments` | Perm(settings) | List staff assignments |
| POST | `/{store_id}/assignments` | Perm(settings) | Create assignment; auto-create user if new email |

### 7.4 Onboarding (`/v1/onboarding`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/business-info` | User | Multipart: business name, bio, reg no, logo/banner/doc uploads |
| POST | `/business-address` | User | Business address; syncs main store address |
| POST | `/business-services` | Perm(services) | Set laundry modes/types/order types + seed default services |
| POST | `/complete` | User | Mark `onboarding_completed` on user |

### 7.5 Dashboard (`/v1/dashboard`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/summary` | Session | Counts: active, completed, pending, draft orders |
| GET | `/chart/completed-orders` | Session | Hourly completed orders today (9-point chart) |
| GET | `/revenue` | Session | Revenue total + success rate from transactions |
| GET | `/recent-orders` | Session | Recent orders (`?limit=5`) |

### 7.6 Orders (`/v1/orders`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | Perm(orders) | List orders; `?status`, `?search`, `?page`, `?limit` |
| POST | `` | Perm(orders) | Create **draft** order (no invoice) |
| GET | `/{order_id}` | Perm(orders) | Order detail with line items |
| PATCH | `/{order_id}` | Perm(orders) | Update draft order fields |
| POST | `/{order_id}/finalize` | Perm(orders) | Validate, compute VAT, create invoice, return payment link |

**Order statuses:** `draft` → `pending` (on finalize) → `active` / `completed` (manual or future automation)

### 7.7 Customers (`/v1/customers`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | Perm(orders) | Search (`?search=`) or list recent (`?limit=20`) |

### 7.8 Invoices (`/v1/invoices`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/{invoice_id}` | **Public** | Invoice detail (customer payment page) |
| POST | `/{invoice_id}/pay` | **Public** | Initialize Paystack payment; returns `authorizationUrl` |
| GET | `/{invoice_id}/payment-link` | Session | Shareable frontend URL `{APP_BASE_URL}/invoice/{id}` |

### 7.9 Webhooks (`/v1/webhooks`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/paystack` | HMAC signature | Handle `charge.success` / `charge.failed` |

### 7.10 Transactions (`/v1/transactions`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | Perm(transactions) | List; `?status`, `?type`, `?page`, `?limit` |
| GET | `/{txn_id}` | Perm(transactions) | Transaction detail |
| POST | `/{txn_id}/refund` | Perm(transactions) | Paystack refund + create refund transaction record |

### 7.11 Services (`/v1/services`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | Perm(orders OR services) | List services; `?status`, `?category` |
| GET | `/summary` | Perm(services) | Service summary stats |
| GET | `/config` | Perm(services) | Laundry modes, service types, order types |
| PUT | `/config` | Perm(services) | Replace full config |
| POST | `/config/items` | Perm(services) | Add item to config section |
| GET | `/{service_id}` | Perm(services) | Service detail |
| POST | `` | Perm(services) | Create service |
| PATCH | `/{service_id}` | Perm(services) | Update service |
| PATCH | `/{service_id}/status` | Perm(services) | Update status only |

### 7.12 Account (`/v1/account`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/personal` | Session | Personal info |
| PATCH | `/personal` | Session | Update name/phone |
| GET | `/business` | Session | Business profile |
| PATCH | `/business` | Session | Update business profile |

### 7.13 Admins (`/v1/admins`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `` | Perm(adminManagement) | List sub-admins |
| POST | `` | Perm(adminManagement) | Create sub-admin, send invite email |
| PATCH | `/{admin_id}` | Perm(adminManagement) | Update sub-admin |
| DELETE | `/{admin_id}` | Perm(adminManagement) | Delete sub-admin (204) |

### 7.14 Placeholders (Stubs — Not Implemented)

| Method | Path | Returns |
|--------|------|---------|
| GET | `/v1/notifications` | `[]` |
| PATCH | `/v1/notifications/{id}/read` | No-op |
| GET | `/v1/tickets` | `[]` |
| POST | `/v1/tickets` | No-op |
| GET | `/v1/help/articles` | `[]` |

---

## 8. Database Schema

**16 tables**, **17 ORM model classes** across 3 Alembic migrations (`001` → `002` → `003`).

### 8.1 Entity Relationship Diagram

```mermaid
erDiagram
    users ||--o{ stores : owns
    users ||--o| business_profiles : has
    users ||--o{ store_assignments : assigned
    stores ||--o{ store_assignments : has
    stores ||--o| service_configs : has
    stores ||--o{ services : offers
    stores ||--o{ customers : has
    stores ||--o{ orders : receives
    stores ||--o{ transactions : records
    customers ||--o{ orders : places
    orders ||--o{ order_line_items : contains
    orders ||--o| invoices : generates
    orders ||--o{ transactions : paid_via
    invoices ||--o{ invoice_line_items : contains
```

**Ephemeral tables:** `verification_codes`, `password_reset_codes` (OTP storage)  
**Utility table:** `id_sequences` (prefixed ID generation)

### 8.2 Table Reference (Summary)

| Table | Primary Key | Purpose |
|-------|-------------|---------|
| `id_sequences` | `prefix` | Atomic counter for prefixed IDs |
| `users` | UUID | Accounts: email, password_hash, phone, email_verified, onboarding_completed |
| `verification_codes` | UUID | Email verification OTP (6 digits, expires_at) |
| `password_reset_codes` | UUID | Password reset OTP |
| `stores` | `STR-NNN` | Store locations: name, address, city, phone, is_main_store, status, owner |
| `store_assignments` | `ADM-NNN` | User↔store RBAC: role, permission_level, custom_permissions (JSON) |
| `business_profiles` | UUID | 1:1 user business info: name, bio, reg no, address, logo/banner/doc URLs |
| `service_configs` | store_id | JSON config: laundry modes, service types, order types |
| `services` | `SRV-NNN` | Per-store catalog: name, category, laundry_mode, unit_price, pricing_unit, turnaround |
| `customers` | UUID | Per-store customers: name, email, phone, address |
| `orders` | UUID | Orders: customer info, status, pricing, payment_status/method, pickup/delivery |
| `order_line_items` | UUID | Order line items: name, quantity, unit_price, amount, laundry_mode |
| `invoices` | UUID | 1:1 with order: invoice_no, status, subtotal, vat, discount, total |
| `invoice_line_items` | UUID | Invoice line items snapshot |
| `transactions` | `TXN-NNN` | Payment ledger: reference, amount, type, status, fee, net, channel, paid_at |

### 8.3 Per-Table Column Reference

**Source:** `src/rinsehq/infrastructure/db/models.py`

#### `id_sequences`
| Column | Type | Notes |
|--------|------|-------|
| `prefix` | String(16) PK | e.g. `STR-`, `TXN-` |
| `last_value` | Integer | Incremented atomically with `FOR UPDATE` |

#### `users`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID string PK | Auto-generated |
| `email` | String(255) unique | Indexed |
| `name` | String(255) | |
| `password_hash` | String(255) | bcrypt |
| `phone` | String(32) | Default `""` |
| `email_verified` | Boolean | Default false |
| `onboarding_completed` | Boolean | Default false |
| `created_at` | DateTime TZ | Server default now |

#### `verification_codes` / `password_reset_codes`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `email` | String(255) | Indexed |
| `code` | String(6) | OTP |
| `expires_at` | DateTime TZ | |
| `created_at` | DateTime TZ | |

#### `stores`
| Column | Type | Notes |
|--------|------|-------|
| `id` | String(16) PK | `STR-NNN` via id_sequences |
| `name`, `address`, `city`, `phone` | String | |
| `is_main_store` | Boolean | |
| `status` | String(16) | Default `active` |
| `owner_user_id` | FK → users | Indexed |
| `created_at` | DateTime TZ | |

#### `store_assignments`
| Column | Type | Notes |
|--------|------|-------|
| `id` | String(16) PK | `ADM-NNN` |
| `store_id`, `user_id` | FK | Indexed |
| `email`, `name` | String | Denormalized |
| `role` | String(16) | `owner`, `manager`, `sub_admin` |
| `permission_level` | String(32) | `full_admin`, `manager`, `staff`, `viewer` |
| `custom_permissions` | JSON nullable | Override capability map |
| `status` | String(16) | Default `active` |

#### `business_profiles`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `user_id` | FK unique | 1:1 with user |
| `store_id` | FK nullable | Optional link to main store |
| `business_name`, `bio`, `registration_no` | String/Text | |
| `address`, `city`, `postal_code`, `country` | String | `country` default `nigeria` |
| `phone`, `whatsapp` | String | |
| `logo_url`, `banner_url`, `document_url` | String nullable | Cloudinary URLs |

#### `service_configs`
| Column | Type | Notes |
|--------|------|-------|
| `store_id` | FK PK | 1:1 with store |
| `config` | JSON | Laundry modes, service types, order types |

#### `services`
| Column | Type | Notes |
|--------|------|-------|
| `id` | String(16) PK | `SRV-NNN` |
| `store_id` | FK | Indexed |
| `name`, `category`, `laundry_mode` | String | |
| `unit_price` | Integer | Kobo |
| `pricing_unit` | String | e.g. per item, per kg |
| `turnaround_hours` | Integer | Default 24 |
| `status` | String(16) | `active` / `inactive` |
| `description` | Text | |
| `orders_count` | Integer | Denormalized counter |
| `updated_at` | DateTime TZ | |

#### `customers`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `store_id` | FK | Indexed |
| `name`, `email`, `phone`, `address` | String | |

#### `orders`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `store_id` | FK | Indexed |
| `customer_id` | FK nullable | |
| `type` | String(32) | `mobile_app` / `offline` |
| `customer`, `customer_email`, `customer_phone`, `customer_address` | String | Snapshot on order |
| `amount_cents` | Integer | Legacy/total field |
| `status` | String(32) indexed | `draft`, `pending`, `active`, `completed` |
| `order_date`, `delivery_date` | DateTime TZ | |
| `delivery_mode`, `order_type`, `laundry_mode`, `service_type` | String | |
| `payment_status` | String(16) | `paid` / `not_paid` |
| `payment_method` | String(64) | Set on webhook |
| `pickup_date`, `pickup_time`, `delivery_time` | String | |
| `description` | Text | |
| `subtotal`, `vat`, `discount`, `total` | Integer | Kobo |
| `created_at` | DateTime TZ | |

#### `order_line_items`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `order_id` | FK | Indexed, cascade delete |
| `name`, `quantity`, `unit_price`, `amount` | | Kobo for prices |
| `laundry_mode` | String nullable | |

#### `invoices`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | Used in public payment URL |
| `order_id` | FK unique | 1:1 with order |
| `store_id` | FK | Indexed |
| `invoice_no` | String(64) indexed | Format `INV-{ORDER_ID_PREFIX}` |
| `status` | String(16) | `not_paid` / `paid` |
| `subtotal`, `vat`, `discount`, `total` | Integer | Kobo |
| `invoice_date`, `created_at` | DateTime TZ | |

#### `invoice_line_items`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `invoice_id` | FK | Indexed, cascade delete |
| `index` | Integer | Display order |
| `laundry_mode`, `items_label` | String | |
| `unit_price`, `amount` | Integer | Kobo |

#### `transactions`
| Column | Type | Notes |
|--------|------|-------|
| `id` | String(16) PK | `TXN-NNN` |
| `store_id`, `order_id` | FK | Indexed |
| `reference` | String(128) unique | Payment gateway reference |
| `customer` | String(255) | |
| `amount_cents` | Integer | Kobo |
| `type` | String(16) | `payment` / `refund` |
| `payment_method` | String(64) | Default `"Paystack"` in model |
| `status` | String(16) indexed | `successful`, `pending`, `failed` |
| `fee_cents`, `net_amount_cents` | Integer | |
| `channel` | String(64) | card, bank, etc. |
| `description` | Text | |
| `customer_email`, `customer_phone` | String | |
| `paid_at` | DateTime TZ nullable | |
| `created_at` | DateTime TZ | |

### 8.4 Key Enums / Status Values

| Field | Values |
|-------|--------|
| `orders.status` | `draft`, `active`, `pending`, `completed` |
| `orders.payment_status` | `paid`, `not_paid` |
| `invoices.status` | `not_paid`, `paid` |
| `transactions.type` | `payment`, `refund` |
| `transactions.status` | `successful`, `pending`, `failed` |
| `transactions.payment_method` | Default `"Paystack"` (hardcoded in several places) |
| `stores.status` | `active` |
| `services.status` | `active`, `inactive` |

### 8.5 ID Generation

**File:** `src/rinsehq/infrastructure/db/id_generator.py`

Prefixed sequential IDs via `id_sequences` table and `next_prefixed_id(session, prefix, width=3)`:

| Prefix | Entity | Example |
|--------|--------|---------|
| `STR-` | Stores | `STR-001` |
| `SRV-` | Services | `SRV-001` |
| `TXN-` | Transactions | `TXN-001` |
| `ADM-` | Store assignments | `ADM-001` |

Uses `SELECT ... FOR UPDATE` for atomic increment. Orders, invoices, customers, users use UUIDs.

**Invoice number format:** `INV-{order.id[:8].upper()}` (generated in `create_invoice_for_order`).

---

## 9. Business Logic & Use Cases

### 9.1 Auth Use Cases (`auth_flows.py`)

| Use Case | Input | Output | Behavior |
|----------|-------|--------|----------|
| `SignUpUseCase` | `SignUpInput` | `Result[User]` | Create user (bcrypt), main store, business profile stub, send OTP |
| `SignInUseCase` | `SignInInput` | `Result[SignInOutput]` | Verify credentials, return accessible stores |
| `VerifyEmailUseCase` | email + code | `Result[None]` | Validate OTP, mark email verified |
| `ResendVerificationUseCase` | email | `Result[None]` | New OTP + email |
| `SelectStoreUseCase` | user_id + store_id | `Result[StoreAccess]` | Validate access |
| `ChangePasswordUseCase` | current + new password | `Result[None]` | Verify current, update hash |
| `ForgotPasswordUseCase` | email | `Result[None]` | Reset OTP (no email leak) |
| `ResetPasswordUseCase` | email + code + password | `Result[None]` | Validate OTP, update password |

**Legacy duplicates:** `sign_up.py` and `sign_in.py` exist but routes use `auth_flows.py`.

### 9.2 Order Use Cases

| Use Case | File | Input | Output | Behavior |
|----------|------|-------|--------|----------|
| `CreateOrderUseCase` | `create_order.py` | `CreateOrderInput` | `Result[Order]` | Validate, create draft with line items |
| `GetOrderUseCase` | `get_order.py` | order_id + store_id | `Result[Order]` | Fetch by ID |
| `UpdateOrderUseCase` | `get_order.py` | `UpdateOrderInput` | `Result[Order]` | Update draft fields only |
| `ListOrdersUseCase` | `list_orders.py` | filters + pagination | `Result[list]` | Paginated list |
| `FinalizeOrderUseCase` | `finalize_order.py` | order_id + store_id | `Result[FinalizeOutput]` | VAT recompute → pending → invoice |

### 9.3 Pricing Service

**File:** `src/rinsehq/application/services/order_pricing.py`

```python
subtotal = sum(line_item.amount for each item)
vat = round(subtotal * vat_rate_percent / 100)   # default 7.5%
total = max(subtotal + vat - discount, 0)
```

**Example (kobo):** Line items ₦5,000 + ₦3,000 → subtotal `800000` kobo → VAT `60000` (7.5%) → total `860000` kobo (₦8,600).

All values in **kobo**. VAT is recomputed server-side on finalize (client-submitted VAT is overwritten).

### 9.4 Dashboard Use Case

`DashboardSummaryUseCase` (`dashboard_summary.py`) — aggregates order counts by status and transaction revenue for the active store.

### 9.5 Repository Layer

| Repository | File | Key Methods |
|------------|------|-------------|
| `SqlAlchemyAuthRepository` | `sqlalchemy_auth_repository.py` | Users, OTP, credentials |
| `SqlAlchemyStoreRepository` | `sqlalchemy_store_repository.py` | Stores, assignments, accessible stores |
| `SqlAlchemyOrderRepository` | `sqlalchemy_order_repository.py` | CRUD orders, line items, dashboard queries |
| `SqlAlchemyCatalogRepository` | `sqlalchemy_catalog_repository.py` | Services, config, customers |
| `SqlAlchemyBillingRepository` | same file as catalog | Invoices, transactions, revenue |
| `SqlAlchemyAccountRepository` | same file as catalog | Profiles, sub-admins |

### 9.6 Billing Repository Methods

**File:** `src/rinsehq/infrastructure/repositories/sqlalchemy_catalog_repository.py` (`SqlAlchemyBillingRepository`)

| Method | Purpose |
|--------|---------|
| `find_invoice(invoice_id)` | Public invoice lookup |
| `find_invoice_for_store(invoice_id, store_id)` | Store-scoped invoice |
| `create_invoice_for_order(order_id, store_id)` | Copy order line items → invoice; set `invoice_no` |
| `mark_invoice_paid(invoice_id)` | Set `invoices.status = paid` |
| `update_order_payment(order_id, status, method)` | Set `payment_status` + `payment_method` on order |
| `list_transactions(store_id, status, type, page, limit)` | Paginated ledger |
| `find_transaction(txn_id, store_id)` | Single transaction |
| `create_payment_transaction(**fields)` | Insert payment row with `TXN-` ID |
| `create_refund_transaction(payment_id, reason, store_id)` | Clone payment as refund with `ref_` prefix |
| `revenue_summary(store_id)` | Sum successful payments + success rate % |

### 9.7 External Services

| Service | Protocol | Implementation | Fallback |
|---------|----------|----------------|----------|
| Email | `EmailService` | `SmtpEmailService` | `NoOpEmailService` |
| Storage | `StorageService` | `CloudinaryStorageService` | `LocalStorageService` |
| Payments | *(none — direct client)* | `PaystackClient` | Demo mode fake URL |

---

## 10. Order & Invoice Lifecycle

### 10.1 Happy Path Flow

```mermaid
flowchart LR
    A["POST /orders draft"] --> B["PATCH /orders edit"]
    B --> C["POST finalize + invoice"]
    C --> D["GET invoice public"]
    D --> E["POST /pay Paystack"]
    E --> F["Webhook charge.success"]
    F --> G["Invoice paid Order paid"]
```

### 10.2 Payment Sequence Diagram

```mermaid
sequenceDiagram
    participant Customer
    participant Frontend
    participant API as RinseHQ_API
    participant GW as Paystack
    Customer->>Frontend: Open invoice page
    Frontend->>API: GET /v1/invoices/{id}
    API-->>Frontend: Invoice detail
    Frontend->>API: POST /v1/invoices/{id}/pay
    API->>GW: initialize_transaction
    GW-->>API: authorizationUrl
    API-->>Frontend: authorizationUrl + reference
    Frontend->>GW: Customer completes payment
    GW->>API: POST /v1/webhooks/paystack
    API->>API: mark_invoice_paid + update_order_payment
```

### 10.3 Step-by-Step

1. **Create draft** — `POST /v1/orders`
   - Status: `draft`
   - No invoice created
   - Response: `{ order, invoice: null }`

2. **Edit draft** — `PATCH /v1/orders/{id}`
   - Update customer, line items, pickup/delivery, pricing fields

3. **Finalize** — `POST /v1/orders/{id}/finalize`
   - Validates customer name and line items exist
   - Recomputes subtotal, VAT (7.5% default), total server-side
   - Upserts customer record if email provided
   - Sets order status → `pending`
   - Creates invoice (1:1 with order) + invoice line items
   - Response: `{ order, invoice, paymentLink }`
   - `paymentLink` = `{APP_BASE_URL}/invoice/{invoice_id}`

4. **Share payment link** — `GET /v1/invoices/{id}/payment-link` (auth required, store-scoped)

5. **Customer views invoice** — `GET /v1/invoices/{id}` (public, no auth)

6. **Customer pays** — `POST /v1/invoices/{id}/pay`
   - Body: `{ "callbackUrl": "..." }`
   - Generates reference `pay_{random_hex}`
   - Calls Paystack `initialize_transaction`
   - Returns `{ authorizationUrl, reference }`

7. **Webhook confirmation** — `POST /v1/webhooks/paystack`
   - Verifies `x-paystack-signature` (HMAC-SHA512)
   - On `charge.success`: marks invoice paid, updates order `payment_status=paid`, `payment_method=Paystack`
   - **Does not** call `create_payment_transaction()` — ledger gap

8. **Refund** (staff) — `POST /v1/transactions/{id}/refund`
   - Calls Paystack refund API
   - Creates local refund transaction record

---

## 11. Current Payment Integration (Paystack)

### 11.1 Implementation Map

| Concern | File | Key behavior |
|---------|------|--------------|
| Initialize payment | `infrastructure/payments/paystack_client.py` | `POST https://api.paystack.co/transaction/initialize` |
| Pay endpoint | `presentation/api/v1/invoices.py` L40–61 | `pay_{hex}` reference → `authorizationUrl` |
| Webhook | `presentation/api/v1/invoices.py` L78–122 | HMAC-SHA512, `charge.success` handler |
| Refund | `presentation/api/v1/transactions.py` L57–70 | Paystack refund + `create_refund_transaction` |
| Config | `config.py` L84–85 | `paystack_configured` references **undeclared** `paystack_secret_key` |

### 11.2 Paystack Client API

**File:** `src/rinsehq/infrastructure/payments/paystack_client.py`

| Method | Paystack API | Purpose |
|--------|--------------|---------|
| `initialize_transaction()` | `POST /transaction/initialize` | Start payment; returns `authorization_url` |
| `verify_webhook_signature()` | — | HMAC-SHA512 of raw body vs `x-paystack-signature` |
| `refund_transaction()` | `POST /refund` | Refund by transaction reference |

**Demo mode:** When `paystack_configured` is false, returns `{callbackUrl}?reference={ref}&demo=1` without calling Paystack.

### 11.3 Paystack Configuration Gap (Verified)

`Settings.paystack_configured` (line 84–85) checks `self.paystack_secret_key`, but **`paystack_secret_key` is not declared** on the `Settings` class (lines 27–50). This means:

- `PAYSTACK_SECRET_KEY` env var is ignored (`extra="ignore"` on settings)
- Accessing `paystack_secret_key` at runtime would raise `AttributeError` if demo mode check passed incorrectly
- Paystack always runs in **demo mode** in practice

**Fix required:**

```python
paystack_secret_key: str = ""
```

### 11.4 Payment Data Model

The `transactions` table is gateway-agnostic enough for Nomba:

| Column | Nomba mapping |
|--------|---------------|
| `reference` | `merchantTxRef` or order reference from checkout |
| `amount_cents` | `transactionAmount` × 100 (Nomba may use Naira — verify API) |
| `type` | `payment` / `refund` |
| `payment_method` | `"Nomba"` or channel-specific |
| `fee_cents` | `transaction.fee` |
| `channel` | `transaction.type` (card, transfer, etc.) |
| `paid_at` | `transaction.time` |

### 11.5 Known Payment Flow Gaps

| Gap | Impact |
|-----|--------|
| `create_payment_transaction()` not called from `/pay` or webhook | Transaction ledger incomplete for real payments |
| Webhook opens separate DB session (`get_session_factory()()`) | Bypasses FastAPI DI session; commit semantics differ |
| Webhook invoice lookup uses `invoice_no.contains(reference[:8])` | Fragile matching if reference format changes |
| `payment_method` hardcoded to `"Paystack"` | Must generalize for Nomba |
| No idempotency on webhook handling | Duplicate webhooks could cause issues |
| No payment status polling endpoint | Relies entirely on webhook |
| Order `status` stays `pending` after payment | No auto-transition to `active` |
| Refund only via Paystack API | Nomba refund API will differ |

---

## 12. Nomba Integration Readiness

### 12.1 Nomba Product Fit

Based on [Nomba documentation](https://developer.nomba.com/docs/introduction/welcome-to-nomba):

| Nomba Product | RinseHQ Use Case | Current Equivalent |
|---------------|------------------|-------------------|
| **Accept Payments — Checkout** | Customer pays invoice via hosted checkout | Paystack `initialize_transaction` → `authorizationUrl` |
| **Accept Payments — Charge API** | Direct card/bank charge | Not implemented |
| **Virtual Account** | Bank transfer to dedicated account | Not implemented |
| **Webhooks** | Confirm payment, update invoice | Paystack webhook at `/v1/webhooks/paystack` |
| **Transfers** | Payout to store bank accounts | Not implemented (future) |
| **Try the API (sandbox)** | Dev/testing without account | Similar to current Paystack demo mode |

### 12.2 Paystack ↔ Nomba API Equivalence

| RinseHQ today (Paystack) | Nomba equivalent | Notes |
|--------------------------|------------------|-------|
| `POST /transaction/initialize` | [Create online checkout order](https://developer.nomba.com/nomba-api-reference/online-checkout/create-an-online-checkout-order.md) | Returns `checkoutLink` instead of `authorization_url` |
| `x-paystack-signature` (HMAC-SHA512) | `nomba-signature` (HMAC-SHA256) | Different algorithm and header names |
| `charge.success` event | `payment_success` event | Map `data.transaction.merchantTxRef` → RinseHQ `reference` |
| `charge.failed` event | `payment_failed` event | Update transaction status to failed |
| `POST /refund` | [Refund checkout transaction](https://developer.nomba.com/nomba-api-reference/online-checkout/refund-checkout-transaction.md) | Different request shape |
| Static bearer secret | [OAuth access token](https://developer.nomba.com/docs/getting-started/authentication.md) | Obtain → use → refresh |
| Demo mode (no key) | [Sandbox](https://developer.nomba.com/docs/products/accept-payment/sandbox-testing.md) + [Try the API](https://developer.nomba.com/docs/guides/try-the-api.md) | No sign-up required for initial testing |

### 12.3 Recommended Integration Architecture

```mermaid
flowchart TB
    subgraph domainLayer [Domain Layer]
        PG[PaymentGateway Protocol]
    end
    subgraph infraLayer [Infrastructure]
        PS[PaystackClient]
        NB[NombaClient]
        Factory[payment_factory]
    end
    subgraph presLayer [Presentation]
        PayRoute["POST /invoices/id/pay"]
        PSWebhook["POST /webhooks/paystack"]
        NBWebhook["POST /webhooks/nomba"]
    end
    PayRoute --> Factory
    Factory --> PS
    Factory --> NB
    PSWebhook --> PS
    NBWebhook --> NB
    PS --> PG
    NB --> PG
```

**New files (next implementation phase):**

```
domain/services/payment_gateway.py     # Protocol: initialize, verify_webhook, refund
infrastructure/payments/
    paystack_client.py                 # Existing (keep or deprecate)
    nomba_client.py                    # Checkout, token auth, webhook verify
    factory.py                         # PAYMENT_PROVIDER env switch
```

**Files to modify (priority order):**

| Priority | File | Change |
|----------|------|--------|
| High | `config.py` | `paystack_secret_key`, `nomba_*` vars, `payment_provider` |
| High | `infrastructure/payments/` | New `nomba_client.py`, `factory.py` |
| High | `presentation/api/v1/invoices.py` | Gateway abstraction + `POST /webhooks/nomba` |
| High | `presentation/api/v1/transactions.py` | Gateway-agnostic refund |
| Medium | `sqlalchemy_catalog_repository.py` | `create_payment_transaction` on webhook |
| Medium | `di.py` | Inject payment gateway |
| Low | `seed.py`, `tests/` | Demo data + payment flow tests |

### 12.4 Nomba Webhook Handler Design

Based on [Nomba webhook docs](https://developer.nomba.com/docs/api-basics/webhook.md):

**Endpoint:** `POST /v1/webhooks/nomba`

**Headers to verify:**
- `nomba-signature` — HMAC-SHA256 of payload with dashboard signature key
- `nomba-signature-algorithm` — always `HmacSHA256`
- `nomba-timestamp` — RFC-3339 timestamp

**Events to subscribe:**
- `payment_success` — primary payment confirmation
- `payment_failed` — mark transaction failed
- `payment_reversal` — handle chargebacks (future)

**Handler pseudocode:**

```
1. Read raw body + nomba-signature header
2. NombaClient.verify_webhook_signature(body, signature) → 400 if invalid
3. Parse JSON: event_type, data.transaction
4. Extract reference from merchantTxRef (pass same ref at checkout creation)
5. Idempotency: if transactions.reference exists and status=successful → return 200
6. On payment_success:
   a. find_invoice by reference or order linkage table
   b. create_payment_transaction(fee, net, channel from payload)
   c. mark_invoice_paid(invoice_id)
   d. update_order_payment(order_id, "paid", "Nomba")
7. On payment_failed:
   a. create or update transaction with status=failed
8. Return ApiResponse(data=None)
```

**Reference strategy:** Pass `pay_{hex}` (or invoice-prefixed ref) as `merchantTxRef` when creating Nomba checkout order — avoids fragile `invoice_no.contains(reference[:8])` lookup.

### 12.5 Nomba Integration Checklist

#### Phase 0 — Documentation
- [x] Complete backend breakdown document (this file)

#### Phase A — Foundation
- [ ] Add `paystack_secret_key` field to Settings (fix existing bug)
- [ ] Define `PaymentGateway` protocol in domain
- [ ] Add Nomba settings: client ID, client secret, account ID, webhook secret, sandbox flag
- [ ] Implement `NombaClient` (token auth, checkout create, webhook verify)
- [ ] Add payment provider factory based on `PAYMENT_PROVIDER` env

#### Phase B — Payment Flow
- [ ] Update `POST /v1/invoices/{id}/pay` to use gateway abstraction
- [ ] Map Nomba `checkoutLink` → response `authorizationUrl` (frontend compat — see Appendix C)
- [ ] Create `POST /v1/webhooks/nomba` endpoint
- [ ] On `payment_success`: `create_payment_transaction()` + `mark_invoice_paid()` + `update_order_payment()`
- [ ] Store Nomba reference in `transactions.reference`
- [ ] Set `payment_method` dynamically

#### Phase C — Hardening
- [ ] Idempotent webhook processing (dedupe by reference)
- [ ] Payment verification endpoint (Nomba fetch checkout transaction)
- [ ] Nomba refund in `POST /v1/transactions/{id}/refund`
- [ ] Optional migration: `gateway` column on transactions
- [ ] Update `.env.example` with all payment vars
- [ ] Integration tests with Nomba sandbox

#### Phase D — Optional Enhancements
- [ ] Virtual Account for bank transfer on invoices
- [ ] Nomba Transfers for store payouts
- [ ] Per-store Nomba `accountId` (multi-tenant merchants)

### 12.6 What Stays the Same

- Order draft → finalize → invoice lifecycle
- Invoice public page flow (`GET /invoices/{id}`, payment link URL pattern)
- `transactions` table schema (mostly gateway-agnostic)
- Amount handling in kobo
- RBAC for transaction list/refund
- Dashboard revenue queries (read from `transactions`)

---

## 13. Configuration & Environment Variables

### 13.1 Settings Class (`config.py`)

| Variable | Env Alias | Default | Purpose |
|----------|-------------|---------|---------|
| `database_url` | `DATABASE_URL` | `postgresql+psycopg://rinsehq:rinsehq@localhost:5432/rinsehq` | DB connection |
| `jwt_secret` | `JWT_SECRET` | `dev-secret-change-in-production` | JWT signing |
| `jwt_expire_minutes` | `JWT_EXPIRE_MINUTES` | `1440` | Token TTL (24h) |
| `cors_origins` | `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | CORS allowlist |
| `app_base_url` | `APP_BASE_URL` | `http://localhost:5173` | Frontend URL for payment links |
| `smtp_host` | `SMTP_HOST` | `smtp.gmail.com` | Email |
| `smtp_port` | `SMTP_PORT` | `587` | Email |
| `smtp_user` | `SMTP_USER` | `""` | Email |
| `smtp_password` | `SMTP_PASSWORD` | `""` | Email (spaces stripped via `smtp_password_clean`) |
| `smtp_from` | `SMTP_FROM` | `""` | From address |
| `cloudinary_cloud_name` | `CLOUDINARY_CLOUD_NAME` | `""` | File uploads |
| `cloudinary_api_key` | `CLOUDINARY_API_KEY` | `""` | File uploads |
| `cloudinary_api_secret` | `CLOUDINARY_API_SECRET` | `""` | File uploads |
| `cloudinary_folder` | `CLOUDINARY_FOLDER` | `rinsehq/onboarding` | Upload folder |
| `default_vat_rate_percent` | `DEFAULT_VAT_RATE_PERCENT` | `7.5` | VAT on order finalize |

### 13.2 Missing / Proposed Payment Settings

| Variable | Status | Purpose |
|----------|--------|---------|
| `PAYSTACK_SECRET_KEY` | **Referenced, not declared** | Paystack bearer token |
| `PAYMENT_PROVIDER` | Not defined | `paystack` \| `nomba` |
| `NOMBA_CLIENT_ID` | Not defined | OAuth client ID |
| `NOMBA_CLIENT_SECRET` | Not defined | OAuth client secret |
| `NOMBA_ACCOUNT_ID` | Not defined | Parent/sub account ID for API calls |
| `NOMBA_WEBHOOK_SECRET` | Not defined | Webhook signature verification |
| `NOMBA_SANDBOX` | Not defined | Use sandbox base URL |
| `SEED_DEMO_DATA` | In `.env.example`, **not consumed** | Misleading — use CLI `rinsehq-seed` |

### 13.3 Render Deployment Validation

When `RENDER=true`:
- Skips `.env` file (uses dashboard env vars only)
- `validate_deployment_config()` fails fast if `DATABASE_URL` still points to localhost

---

## 14. Infrastructure & Deployment

### 14.1 Local Development

```bash
docker compose up -d          # PostgreSQL on :5432
cp .env.example .env
pip install -e ".[dev]"
alembic upgrade head
python -m rinsehq.infrastructure.seed   # optional demo data
uvicorn rinsehq.main:app --reload --port 8000
```

Frontend: `VITE_API_BASE_URL=http://localhost:8000/v1`

### 14.2 Docker Compose

- **Service:** `postgres:16-alpine` only
- Credentials: `rinsehq` / `rinsehq` / database `rinsehq`
- Port `5432`, volume `rinsehq_pg_data`
- **No API container** — run uvicorn locally

### 14.3 Dockerfile (API)

- Base: `python:3.12-slim`
- Installs `libpq-dev`, `gcc` for psycopg
- `pip install -e .`
- Exposes 8000
- CMD: `uvicorn rinsehq.main:app --host 0.0.0.0 --port ${PORT:-8000}`
- **Does not run migrations** — use `scripts/start.sh` on Render

### 14.4 Render Deployment

| Setting | Value |
|---------|-------|
| Build | `pip install -r requirements.txt` |
| Start | `sh scripts/start.sh` → `alembic upgrade head && uvicorn ...` |
| Env | `DATABASE_URL`, `JWT_SECRET`, optional SMTP/Cloudinary/Paystack/Nomba |

### 14.5 Migrations

| Revision | File | Description |
|----------|------|-------------|
| `001` | `001_initial.py` | Minimal users + orders |
| `002` | `002_full_schema.py` | Full schema (drops/recreates orders; adds all tables) |
| `003` | `003_password_reset_codes.py` | Password reset OTP table |

### 14.6 Demo Seed Data

```bash
python -m rinsehq.infrastructure.seed
python -m rinsehq.infrastructure.seed --force   # wipe & reseed
```

Demo password: `Demo1234!`

| Email | Role | Stores |
|-------|------|--------|
| demo@rinsehq.com | Owner | STR-001, STR-002, STR-003 |
| chioma@laundrycare.ng | Manager | STR-002, STR-003 |
| emeka@laundrycare.ng | Staff | STR-003 |
| fatima@laundrycare.ng | Viewer | STR-001, STR-002 |

---

## 15. Testing

```bash
PYTHONPATH=src pytest tests/ -q
```

### 15.1 Test Coverage Matrix

| Area | File | Covered | Notes |
|------|------|:-------:|-------|
| Health | `test_health.py` | ✓ | `GET /v1/health` |
| Auth signup/login | `test_auth.py` | ✓ | Signup, verify, login, password reset |
| Auth session | `test_auth.py` | ✓ | `/me`, select-store |
| Order CRUD | `test_orders.py` | ✓ | Create, update, finalize |
| Order pricing | `test_order_pricing.py` | ✓ | Unit test for VAT math |
| Dashboard | `test_dashboard.py` | ✓ | Summary counts |
| Paystack initialize | — | ✗ | Demo mode only in manual testing |
| Paystack webhook | — | ✗ | No signature/integration tests |
| Refunds | — | ✗ | |
| Nomba (all) | — | ✗ | Not implemented |
| Onboarding uploads | — | ✗ | Cloudinary not mocked |
| Email sending | — | ✗ | NoOp path in tests |
| Admin management | — | ✗ | |
| Transactions list | — | ✗ | Only via seed data |
| RBAC permission matrix | — | ✗ | Partial via order auth tests |

### 15.2 Proposed Nomba Sandbox Test Plan (Next Phase)

1. Mock Nomba OAuth token endpoint in tests
2. Test `POST /invoices/{id}/pay` returns `authorizationUrl` from `checkoutLink`
3. Test webhook signature verification (valid + invalid signatures)
4. Test `payment_success` creates transaction + marks invoice paid (idempotent)
5. Test `payment_failed` updates transaction status
6. Test refund flow end-to-end

**Test setup:** `tests/conftest.py` uses in-memory SQLite; payment tests may need httpx mock or Nomba sandbox credentials in CI secrets.

---

## 16. Known Gaps & Technical Debt

| # | Gap | Severity | Notes |
|---|-----|----------|-------|
| 1 | `PAYSTACK_SECRET_KEY` not on Settings model | High | Paystack always demo mode |
| 2 | `create_payment_transaction` not called in live payment flow | High | Transaction ledger incomplete |
| 3 | Webhook invoice matching is fragile | Medium | `invoice_no.contains(reference[:8])` |
| 4 | `payment_method` hardcoded `"Paystack"` | Medium | Blocks clean Nomba migration |
| 5 | No payment gateway abstraction | Medium | Direct `PaystackClient` in routes |
| 6 | Payment logic in presentation layer | Medium | Not in use cases; hard to test |
| 7 | Webhook uses separate DB session | Medium | `invoices.py` L100–118 bypasses DI |
| 8 | No automated order status after payment | Medium | Order stays `pending` after pay |
| 9 | Placeholder endpoints | Low | notifications, tickets, help stubs |
| 10 | `/v1/health` no ApiResponse envelope | Low | Inconsistent API |
| 11 | `SEED_DEMO_DATA` env unused | Low | Misleading in `.env.example` |
| 12 | No rate limiting / request logging | Low | Production hardening |
| 13 | Stateless logout | Low | By design for JWT |
| 14 | `.env.example` incomplete | Low | Missing SMTP, Cloudinary, Paystack |
| 15 | Legacy schema files unused | Low | `presentation/schemas/auth.py`, `order.py` |
| 16 | Duplicate auth use cases | Low | `sign_up.py` vs `auth_flows.py` |

---

## Appendix A: Nomba Authentication Flow

Nomba uses **OAuth 2.0 client credentials** — unlike Paystack's static secret key.

```mermaid
sequenceDiagram
    participant API as RinseHQ API
    participant Nomba as Nomba Auth API
    API->>Nomba: POST /authenticate (client_id + client_secret)
    Nomba-->>API: access_token + expires_in
    API->>Nomba: API calls with Bearer access_token
    Note over API,Nomba: On expiry: refresh or re-authenticate
```

| Step | Paystack | Nomba |
|------|----------|-------|
| Credential | `PAYSTACK_SECRET_KEY` (static) | `client_id` + `client_secret` |
| Auth header | `Authorization: Bearer {secret}` | `Authorization: Bearer {access_token}` |
| Token refresh | N/A | `POST` refresh expired token |
| Account scoping | Single secret | `accountId` header/param per request |
| Docs | paystack.com/docs | [Authenticate](https://developer.nomba.com/docs/getting-started/authentication.md) |

**Implication for `NombaClient`:** Cache access token in memory with expiry; refresh before API calls. Consider thread-safe token store if using multiple workers.

---

## Appendix B: Complete File Index

All **90 project files** grouped by layer:

### Root & Config (12)
`BACKEND_SCOPE.md`, `README.md`, `pyproject.toml`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `alembic.ini`, `.env.example`, `.gitignore`, `.python-version`, `runtime.txt`, `scripts/start.sh`

### Alembic (5)
`alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/001_initial.py`, `002_full_schema.py`, `003_password_reset_codes.py`

### Tests (7)
`tests/conftest.py`, `tests/helpers.py`, `tests/test_auth.py`, `tests/test_dashboard.py`, `tests/test_health.py`, `tests/test_order_pricing.py`, `tests/test_orders.py`

### Package Root (3)
`src/rinsehq/__init__.py`, `main.py`, `config.py`, `seed_cli.py`

### Presentation — API (15)
`presentation/api/v1/router.py`, `auth.py`, `stores.py`, `onboarding.py`, `dashboard.py`, `orders.py`, `customers.py`, `invoices.py`, `transactions.py`, `services.py`, `account.py`, `admins.py`, `health.py`, `placeholders.py`

### Presentation — Schemas & Helpers (5)
`presentation/schemas/envelope.py`, `mappers.py`, `auth.py`, `order.py`, `presentation/helpers.py`

### Application (11)
`application/dtos/auth.py`, `common.py`, `order.py`, `application/services/order_pricing.py`, `application/use_cases/auth_flows.py`, `create_order.py`, `dashboard_summary.py`, `finalize_order.py`, `get_order.py`, `list_orders.py`, `sign_in.py`, `sign_up.py`

### Domain — Entities (8)
`domain/entities/account.py`, `customer.py`, `invoice.py`, `order.py`, `service.py`, `store.py`, `transaction.py`, `user.py`

### Domain — Repositories (4)
`domain/repositories/auth_repository.py`, `catalog_repository.py`, `order_repository.py`, `store_repository.py`

### Domain — Services (2)
`domain/services/email_service.py`, `storage_service.py`

### Infrastructure (22)
`infrastructure/di.py`, `seed.py`, `db/base.py`, `models.py`, `session.py`, `id_generator.py`, `repositories/sqlalchemy_auth_repository.py`, `sqlalchemy_catalog_repository.py`, `sqlalchemy_order_repository.py`, `sqlalchemy_store_repository.py`, `auth/context.py`, `permissions.py`, `security/jwt.py`, `passwords.py`, `email/smtp_client.py`, `storage/cloudinary_client.py`, `payments/paystack_client.py`

---

## Appendix C: Frontend API Contract

The [rinsehq-dashboard](https://github.com/rinse-hq/rinsehq-dashboard) frontend expects these payment-related shapes:

### Invoice payment initialization

**Request:** `POST /v1/invoices/{invoice_id}/pay`

```json
{ "callbackUrl": "https://app.example.com/invoice/{id}/callback" }
```

**Response:**

```json
{
  "success": true,
  "data": {
    "authorizationUrl": "https://checkout.paystack.com/...",
    "reference": "pay_a1b2c3d4e5f6"
  }
}
```

### Nomba compatibility strategy

Nomba checkout returns `checkoutLink` instead of `authorization_url`. **Recommended:** map in backend so frontend requires no changes:

```python
# In gateway abstraction / invoices.py
return ApiResponse(data={
    "authorizationUrl": nomba_result.checkout_link,  # alias for compat
    "reference": nomba_result.order_reference,
})
```

### Payment link (staff share)

**Response:** `GET /v1/invoices/{id}/payment-link`

```json
{ "success": true, "data": { "url": "{APP_BASE_URL}/invoice/{invoice_id}" } }
```

### Invoice detail (public page)

**Response:** `GET /v1/invoices/{id}` — camelCase via `invoice_to_response()` mapper (business name, line items, totals, status).

### Finalize order (staff)

**Response:** `POST /v1/orders/{id}/finalize` includes `paymentLink` = `{APP_BASE_URL}/invoice/{invoice_id}`.

---

## Summary for Nomba Phase

**What exists today:**
- Complete order → invoice → payment link flow
- Public invoice page API (`GET` + `POST /pay`)
- Transaction ledger schema and list/refund endpoints
- Paystack client with initialize, webhook, refund (demo mode due to config bug)
- Multi-store RBAC, dashboard revenue from transactions
- Clean architecture suitable for gateway swap

**What needs building for Nomba:**
1. Payment gateway abstraction layer (`PaymentGateway` protocol)
2. Nomba client (OAuth, Checkout API, webhook HMAC-SHA256 verification)
3. Fix `paystack_secret_key` on Settings + add Nomba env vars
4. Fix payment transaction recording in webhook handler
5. New webhook route `POST /v1/webhooks/nomba`
6. Generalize `payment_method` away from hardcoded `"Paystack"`
7. Map `checkoutLink` → `authorizationUrl` for frontend compatibility
8. Integration tests for full payment lifecycle

The existing architecture (clean layers, billing repository, kobo amounts, public invoice endpoints) is well-suited for swapping Paystack with Nomba without restructuring the order/invoice domain.
