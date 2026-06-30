from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from rinsehq.application.use_cases.dashboard_summary import DashboardSummaryUseCase
from rinsehq.application.use_cases.list_orders import ListOrdersUseCase
from rinsehq.infrastructure.di import CurrentSession, get_order_repository
from rinsehq.infrastructure.repositories.sqlalchemy_order_repository import SqlAlchemyOrderRepository
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import SqlAlchemyBillingRepository
from rinsehq.infrastructure.di import get_billing_repository
from rinsehq.presentation.schemas.envelope import ApiResponse
from rinsehq.presentation.schemas.mappers import order_row_to_response

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

TIME_LABELS = [
    "09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM",
    "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM",
]


@router.get("/summary")
async def dashboard_summary(
    ctx: CurrentSession,
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
) -> ApiResponse[dict]:
    use_case = DashboardSummaryUseCase(order_repo)
    summary = await use_case.execute(ctx.store_id)
    return ApiResponse(
        data={
            "activeOrders": summary.active,
            "completedOrders": summary.completed,
            "pendingOrders": summary.pending,
        }
    )


@router.get("/chart/completed-orders")
async def completed_chart(
    ctx: CurrentSession,
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
) -> ApiResponse[dict]:
    hours = await order_repo.hourly_completed_today(ctx.store_id)
    points = [{"x": i, "y": y} for i, y in enumerate(hours)]
    return ApiResponse(data={"points": points, "timeLabels": TIME_LABELS})


@router.get("/revenue")
async def revenue(
    ctx: CurrentSession,
    billing_repo: Annotated[SqlAlchemyBillingRepository, Depends(get_billing_repository)],
) -> ApiResponse[dict]:
    data = await billing_repo.revenue_summary(ctx.store_id)
    return ApiResponse(data=data)


@router.get("/recent-orders")
async def recent_orders(
    ctx: CurrentSession,
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
    limit: int = Query(5, ge=1, le=50),
) -> ApiResponse[list]:
    orders = await order_repo.recent_orders(ctx.store_id, limit)
    return ApiResponse(data=[order_row_to_response(o) for o in orders])
