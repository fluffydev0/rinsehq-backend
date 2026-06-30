from typing import List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.domain.entities.order import OrderStatus, OrderType


@dataclass(frozen=True)
class CreateOrderDto:
    type: OrderType
    customer: str
    amount_cents: int
    status: OrderStatus
    order_date: datetime
    delivery_date: datetime
    delivery_mode: str


@dataclass(frozen=True)
class UpdateOrderDto:
    type: Optional[OrderType] = None
    customer: Optional[str] = None
    amount_cents: Optional[int] = None
    status: Optional[OrderStatus] = None
    order_date: Optional[datetime] = None
    delivery_date: Optional[datetime] = None
    delivery_mode: Optional[str] = None


VALID_ORDER_TYPES = {"mobile_app", "offline"}
VALID_ORDER_STATUSES = {"active", "pending", "completed"}


def validate_create_order(dto: CreateOrderDto) -> Union[Result[CreateOrderDto], ErrorResult]:
    if dto.type not in VALID_ORDER_TYPES:
        return ErrorResult("Invalid order type")
    if not dto.customer.strip():
        return ErrorResult("Customer is required")
    if dto.amount_cents <= 0:
        return ErrorResult("Amount must be greater than zero")
    if dto.status not in VALID_ORDER_STATUSES:
        return ErrorResult("Invalid order status")
    if not dto.delivery_mode.strip():
        return ErrorResult("Delivery mode is required")
    return SuccessResult(dto)
