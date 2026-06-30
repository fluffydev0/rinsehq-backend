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


VALID_ORDER_TYPES = {"mobile_app", "offline"}


def validate_create_order(dto: CreateOrderDto) -> Result[CreateOrderDto]:
    if not dto.customer_name.strip():
        return ErrorResult("Customer is required")
    if dto.total <= 0:
        return ErrorResult("Amount must be greater than zero")
    return SuccessResult(dto)
