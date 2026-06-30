from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Union, Literal

from pydantic import BaseModel, Field

OrderTypeSchema = Literal["mobile_app", "offline"]
OrderStatusSchema = Literal["active", "pending", "completed"]


class OrderResponse(BaseModel):
    id: str
    type: OrderTypeSchema
    customer: str
    amount_cents: int
    amount_display: str
    status: OrderStatusSchema
    order_date: datetime
    delivery_date: datetime
    delivery_mode: str
    created_at: datetime


class CreateOrderRequest(BaseModel):
    type: OrderTypeSchema
    customer: str
    amount_cents: int = Field(gt=0)
    status: OrderStatusSchema = "pending"
    order_date: datetime
    delivery_date: datetime
    delivery_mode: str


class UpdateOrderRequest(BaseModel):
    type: Optional[OrderTypeSchema] = None
    customer: Optional[str] = None
    amount_cents: Optional[int] = Field(default=None, gt=0)
    status: Optional[OrderStatusSchema] = None
    order_date: Optional[datetime] = None
    delivery_date: Optional[datetime] = None
    delivery_mode: Optional[str] = None


class DashboardSummaryResponse(BaseModel):
    active: int
    pending: int
    completed: int


def format_amount(cents: int) -> str:
    major = cents // 100
    return f"N{major:,}"
