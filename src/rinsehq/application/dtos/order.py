from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.domain.entities.order import OrderLineItem, OrderStatus, OrderType


@dataclass(frozen=True)
class CreateOrderDto:
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_address: str
    laundry_mode: str
    service_type: str
    order_type: str
    type: OrderType
    order_date: datetime
    delivery_date: datetime
    pickup_date: str
    pickup_time: str
    delivery_time: str
    description: str
    subtotal: int
    vat: int
    discount: int
    total: int
    line_items: list[OrderLineItem]


@dataclass(frozen=True)
class UpdateOrderDto:
    status: Optional[OrderStatus] = None
    description: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    laundry_mode: Optional[str] = None
    service_type: Optional[str] = None
    order_type: Optional[str] = None
    delivery_date: Optional[datetime] = None
    pickup_date: Optional[str] = None
    pickup_time: Optional[str] = None
    delivery_time: Optional[str] = None
    subtotal: Optional[int] = None
    vat: Optional[int] = None
    discount: Optional[int] = None
    total: Optional[int] = None
    line_items: Optional[list[OrderLineItem]] = None


VALID_ORDER_TYPES = {"mobile_app", "offline"}


def validate_draft_order(dto: CreateOrderDto) -> Result[CreateOrderDto]:
    return SuccessResult(dto)


def validate_finalize_order(
    customer_name: str,
    line_items: list[OrderLineItem],
    total: int,
) -> Result[None]:
    if not customer_name.strip():
        return ErrorResult("Customer is required")
    if not line_items:
        return ErrorResult("At least one line item is required")
    if total <= 0:
        return ErrorResult("Amount must be greater than zero")
    return SuccessResult(None)
