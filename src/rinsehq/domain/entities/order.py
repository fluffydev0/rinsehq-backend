from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

OrderType = Literal["mobile_app", "offline"]
OrderStatus = Literal["active", "pending", "completed"]
PaymentStatus = Literal["paid", "not_paid"]


@dataclass(frozen=True)
class OrderLineItem:
    name: str
    quantity: int
    unit_price: int
    amount: int
    laundry_mode: str | None = None


@dataclass(frozen=True)
class Order:
    id: str
    store_id: str
    type: OrderType
    customer: str
    amount_cents: int
    status: OrderStatus
    order_date: datetime
    delivery_date: datetime
    delivery_mode: str
    created_at: datetime
    customer_email: str = ""
    customer_phone: str = ""
    customer_address: str = ""
    payment_status: PaymentStatus = "not_paid"
    payment_method: str = ""
    laundry_mode: str = ""
    service_type: str = ""
    pickup_date: str = ""
    pickup_time: str = ""
    delivery_time: str = ""
    description: str = ""
    subtotal: int = 0
    vat: int = 0
    discount: int = 0
    total: int = 0
    line_items: list[OrderLineItem] | None = None
    invoice_id: str | None = None
    invoice_no: str | None = None
