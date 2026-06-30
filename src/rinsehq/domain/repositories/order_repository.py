from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from rinsehq.domain.entities.order import Order, OrderLineItem, OrderStatus, OrderType


@dataclass(frozen=True)
class CreateOrderInput:
    store_id: str
    type: OrderType
    customer: str
    amount_cents: int
    status: OrderStatus
    order_date: object
    delivery_date: object
    delivery_mode: str
    customer_email: str = ""
    customer_phone: str = ""
    customer_address: str = ""
    order_type: str = "offline"
    laundry_mode: str = ""
    service_type: str = ""
    payment_status: str = "not_paid"
    payment_method: str = ""
    pickup_date: str = ""
    pickup_time: str = ""
    delivery_time: str = ""
    description: str = ""
    subtotal: int = 0
    vat: int = 0
    discount: int = 0
    total: int = 0
    line_items: list[OrderLineItem] | None = None
    customer_id: str | None = None


@dataclass(frozen=True)
class UpdateOrderInput:
    status: Optional[OrderStatus] = None
    description: Optional[str] = None
    payment_status: Optional[str] = None


@dataclass(frozen=True)
class OrderFilters:
    store_id: str
    status: Optional[OrderStatus] = None
    search: Optional[str] = None
    page: int = 1
    limit: int = 20


@dataclass(frozen=True)
class OrderSummary:
    active: int
    pending: int
    completed: int


@dataclass(frozen=True)
class PaginatedOrders:
    items: list[Order]
    total: int
    page: int
    limit: int


class OrderRepository(Protocol):
    async def list_orders(self, filters: OrderFilters) -> PaginatedOrders: ...

    async def find_by_id(self, order_id: str, store_id: str | None = None) -> Optional[Order]: ...

    async def create(self, input: CreateOrderInput) -> Order: ...

    async def update(self, order_id: str, input: UpdateOrderInput, store_id: str) -> Optional[Order]: ...

    async def count_by_status(self, store_id: str) -> OrderSummary: ...

    async def recent_orders(self, store_id: str, limit: int) -> list[Order]: ...

    async def hourly_completed_today(self, store_id: str) -> list[int]: ...
