from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from rinsehq.application.dtos.order import CreateOrderDto, UpdateOrderDto
from rinsehq.application.use_cases.create_order import CreateOrderUseCase
from rinsehq.application.use_cases.finalize_order import FinalizeOrderUseCase
from rinsehq.application.use_cases.get_order import GetOrderUseCase, UpdateOrderUseCase
from rinsehq.application.use_cases.list_orders import ListOrdersUseCase
from rinsehq.config import get_settings
from rinsehq.domain.entities.order import OrderLineItem, OrderStatus
from rinsehq.infrastructure.di import (
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
    serviceId: Optional[str] = None
    name: str = ""
    quantity: int = 1
    unitPrice: int = 0
    amount: int = 0
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
    customer: Optional[CustomerRequest] = None
    laundryMode: Optional[str] = None
    serviceTypeId: Optional[str] = None
    lineItems: Optional[list[LineItemRequest]] = None
    orderType: Optional[str] = None
    pickup: Optional[PickupDeliveryRequest] = None
    delivery: Optional[PickupDeliveryRequest] = None
    subtotal: Optional[int] = None
    vat: Optional[int] = None
    discount: Optional[int] = None
    total: Optional[int] = None


def _parse_delivery_date(delivery: Optional[PickupDeliveryRequest], fallback: datetime) -> datetime:
    if delivery and delivery.date:
        try:
            return datetime.fromisoformat(delivery.date.replace("Z", "+00:00"))
        except ValueError:
            pass
    return fallback


def _line_items_from_request(items: list[LineItemRequest]) -> list[OrderLineItem]:
    return [
        OrderLineItem(
            name=li.name,
            quantity=li.quantity,
            unit_price=li.unitPrice,
            amount=li.amount,
            laundry_mode=li.laundryMode,
            service_id=li.serviceId,
        )
        for li in items
    ]


def _build_create_dto(body: CreateOrderRequest, now: datetime) -> CreateOrderDto:
    delivery_date = _parse_delivery_date(body.delivery, now)
    return CreateOrderDto(
        customer_name=body.customer.name,
        customer_email=body.customer.email,
        customer_phone=body.customer.phone,
        customer_address=body.customer.address,
        laundry_mode=body.laundryMode,
        service_type=body.serviceTypeId,
        order_type=body.orderType,
        type="offline",
        order_date=now,
        delivery_date=delivery_date,
        pickup_date=body.pickup.date if body.pickup else "",
        pickup_time=body.pickup.timeSlot if body.pickup else "",
        delivery_time=body.delivery.timeSlot if body.delivery else "",
        description=body.description,
        subtotal=body.subtotal,
        vat=body.vat,
        discount=body.discount,
        total=body.total or body.amount,
        line_items=_line_items_from_request(body.lineItems),
    )


def get_create_order_use_case(
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
) -> CreateOrderUseCase:
    return CreateOrderUseCase(order_repo, catalog_repo)


def get_finalize_order_use_case(
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
    billing_repo: Annotated[SqlAlchemyBillingRepository, Depends(get_billing_repository)],
) -> FinalizeOrderUseCase:
    return FinalizeOrderUseCase(order_repo, catalog_repo, billing_repo)


def get_update_order_use_case(
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
    catalog_repo: Annotated[SqlAlchemyCatalogRepository, Depends(get_catalog_repository)],
) -> UpdateOrderUseCase:
    return UpdateOrderUseCase(order_repo, catalog_repo)


def _payment_link_url(invoice_id: str) -> str:
    settings = get_settings()
    return f"{settings.app_base_url}/invoice/{invoice_id}"


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
    dto = _build_create_dto(body, now)
    order = unwrap_result(await use_case.execute(ctx.store_id, dto))
    return ApiResponse(
        data={
            "order": order_detail_to_response(order),
            "invoice": None,
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
    use_case: Annotated[UpdateOrderUseCase, Depends(get_update_order_use_case)],
) -> ApiResponse[dict]:
    now = datetime.utcnow()
    line_items = (
        _line_items_from_request(body.lineItems) if body.lineItems is not None else None
    )
    dto = UpdateOrderDto(
        status=body.status,
        description=body.description,
        customer_name=body.customer.name if body.customer else None,
        customer_email=body.customer.email if body.customer else None,
        customer_phone=body.customer.phone if body.customer else None,
        customer_address=body.customer.address if body.customer else None,
        laundry_mode=body.laundryMode,
        service_type=body.serviceTypeId,
        order_type=body.orderType,
        delivery_date=_parse_delivery_date(body.delivery, now) if body.delivery else None,
        pickup_date=body.pickup.date if body.pickup else None,
        pickup_time=body.pickup.timeSlot if body.pickup else None,
        delivery_time=body.delivery.timeSlot if body.delivery else None,
        subtotal=body.subtotal,
        vat=body.vat,
        discount=body.discount,
        total=body.total,
        line_items=line_items,
    )
    order = unwrap_result(
        await use_case.execute(order_id, ctx.store_id, dto),
        not_found=True,
    )
    return ApiResponse(data=order_detail_to_response(order))


@router.post("/{order_id}/finalize", status_code=status.HTTP_200_OK)
async def finalize_order(
    order_id: str,
    ctx: Annotated[SessionContext, Depends(require_permission("orders"))],
    use_case: Annotated[FinalizeOrderUseCase, Depends(get_finalize_order_use_case)],
) -> ApiResponse[dict]:
    result = await use_case.execute(order_id, ctx.store_id)
    order, invoice = unwrap_result(result)
    return ApiResponse(
        data={
            "order": order_detail_to_response(order),
            "invoice": invoice_to_response(invoice),
            "paymentLink": _payment_link_url(invoice.id),
        }
    )
