# RinseHQ — Payment Gateway Integration & Frontend Dashboard Guide

> **Purpose:** End-to-end implementation reference for Nomba payment integration (backend) and required updates to [rinsehq-dashboard](https://github.com/rinse-hq/rinsehq-dashboard) (frontend).  
> **Audience:** Backend and frontend engineers implementing or reviewing the payment flow.  
> **Last updated:** July 2026  
> **Related docs:** `NOMBA_INTEGRATION.md` (backend step-by-step), `BACKEND_SCOPE.md` (full API inventory)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [End-to-End Payment Flows](#3-end-to-end-payment-flows)
4. [Backend Implementation (Complete)](#4-backend-implementation-complete)
5. [API Reference — Payment Endpoints](#5-api-reference--payment-endpoints)
6. [Environment & Deployment](#6-environment--deployment)
7. [Frontend Dashboard Implementation](#7-frontend-dashboard-implementation)
8. [Frontend File-by-File Checklist](#8-frontend-file-by-file-checklist)
9. [Testing & Verification](#9-testing--verification)
10. [Troubleshooting](#10-troubleshooting)
11. [Remaining Work & Roadmap](#11-remaining-work--roadmap)

---

## 1. Executive Summary

### What changed

RinseHQ moved from **Paystack** (broken demo mode) to **Nomba** as the payment service provider:

| Area | Before (Paystack) | After (Nomba) |
|------|-------------------|---------------|
| Checkout | `PaystackClient.initialize_transaction()` | `NombaClient.create_checkout()` |
| Webhook | `POST /v1/webhooks/paystack` (HMAC-SHA512) | `POST /v1/webhooks/nomba` (HMAC-SHA256) |
| Auth | Static secret key | OAuth 2.0 client credentials + cached token |
| Transaction ledger | Webhook never wrote to `transactions` | Pending txn on pay init; success/fail on webhook |
| Bank transfer | Not supported | `POST /v1/invoices/{id}/virtual-account` (NUBAN) |
| Frontend contract | `{ authorizationUrl, reference }` | **Same shape** — no breaking change for card pay |

### Backend status

The Nomba integration is **implemented** in this repo:

| Component | File | Status |
|-----------|------|--------|
| Settings | `src/rinsehq/config.py` | Done |
| Nomba HTTP client | `src/rinsehq/infrastructure/payments/nomba_client.py` | Done |
| Payment protocol | `src/rinsehq/domain/services/payment_gateway.py` | Done (optional abstraction) |
| DI wiring | `src/rinsehq/infrastructure/di.py` | Done |
| Pay + webhook routes | `src/rinsehq/presentation/api/v1/invoices.py` | Done |
| Billing repo methods | `src/rinsehq/infrastructure/repositories/sqlalchemy_catalog_repository.py` | Done |
| Integration tests | `tests/test_nomba_payments.py` | Done |
| Lifespan cleanup | `src/rinsehq/main.py` | Done |

### Frontend status

The dashboard repo is separate. **Card checkout requires minimal changes** because the backend preserves `authorizationUrl`. **Recommended enhancements:** bank transfer UI, Nomba branding, payment status polling, transaction ledger updates.

---

## 2. System Architecture

### 2.1 High-level context

```mermaid
flowchart LR
    subgraph staff [Staff — Authenticated Dashboard]
        Orders[Orders page]
        Txns[Transactions page]
        Share[Share payment link]
    end

    subgraph customer [Customer — Public, no auth]
        InvoicePage["/invoice/:id"]
        Callback["/invoice/:id/callback"]
    end

    subgraph api [RinseHQ API — FastAPI /v1]
        PayRoute["POST /invoices/:id/pay"]
        VARoute["POST /invoices/:id/virtual-account"]
        Webhook["POST /webhooks/nomba"]
        Ledger[(transactions table)]
    end

    subgraph nomba [Nomba Sandbox/Prod]
        Checkout[Hosted Checkout]
        VA[Virtual Account NUBAN]
        WH[Webhook delivery]
    end

    Orders -->|finalize| api
    Share -->|payment link| InvoicePage
    InvoicePage -->|card pay| PayRoute
    InvoicePage -->|bank transfer| VARoute
    PayRoute --> Checkout
    VARoute --> VA
    Checkout -->|redirect| Callback
    WH --> Webhook
    Webhook --> Ledger
    Txns -->|list| Ledger
```

### 2.2 Backend layer map

```
presentation/api/v1/invoices.py     ← HTTP: pay, virtual-account, webhook
        │
        ├── infrastructure/payments/nomba_client.py   ← OAuth, checkout, VA, verify
        ├── infrastructure/di.py                    ← NombaClient singleton
        └── infrastructure/repositories/
                sqlalchemy_catalog_repository.py      ← ledger + invoice mutations

domain/services/payment_gateway.py  ← Protocol (future multi-provider switch)
domain/entities/transaction.py      ← Transaction entity
domain/entities/invoice.py          ← Invoice entity
```

### 2.3 Amount units

All RinseHQ amounts are stored in **kobo** (1 NGN = 100 kobo):

- Invoice `total`, order `amount_cents`, transaction `amount_cents` → kobo
- Nomba checkout `order.amount` → kobo (passed directly, no conversion)
- Frontend display: divide by 100 and format as `₦` or `N{amount}`

The webhook handler includes a heuristic: if Nomba sends Naira (value &lt; 1_000_000), multiply by 100 before storing.

---

## 3. End-to-End Payment Flows

### 3.1 Staff flow — create order to payment link

```mermaid
sequenceDiagram
    participant Staff as Dashboard (staff)
    participant API as RinseHQ API
    participant DB as PostgreSQL

    Staff->>API: POST /v1/orders (JWT + store session)
    API->>DB: Create draft order
    Staff->>API: POST /v1/orders/{id}/finalize
    API->>DB: status=pending, create invoice
    API-->>Staff: { order, invoice, paymentLink }
    Note over Staff: paymentLink = APP_BASE_URL/invoice/{invoiceId}
    Staff->>API: GET /v1/invoices/{id}/payment-link (optional)
    API-->>Staff: { url: same payment link }
    Staff->>Staff: Copy link → send to customer (WhatsApp, email, etc.)
```

**Key response from finalize:**

```json
{
  "success": true,
  "data": {
    "order": { "...": "..." },
    "invoice": { "id": "INV-...", "invoiceNo": "INV-...", "total": 107500, "status": "not_paid" },
    "paymentLink": "http://localhost:5173/invoice/{invoice_id}"
  }
}
```

### 3.2 Customer flow — card payment (Nomba Checkout)

```mermaid
sequenceDiagram
    participant Customer as Public invoice page
    participant API as RinseHQ API
    participant Nomba as Nomba Checkout
    participant WH as Webhook handler

    Customer->>API: GET /v1/invoices/{id}
    API-->>Customer: Invoice detail (status, line items, total)
    Customer->>API: POST /v1/invoices/{id}/pay
    Note over Customer,API: Body: { callbackUrl: ".../invoice/{id}/callback" }
    API->>Nomba: POST /checkout/order (OAuth token)
    Nomba-->>API: checkoutUrl
    API->>API: create pending transaction (reference=rinse_inv_{invoice_no})
    API-->>Customer: { authorizationUrl, reference }
    Customer->>Nomba: Redirect to authorizationUrl
    Customer->>Nomba: Enter card details
    Nomba->>WH: POST /v1/webhooks/nomba (payment_success)
    WH->>WH: Verify HMAC-SHA256 signature
    WH->>WH: mark_transaction_successful + mark_invoice_paid + update_order_payment
    Nomba->>Customer: Redirect to callbackUrl
    Customer->>API: GET /v1/invoices/{id} (poll or on callback page)
    API-->>Customer: status=paid
```

**Reference format (stable, idempotent):**

```
rinse_inv_{invoice_no_with_underscores}
Example: INV-2026-0042 → rinse_inv_inv_2026_0042
```

### 3.3 Customer flow — bank transfer (Virtual Account)

```mermaid
sequenceDiagram
    participant Customer as Public invoice page
    participant API as RinseHQ API
    participant Nomba as Nomba Virtual Accounts
    participant WH as Webhook handler

    Customer->>API: POST /v1/invoices/{id}/virtual-account
    API->>Nomba: POST /accounts/virtual
    Nomba-->>API: NUBAN, bankName, accountName
    API->>API: create pending txn (reference=va_rinse_{invoice_no})
    API-->>Customer: { accountNumber, bankName, accountName, amountDue }
    Customer->>Customer: Bank app transfer to NUBAN
    Nomba->>WH: POST /v1/webhooks/nomba (virtual_account.funded)
    WH->>WH: Match accountRef → invoice, mark paid
```

---

## 4. Backend Implementation (Complete)

This section documents **what is built** and **why**, so you can maintain or extend it.

### 4.1 Configuration — `config.py`

Nomba credentials are loaded from environment variables:

| Env var | Settings field | Required | Purpose |
|---------|----------------|----------|---------|
| `NOMBA_CLIENT_ID` | `nomba_client_id` | Yes | OAuth client ID |
| `NOMBA_CLIENT_SECRET` | `nomba_client_secret` | Yes | OAuth private key |
| `NOMBA_ACCOUNT_ID` | `nomba_account_id` | Yes | Sent as `accountId` header on all Nomba calls |
| `NOMBA_WEBHOOK_SECRET` | `nomba_webhook_secret` | Prod only | HMAC-SHA256 webhook verification |
| `NOMBA_BASE_URL` | `nomba_base_url` | No (has default) | Sandbox: `https://sandbox.api.nomba.com/v1` |
| `APP_BASE_URL` | `app_base_url` | Yes | Used for payment links (`/invoice/{id}`) |
| `CORS_ORIGINS` | `cors_origins` | Yes | Must include dashboard origin |

Helper property:

```python
@property
def nomba_configured(self) -> bool:
    return bool(self.nomba_client_id and self.nomba_client_secret and self.nomba_account_id)
```

### 4.2 NombaClient — `nomba_client.py`

**Responsibilities:**

1. **OAuth token management** — `POST /auth/token/issue` with `client_credentials`; token cached in memory with 5-minute expiry buffer.
2. **Checkout** — `POST /checkout/order` → returns `checkoutUrl` mapped to `authorizationUrl` for frontend.
3. **Virtual accounts** — `POST /accounts/virtual` → NUBAN for bank transfer.
4. **Webhook verification** — static method `verify_webhook(raw_body, signature, secret)` using HMAC-SHA256.

**Error types:**

| Exception | When |
|-----------|------|
| `NombaAuthError` | Token issue failed |
| `NombaCheckoutError` | Checkout creation failed → API returns 502 |
| `NombaVirtualAccountError` | VA creation failed → API returns 502 |

**Singleton lifecycle:** Created once via `get_nomba_client()` in DI; closed on app shutdown in `main.py` lifespan.

### 4.3 PaymentGateway protocol — `payment_gateway.py`

Optional domain-layer abstraction for future multi-provider support (`nomba` | `paystack`). Currently routes inject `NombaClient` directly. To add a provider switch later:

1. Implement `PaymentGateway` on `NombaClient` (map `checkout_url` → `authorization_url`).
2. Add `get_payment_gateway()` factory reading `PAYMENT_PROVIDER` env var.
3. Replace `NombaClientDep` with `PaymentGatewayDep` in routes.

### 4.4 Invoice routes — `invoices.py`

#### `POST /v1/invoices/{invoice_id}/pay`

| Step | Action |
|------|--------|
| 1 | Load invoice; reject if already `paid` |
| 2 | Build stable reference: `rinse_inv_{invoice_no}` |
| 3 | If txn with same ref is already `successful`, reject |
| 4 | Call `nomba.create_checkout()` |
| 5 | If no pending txn exists, `create_payment_transaction(status=pending)` |
| 6 | Return `{ authorizationUrl, reference }` |

**Auth:** Public (no JWT). Anyone with invoice UUID can pay.

#### `POST /v1/invoices/{invoice_id}/virtual-account`

| Step | Action |
|------|--------|
| 1 | Load invoice; reject if paid |
| 2 | Build `account_ref = rinse_{invoice_no}` |
| 3 | Call `nomba.create_virtual_account()` |
| 4 | Create pending txn with `reference=va_{account_ref}`, `channel=bank_transfer` |
| 5 | Return NUBAN details + `amountDue` in kobo |

**Auth:** Public.

#### `GET /v1/invoices/{invoice_id}/payment-link`

Returns shareable URL for staff. **Requires store session JWT** + store scope.

#### `POST /v1/webhooks/nomba`

| Event | Handler behavior |
|-------|------------------|
| `payment_success` | Find txn by `merchantTxRef` / `orderReference`; idempotent skip if already successful; `mark_transaction_successful`; `mark_invoice_paid`; `update_order_payment(paid, Nomba)` |
| `payment_failed` | Mark pending txn as `failed` |
| `virtual_account.funded` | Resolve invoice by `accountRef`; mark txn + invoice + order paid |

**Signature:** Header `nomba-signature`. If `NOMBA_WEBHOOK_SECRET` is empty (local dev), verification is skipped with a warning log.

**Always return HTTP 200** — Nomba retries on non-2xx.

### 4.5 Billing repository additions

Methods added to `SqlAlchemyBillingRepository`:

| Method | Purpose |
|--------|---------|
| `find_transaction_by_reference(ref)` | Idempotency + webhook lookup |
| `mark_transaction_successful(id, channel, fee_kobo, net_kobo)` | Post-payment ledger update |
| `mark_transaction_failed(id)` | Failed card payment |
| `find_invoice_by_order_id(order_id)` | Link webhook txn → invoice |
| `find_invoice_by_account_ref(account_ref)` | Virtual account webhook → invoice |

Existing methods reused: `create_payment_transaction`, `mark_invoice_paid`, `update_order_payment`, `find_invoice`.

### 4.6 Database impact

**`transactions` table** (populated correctly now):

| Column | Example after card pay |
|--------|------------------------|
| `reference` | `rinse_inv_inv_2026_0042` |
| `payment_method` | `Nomba` |
| `status` | `pending` → `successful` |
| `channel` | `card` or `bank_transfer` |
| `fee_cents` | From webhook |
| `net_amount_cents` | amount - fee |
| `paid_at` | Set on success |

**`invoices.status`:** `not_paid` → `paid`  
**`orders.payment_status`:** `unpaid` → `paid`  
**`orders.payment_method`:** `Nomba`

Dashboard revenue queries read from `transactions` where `status=successful` — they will now show real data after payments.

---

## 5. API Reference — Payment Endpoints

Base URL: `{API_URL}/v1`  
Envelope: `{ "success": true, "data": {...}, "meta": {...}? }`

### 5.1 Get invoice (public)

```
GET /invoices/{invoice_id}
```

**Response `data` (camelCase):**

```json
{
  "id": "uuid",
  "businessName": "Fresh Laundry Co",
  "status": "not_paid",
  "invoiceNo": "INV-2026-0042",
  "invoiceDate": "2026-07-02T10:00:00",
  "paymentMethod": "",
  "customer": {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "+234...",
    "address": "..."
  },
  "lineItems": [
    {
      "index": 1,
      "laundryMode": "Wash & Fold",
      "itemsLabel": "Shirts x 5",
      "unitPrice": 50000,
      "amount": 50000
    }
  ],
  "subtotal": 100000,
  "vat": 7500,
  "discount": 0,
  "total": 107500,
  "businessContact": {
    "address": "...",
    "phone": "...",
    "whatsapp": "..."
  }
}
```

**Status values:** `not_paid`, `paid` (check this for UI state).

### 5.2 Initialize card payment (public)

```
POST /invoices/{invoice_id}/pay
Content-Type: application/json

{
  "callbackUrl": "https://your-dashboard.com/invoice/{invoice_id}/callback"
}
```

**Success response:**

```json
{
  "success": true,
  "data": {
    "authorizationUrl": "https://checkout.nomba.com/...",
    "reference": "rinse_inv_inv_2026_0042"
  }
}
```

**Errors:**

| Status | When |
|--------|------|
| 404 | Invoice not found |
| 400 | Invoice already paid |
| 502 | Nomba checkout failed |

**Frontend action:** `window.location.href = data.authorizationUrl`

### 5.3 Get virtual account (public) — NEW

```
POST /invoices/{invoice_id}/virtual-account
```

No request body.

**Success response:**

```json
{
  "success": true,
  "data": {
    "accountNumber": "1234567890",
    "bankName": "Nomba MFB",
    "accountName": "RinseHQ — INV-2026-0042",
    "reference": "rinse_inv_2026_0042",
    "amountDue": 107500
  }
}
```

**Frontend action:** Display NUBAN with copy button; show `amountDue / 100` as NGN; poll invoice status until `paid`.

### 5.4 Payment link (staff)

```
GET /invoices/{invoice_id}/payment-link
Authorization: Bearer {store_session_jwt}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "url": "http://localhost:5173/invoice/{invoice_id}"
  }
}
```

### 5.5 List transactions (staff)

```
GET /transactions?status=successful&type=payment&page=1&limit=20
Authorization: Bearer {store_session_jwt}
Permission: transactions
```

**Row shape:**

```json
{
  "id": "TXN-001",
  "reference": "rinse_inv_inv_2026_0042",
  "orderId": "ORD-001",
  "customer": "Jane Doe",
  "amount": "N1,075",
  "type": "payment",
  "paymentMethod": "Nomba",
  "status": "successful",
  "date": "2026-07-02T12:00:00"
}
```

Detail adds: `fee`, `netAmount`, `channel`, `paidAt`, `customerEmail`, `customerPhone`.

### 5.6 Finalize order (staff)

```
POST /orders/{order_id}/finalize
```

Returns `paymentLink` alongside `order` and `invoice` — use this immediately after finalize to show "Share payment link" UI.

---

## 6. Environment & Deployment

### 6.1 Local development

**`.env` (API):**

```bash
DATABASE_URL=postgresql+psycopg://rinsehq:rinsehq@localhost:5432/rinsehq
JWT_SECRET=your-local-secret
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
APP_BASE_URL=http://localhost:5173

NOMBA_CLIENT_ID=<from Nomba developer dashboard>
NOMBA_CLIENT_SECRET=<private key>
NOMBA_ACCOUNT_ID=<parent account id>
NOMBA_WEBHOOK_SECRET=          # leave empty locally
NOMBA_BASE_URL=https://sandbox.api.nomba.com/v1
```

**`.env` (Dashboard — typical Vite):**

```bash
VITE_API_BASE_URL=http://localhost:8000/v1
VITE_APP_URL=http://localhost:5173
```

### 6.2 Render production

| Variable | Notes |
|----------|-------|
| `NOMBA_*` | All four Nomba vars required in prod |
| `NOMBA_WEBHOOK_SECRET` | Set **after** registering webhook URL in Nomba dashboard |
| `APP_BASE_URL` | Production dashboard URL (e.g. `https://app.rinsehq.com`) |
| `CORS_ORIGINS` | Must include production dashboard origin |

**Startup:** `scripts/start.sh` runs Alembic migrations then Uvicorn.

### 6.3 Register Nomba webhook

1. Log into [Nomba Developer Dashboard](https://developer.nomba.com)
2. **Webhooks → Add endpoint**
3. URL: `https://{your-api-host}/v1/webhooks/nomba`
4. Events: `payment_success`, `payment_failed`, `virtual_account.funded`
5. Copy signing secret → `NOMBA_WEBHOOK_SECRET` → redeploy

### 6.4 Local webhook testing (ngrok)

```bash
# Terminal 1
uvicorn rinsehq.main:app --reload --port 8000

# Terminal 2
ngrok http 8000
# Register https://xxxx.ngrok.io/v1/webhooks/nomba in Nomba dashboard
```

### 6.5 Sandbox test cards

| Scenario | Card number |
|----------|-------------|
| Success | `5060 6666 6666 6666 666` |
| Insufficient funds | `5060 6666 6666 6666 674` |

Expiry: any future date. CVV: any 3 digits.

---

## 7. Frontend Dashboard Implementation

The dashboard lives in **rinsehq-dashboard** (separate repo). This section is a detailed implementation guide assuming a **React + Vite + TypeScript** stack with React Router (matching `localhost:5173` defaults in the API config).

### 7.1 What requires zero changes (card pay only)

If the dashboard already:

1. Loads invoice via `GET /v1/invoices/:id`
2. Calls `POST /v1/invoices/:id/pay` with `{ callbackUrl }`
3. Redirects to `response.data.authorizationUrl`
4. Shows success on callback page

…then **card payments work with Nomba without code changes**. The backend deliberately maps Nomba's `checkoutUrl` → `authorizationUrl`.

### 7.2 What you should update

| Priority | Area | Change |
|----------|------|--------|
| **P0** | Branding | Replace "Paystack" labels with "Nomba" or generic "Pay online" |
| **P0** | Callback page | Poll invoice status after redirect (webhook may lag 1–5s) |
| **P0** | Error handling | Handle 502 from pay endpoint ("Payment provider unavailable") |
| **P1** | Bank transfer tab | New UI calling `POST /virtual-account` |
| **P1** | Transactions page | Expect `paymentMethod: "Nomba"`, new `channel` values |
| **P1** | Order detail | Show `paymentStatus` / `paymentMethod` from order API |
| **P2** | Copy payment link | Use `GET /payment-link` or build from `VITE_APP_URL/invoice/:id` |
| **P2** | Amount formatting | Consistent kobo → NGN helper |

### 7.3 Recommended route structure

```
/invoice/:invoiceId              → PublicInvoicePage (view + pay)
/invoice/:invoiceId/callback     → PaymentCallbackPage (post-checkout)
/orders/:orderId                 → OrderDetail (staff — payment status)
/transactions                    → TransactionList (staff — ledger)
```

Staff routes remain behind auth + store selection.

### 7.4 API client layer

Create or update `src/lib/api/invoices.ts`:

```typescript
const API_BASE = import.meta.env.VITE_API_BASE_URL;

export interface Invoice {
  id: string;
  status: "not_paid" | "paid";
  invoiceNo: string;
  total: number; // kobo
  customer: { name: string; email: string; phone: string; address: string };
  lineItems: Array<{
    index: number;
    laundryMode: string;
    itemsLabel: string;
    unitPrice: number;
    amount: number;
  }>;
  subtotal: number;
  vat: number;
  discount: number;
  businessName: string;
  businessContact: { address: string; phone: string; whatsapp: string };
}

export interface PayInvoiceResponse {
  authorizationUrl: string;
  reference: string;
}

export interface VirtualAccountResponse {
  accountNumber: string;
  bankName: string;
  accountName: string;
  reference: string;
  amountDue: number; // kobo
}

interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  error?: string;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  const body: ApiEnvelope<T> = await res.json();
  if (!res.ok || !body.success) {
    throw new Error(body.error ?? `Request failed (${res.status})`);
  }
  return body.data;
}

export function getInvoice(invoiceId: string) {
  return apiFetch<Invoice>(`/invoices/${invoiceId}`);
}

export function payInvoice(invoiceId: string, callbackUrl: string) {
  return apiFetch<PayInvoiceResponse>(`/invoices/${invoiceId}/pay`, {
    method: "POST",
    body: JSON.stringify({ callbackUrl }),
  });
}

export function getVirtualAccount(invoiceId: string) {
  return apiFetch<VirtualAccountResponse>(`/invoices/${invoiceId}/virtual-account`, {
    method: "POST",
  });
}

export function getPaymentLink(invoiceId: string, token: string) {
  return apiFetch<{ url: string }>(`/invoices/${invoiceId}/payment-link`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}
```

### 7.5 Money formatting utility

```typescript
/** Amounts from API are in kobo */
export function formatNgnFromKobo(kobo: number): string {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(kobo / 100);
}

/** For display matching API list responses like "N1,075" */
export function formatNgnPlain(kobo: number): string {
  return `N${(kobo / 100).toLocaleString("en-NG")}`;
}
```

### 7.6 Public invoice page — full implementation pattern

**File:** `src/pages/invoice/PublicInvoicePage.tsx`

**State machine:**

```
loading → ready (not_paid) → paying | showing_va → paid
                      ↘ error
```

**UI sections:**

1. **Header** — business name, invoice number, date
2. **Line items table** — from `invoice.lineItems`
3. **Totals** — subtotal, VAT, discount, total (format from kobo)
4. **Payment method tabs** — "Pay with card" | "Bank transfer"
5. **Pay button** — disabled if `status === "paid"`

**Card pay handler:**

```typescript
async function handleCardPay() {
  setPayError(null);
  setIsPaying(true);
  try {
    const callbackUrl = `${import.meta.env.VITE_APP_URL}/invoice/${invoiceId}/callback`;
    const { authorizationUrl } = await payInvoice(invoiceId, callbackUrl);
    window.location.href = authorizationUrl;
  } catch (e) {
    setPayError(e instanceof Error ? e.message : "Payment failed");
    setIsPaying(false);
  }
}
```

**Bank transfer handler:**

```typescript
async function handleBankTransfer() {
  setVaError(null);
  setIsLoadingVa(true);
  try {
    const va = await getVirtualAccount(invoiceId);
    setVirtualAccount(va);
    startPolling(); // see below
  } catch (e) {
    setVaError(e instanceof Error ? e.message : "Could not load account details");
  } finally {
    setIsLoadingVa(false);
  }
}
```

**Virtual account display component:**

```tsx
function VirtualAccountDetails({ va }: { va: VirtualAccountResponse }) {
  const copy = (text: string) => navigator.clipboard.writeText(text);

  return (
    <div className="va-details">
      <p>Transfer exactly {formatNgnFromKobo(va.amountDue)} to:</p>
      <dl>
        <dt>Account number</dt>
        <dd>
          {va.accountNumber}
          <button type="button" onClick={() => copy(va.accountNumber)}>Copy</button>
        </dd>
        <dt>Bank</dt>
        <dd>{va.bankName}</dd>
        <dt>Account name</dt>
        <dd>{va.accountName}</dd>
      </dl>
      <p className="hint">
        Payment confirms automatically after transfer. This page will update when received.
      </p>
    </div>
  );
}
```

### 7.7 Payment callback page — poll until paid

Nomba redirects to `callbackUrl` **before or after** the webhook completes. Do not assume instant `paid` status.

**File:** `src/pages/invoice/PaymentCallbackPage.tsx`

```typescript
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getInvoice } from "@/lib/api/invoices";

const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 15; // 30 seconds

export function PaymentCallbackPage() {
  const { invoiceId } = useParams<{ invoiceId: string }>();
  const [status, setStatus] = useState<"polling" | "paid" | "pending" | "error">("polling");

  useEffect(() => {
    if (!invoiceId) return;
    let polls = 0;

    const tick = async () => {
      try {
        const invoice = await getInvoice(invoiceId);
        if (invoice.status === "paid") {
          setStatus("paid");
          return;
        }
        polls += 1;
        if (polls >= MAX_POLLS) {
          setStatus("pending");
          return;
        }
        setTimeout(tick, POLL_INTERVAL_MS);
      } catch {
        setStatus("error");
      }
    };

    tick();
  }, [invoiceId]);

  if (status === "polling") return <p>Confirming your payment…</p>;
  if (status === "paid") return <p>Payment successful. Thank you!</p>;
  if (status === "pending")
    return (
      <p>
        Payment received by Nomba — confirmation may take a moment.{" "}
        <Link to={`/invoice/${invoiceId}`}>Refresh invoice</Link>
      </p>
    );
  return <p>Something went wrong. Please contact the business.</p>;
}
```

**Bank transfer polling:** Use the same pattern on `PublicInvoicePage` after showing VA — poll `getInvoice` every 5s until `paid` or user leaves.

### 7.8 Staff — order finalize & share link

After `POST /orders/:id/finalize`, show a modal:

```tsx
function PaymentLinkModal({ invoiceId, paymentLink }: { invoiceId: string; paymentLink: string }) {
  const copy = () => navigator.clipboard.writeText(paymentLink);

  return (
    <div>
      <h3>Invoice ready — share payment link</h3>
      <input readOnly value={paymentLink} />
      <button onClick={copy}>Copy link</button>
      <a href={paymentLink} target="_blank" rel="noreferrer">Preview customer page</a>
    </div>
  );
}
```

Optional: fetch canonical URL from API if `APP_BASE_URL` differs from dashboard URL:

```typescript
const { url } = await getPaymentLink(invoice.id, sessionToken);
```

### 7.9 Staff — transactions page updates

**Display changes:**

| Field | Old (Paystack era) | New (Nomba) |
|-------|-------------------|-------------|
| `paymentMethod` | `"Paystack"` | `"Nomba"` |
| `channel` | often empty | `"card"` or `"bank_transfer"` |
| `status` | often empty ledger | `pending` → `successful` / `failed` |

**Filter chips:** Keep existing status filters; add channel filter if useful.

**Refund button:** Backend refund (`POST /transactions/:id/refund`) currently creates a local refund record only — **does not call Nomba refund API yet**. Disable or warn until Nomba refund is wired.

### 7.10 Staff — order detail payment badge

From `GET /orders/:id`:

```typescript
function PaymentBadge({ order }: { order: { paymentStatus: string; paymentMethod: string } }) {
  const colors = {
    unpaid: "warning",
    paid: "success",
    refunded: "neutral",
  } as const;

  return (
    <span className={`badge badge-${colors[order.paymentStatus as keyof typeof colors] ?? "neutral"}`}>
      {order.paymentStatus}
      {order.paymentMethod ? ` · ${order.paymentMethod}` : ""}
    </span>
  );
}
```

### 7.11 Remove Paystack-specific code (dashboard)

Search the dashboard repo for these patterns and remove/replace:

| Search term | Action |
|-------------|--------|
| `paystack` / `Paystack` | Remove imports, rename UI copy |
| `@paystack/inline-js` | Remove dependency if present |
| `paystack.com` | Remove hardcoded URLs |
| `x-paystack` | Not used on frontend (webhook is server-side) |
| Demo mode `?demo=1` | Remove — Nomba uses real sandbox checkout |

### 7.12 UX copy recommendations

| Location | Suggested copy |
|----------|----------------|
| Pay button | "Pay with card" or "Pay online" |
| Bank tab | "Pay by bank transfer" |
| Processing | "Redirecting to secure checkout…" |
| Callback | "Confirming your payment…" |
| VA hint | "Use this account number for a one-time transfer. Do not save for future payments." |
| Paid state | "This invoice has been paid. Thank you!" |

Avoid mentioning "Nomba" to end customers unless required for trust/compliance — "Secure payment" is usually sufficient.

---

## 8. Frontend File-by-File Checklist

Use this as a PR checklist in **rinsehq-dashboard**:

### New files

- [ ] `src/lib/api/invoices.ts` — invoice + pay + virtual account API functions
- [ ] `src/lib/format/money.ts` — kobo → NGN formatters
- [ ] `src/pages/invoice/PublicInvoicePage.tsx` — public pay page (or update existing)
- [ ] `src/pages/invoice/PaymentCallbackPage.tsx` — post-checkout polling
- [ ] `src/components/invoice/VirtualAccountDetails.tsx` — NUBAN display + copy
- [ ] `src/components/invoice/PaymentMethodTabs.tsx` — card vs bank transfer

### Files to modify

- [ ] `src/router.tsx` — add `/invoice/:id/callback` route
- [ ] `src/pages/orders/OrderDetail.tsx` — payment status badge
- [ ] `src/pages/orders/FinalizeOrderFlow.tsx` — payment link modal after finalize
- [ ] `src/pages/transactions/TransactionList.tsx` — Nomba method + channel column
- [ ] `src/pages/transactions/TransactionDetail.tsx` — show fee, netAmount, channel, paidAt
- [ ] `.env.example` — `VITE_API_BASE_URL`, `VITE_APP_URL`
- [ ] Any Paystack-branded components — rebrand or remove

### Files likely unchanged

- [ ] Auth flow (`/auth/login`, store selection)
- [ ] Order creation form
- [ ] Dashboard summary (reads orders; revenue may come from transactions endpoint separately)
- [ ] Services, customers, admins modules

---

## 9. Testing & Verification

### 9.1 Backend automated tests

```bash
pytest tests/test_nomba_payments.py -v
```

Covers:

- Webhook HMAC verification
- `payment_success` → invoice paid + txn successful
- `POST /pay` → pending transaction created + `authorizationUrl` returned

### 9.2 Manual E2E checklist

```
□ Staff: create order → finalize → receive paymentLink
□ Public: open paymentLink → invoice loads (GET /invoices/:id)
□ Card: click Pay → redirect to Nomba checkout
□ Card: pay with 5060...666 → callback page → status becomes paid
□ DB/API: transactions row status=successful, invoice status=paid
□ Idempotency: resend webhook → no duplicate credit
□ Bank: request virtual account → NUBAN displayed
□ Bank: (sandbox) fund VA → webhook → invoice paid
□ Staff: transactions list shows new payment
□ Staff: order detail shows paymentStatus=paid, paymentMethod=Nomba
□ Failed card: 5060...674 → txn status=failed, invoice still not_paid
```

### 9.3 Frontend testing checklist

```
□ Public invoice page loads without auth
□ Card pay redirects to Nomba (not Paystack URL)
□ Callback page polls and shows success
□ Bank transfer tab shows NUBAN and copy works
□ Paid invoice hides pay buttons, shows confirmation
□ Already-paid invoice: pay returns 400 with clear message
□ 502 error shows user-friendly message
□ Payment link copy works after finalize
□ Transactions table shows Nomba payments after webhook
□ Mobile layout: VA details readable, copy button accessible
```

### 9.4 CORS verification

If the public invoice page calls the API from the browser, ensure the dashboard origin is in `CORS_ORIGINS`. Payment initiation is a cross-origin POST from the customer browser.

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Pay returns 502 | Invalid Nomba credentials or sandbox down | Check `NOMBA_*` env vars; inspect API logs for `NombaCheckoutError` |
| Redirect works but invoice stays `not_paid` | Webhook not reaching API | Register webhook URL in Nomba; use ngrok locally; check Render logs |
| Webhook 401 | Wrong `NOMBA_WEBHOOK_SECRET` | Re-copy signing secret from Nomba dashboard |
| Callback shows "pending" forever | Webhook delayed or failed | Check logs for `payment_success`; verify reference matches `rinse_inv_*` |
| Transaction ledger empty | Old Paystack bug (fixed) | Ensure you're on Nomba code path; pay init creates pending txn |
| CORS error on invoice page | Origin not allowed | Add dashboard URL to `CORS_ORIGINS` |
| Amount mismatch | Nomba sent Naira in webhook | Handler multiplies by 100 when value &lt; 1M — verify in sandbox logs |
| VA funded but not paid | `accountRef` mismatch | Reference must be `rinse_{invoice_no}`; check webhook payload |
| Double payment | User paid twice | Backend rejects if txn already `successful`; Nomba may still charge — handle support case |

**Debug logging:** Search Render/local logs for:

```
Nomba webhook received: event=payment_success
Invoice {id} marked paid
Order {id} payment_status=paid via Nomba
Duplicate payment_success for reference=... — ignoring
```

---

## 11. Remaining Work & Roadmap

### Backend gaps

| Item | Priority | Notes |
|------|----------|-------|
| Nomba refund API | Medium | Wire `POST /checkout/refund/{orderReference}` into `POST /transactions/:id/refund` |
| `PAYMENT_PROVIDER` switch | Low | Factory to support Paystack fallback |
| Webhook event log table | Low | Durable idempotency via `request_id` |
| Order auto-transition | Low | `pending` → `active` after payment in webhook |
| Multi-worker token cache | Low | Redis for OAuth token if scaling beyond 1 worker |
| Reconciliation job | Low | Nightly Nomba vs local ledger diff |

### Frontend gaps

| Item | Priority | Notes |
|------|----------|-------|
| Bank transfer UI | High | New tab + polling (Section 7.6) |
| Callback polling | High | Section 7.7 |
| Refund UX | Medium | Disable until Nomba refund wired |
| Payment notifications | Low | Toast/email when invoice paid (staff) |
| QR code for VA | Low | Optional — encode NUBAN for mobile banking apps |

### Documentation maintenance

When changing payment behavior, update:

1. This file (`PAYMENT_GATEWAY_IMPLEMENTATION.md`)
2. `NOMBA_INTEGRATION.md` (backend phases)
3. `BACKEND_SCOPE.md` Appendix C (API contract)
4. Dashboard `.env.example` and README

---

## Quick Reference — Key Files

### Backend (this repo)

| File | Role |
|------|------|
| `src/rinsehq/config.py` | Nomba env settings |
| `src/rinsehq/infrastructure/payments/nomba_client.py` | Nomba API client |
| `src/rinsehq/presentation/api/v1/invoices.py` | Pay, VA, webhook routes |
| `src/rinsehq/infrastructure/repositories/sqlalchemy_catalog_repository.py` | Ledger + invoice DB ops |
| `src/rinsehq/infrastructure/di.py` | `NombaClientDep` |
| `tests/test_nomba_payments.py` | Integration tests |
| `.env.example` | Env var template |

### Frontend (rinsehq-dashboard — separate repo)

| Area | Typical path |
|------|--------------|
| Public invoice page | `src/pages/invoice/` |
| API client | `src/lib/api/invoices.ts` |
| Router | `src/router.tsx` or `src/App.tsx` |
| Transactions | `src/pages/transactions/` |
| Order finalize | `src/pages/orders/` |

---

*End of PAYMENT_GATEWAY_IMPLEMENTATION.md*
