from dataclasses import dataclass
from datetime import datetime
from typing import Literal

OrderType = Literal["mobile_app", "offline"]
OrderStatus = Literal["active", "pending", "completed"]


@dataclass(frozen=True)
class Order:
    id: str
    type: OrderType
    customer: str
    amount_cents: int
    status: OrderStatus
    order_date: datetime
    delivery_date: datetime
    delivery_mode: str
    created_at: datetime
