from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class InvoiceLineItem:
    index: int
    laundry_mode: str
    items_label: str
    unit_price: int
    amount: int


@dataclass(frozen=True)
class Invoice:
    id: str
    business_name: str
    status: str
    invoice_no: str
    invoice_date: datetime
    payment_method: str
    subtotal: int
    vat: int
    discount: int
    total: int
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_address: str
    line_items: list[InvoiceLineItem]
    business_address: str = ""
    business_phone: str = ""
    business_whatsapp: str = ""
