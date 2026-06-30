from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from rinsehq.application.dtos.order import CreateOrderDto
from rinsehq.application.use_cases.create_order import CreateOrderUseCase
from rinsehq.application.use_cases.get_order import GetOrderUseCase, UpdateOrderUseCase
from rinsehq.application.use_cases.list_orders import ListOrdersUseCase
from rinsehq.domain.entities.order import OrderLineItem, OrderStatus
from rinsehq.infrastructure.di import (
    CurrentSession,
    get_billing_repository,
    get_catalog_repository,
    get_order_repository,
    require_permission,
)
from rinsehq.infrastructure.auth.context import SessionContext
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import (
    SqlAlchemyBillingRepository,
    SqlAlchemyCatalogRepository,
)
from rinsehq.infrastructure.repositories.sqlalchemy_order_repository import SqlAlchemyOrderRepository
from rinsehq.presentation.helpers import unwrap_result
from rinsehq.presentation.schemas.envelope import ApiResponse, PaginationMeta
from rinsehq.presentation.schemas.mappers import invoice_to_response, order_detail_to_response, order_row_to_response

router = APIRouter(prefix="/orders", tags=["orders"])


class LineItemRequest(BaseModel):
    name: str
    quantity: int
    unitPrice: int
    amount: int
    laundryMode: Optional[str] = None


class CustomerRequest(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    address: str = ""


class PickupDeliveryRequest(BaseModel):
    date: str
    timeSlot: str


class CreateOrderRequest(BaseModel):
    storeId: Optional[str] = None
    customer: CustomerRequest
    laundryMode: str = ""
    serviceTypeId: str = ""
    lineItems: list[LineItemRequest] = Field(default_factory=list)
    orderType: str = "offline"
    amount: int = 0
    pickup: Optional[PickupDeliveryRequest] = None
    delivery: Optional[PickupDeliveryRequest] = None
    description: str = ""
    subtotal: int = 0
    vat: int = 0
    discount: int = 0
    total: int = 0


class UpdateOrderRequest(BaseModel):
    status: Optional[OrderStatus] = None
    description: Optional[str] = None


def get_create_order_use_case(
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
    billing_repo: Annotated[SqlAlchemyBillingRepository, Depends(get_billing_repository)],
) -> CreateOrderUseCase:
    return CreateOrderUseCase(order_repo, catalog_repo, billing_repo)


@router.get("")
async def list_orders(
    ctx: Annotated[SessionContext, Depends(require_permission("orders"))],
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
    status_filter: Annotated[Optional[OrderStatus], Query(alias="status")] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> ApiResponse[list]:
    use_case = ListOrdersUseCase(order_repo)
    result = await use_case.execute(ctx.store_id, status_filter, search, page, limit)
    return ApiResponse(
        data=[order_row_to_response(o) for o in result.items],
        meta=PaginationMeta(total=result.total, page=result.page, limit=result.limit),  # type: ignore[call-arg]
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(
    body: CreateOrderRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("orders"))],
    use_case: Annotated[CreateOrderUseCase, Depends(get_create_order_use_case)],
) -> ApiResponse[dict]:
    now = datetime.utcnow()
    line_items = [
        OrderLineItem(
            name=li.name,
            quantity=li.quantity,
            unit_price=li.unitPrice,
            amount=li.amount,
            laundry_mode=li.laundryMode,
        )
        for li in body.lineItems
    ]
    dto = CreateOrderDto(
        customer_name=body.customer.name,
        customer_email=body.customer.email,
        customer_phone=body.customer.phone,
        customer_address=body.customer.address,
        laundry_mode=body.laundryMode,
        service_type=body.serviceTypeId,
        order_type=body.orderType,
        type="offline",
        order_date=now,
        delivery_date=now,
        pickup_date=body.pickup.date if body.pickup else "",
        pickup_time=body.pickup.timeSlot if body.pickup else "",
        delivery_time=body.delivery.timeSlot if body.delivery else "",
        description=body.description,
        subtotal=body.subtotal,
        vat=body.vat,
        discount=body.discount,
        total=body.total or body.amount,
        line_items=line_items,
    )
    result = await use_case.execute(ctx.store_id, dto)
    order, invoice = unwrap_result(result)
    return ApiResponse(
        data={
            "order": order_detail_to_response(order),
            "invoice": invoice_to_response(invoice),
        }
    )


@router.get("/{order_id}")
async def get_order(
    order_id: str,
    ctx: Annotated[SessionContext, Depends(require_permission("orders"))],
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
) -> ApiResponse[dict]:
    use_case = GetOrderUseCase(order_repo)
    order = unwrap_result(await use_case.execute(order_id, ctx.store_id), not_found=True)
    return ApiResponse(data=order_detail_to_response(order))


@router.patch("/{order_id}")
async def update_order(
    order_id: str,
    body: UpdateOrderRequest,
    ctx: Annotated[SessionContext, Depends(require_permission("orders"))],
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
) -> ApiResponse[dict]:
    use_case = UpdateOrderUseCase(order_repo)
    order = unwrap_result(
        await use_case.execute(order_id, ctx.store_id, body.status, body.description),
        not_found=True,
    )
    return ApiResponse(data=order_detail_to_response(order))
