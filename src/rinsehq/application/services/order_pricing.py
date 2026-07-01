from __future__ import annotations

from rinsehq.domain.entities.order import OrderLineItem


def compute_order_pricing(
    line_items: list[OrderLineItem],
    discount: int = 0,
    vat_rate_percent: float = 7.5,
) -> tuple[int, int, int, int]:
    """Return (subtotal, vat, discount, total) in kobo."""
    subtotal = sum(li.amount for li in line_items)
    vat = round(subtotal * vat_rate_percent / 100)
    total = max(subtotal + vat - discount, 0)
    return subtotal, vat, discount, total
