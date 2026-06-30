from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

TransactionType = Literal["payment", "refund"]
TransactionStatus = Literal["successful", "pending", "failed"]


@dataclass(frozen=True)
class Transaction:
    id: str
    reference: str
    order_id: str
    customer: str
    amount_cents: int
    type: TransactionType
    payment_method: str
    status: TransactionStatus
    date: datetime
    customer_email: str = ""
    customer_phone: str = ""
    description: str = ""
    fee_cents: int = 0
    net_amount_cents: int = 0
    channel: str = ""
    paid_at: datetime | None = None
