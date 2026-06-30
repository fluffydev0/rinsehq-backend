from dataclasses import dataclass
from typing import List, Optional, Union, Protocol

from rinsehq.domain.entities.order import Order, OrderStatus, OrderType


@dataclass(frozen=True)
class CreateOrderInput:
    type: OrderType
    customer: str
    amount_cents: int
    status: OrderStatus
    order_date: object
    delivery_date: object
    delivery_mode: str


@dataclass(frozen=True)
class UpdateOrderInput:
    type: Optional[OrderType] = None
    customer: Optional[str] = None
    amount_cents: Optional[int] = None
    status: Optional[OrderStatus] = None
    order_date: Optional[object] = None
    delivery_date: Optional[object] = None
    delivery_mode: Optional[str] = None


@dataclass(frozen=True)
class OrderFilters:
    status: Optional[OrderStatus] = None
    search: Optional[str] = None


@dataclass(frozen=True)
class OrderSummary:
    active: int
    pending: int
    completed: int


class OrderRepository(Protocol):
    async def list_orders(self, filters: Optional[OrderFilters] = None) -> List[Order]: ...

    async def find_by_id(self, order_id: str) -> Optional[Order]: ...

    async def create(self, input: CreateOrderInput) -> Order: ...

    async def update(self, order_id: str, input: UpdateOrderInput) -> Optional[Order]: ...

    async def count_by_status(self) -> OrderSummary: ...
