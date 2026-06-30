from fastapi import APIRouter

from rinsehq.presentation.api.v1 import auth, dashboard, health, orders

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(orders.router)
api_v1_router.include_router(dashboard.router)
