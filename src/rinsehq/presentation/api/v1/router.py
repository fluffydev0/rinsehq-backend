from __future__ import annotations

from fastapi import APIRouter

from rinsehq.presentation.api.v1 import (
    account,
    admins,
    auth,
    customers,
    dashboard,
    health,
    invoices,
    onboarding,
    orders,
    placeholders,
    services,
    stores,
    transactions,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(stores.router)
api_v1_router.include_router(onboarding.router)
api_v1_router.include_router(dashboard.router)
api_v1_router.include_router(orders.router)
api_v1_router.include_router(customers.router)
api_v1_router.include_router(invoices.router)
api_v1_router.include_router(invoices.webhook_router)
api_v1_router.include_router(transactions.router)
api_v1_router.include_router(services.router)
api_v1_router.include_router(account.router)
api_v1_router.include_router(admins.router)
api_v1_router.include_router(placeholders.router)
