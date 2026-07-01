from rinsehq.application.services.order_pricing import compute_order_pricing
from rinsehq.domain.entities.order import OrderLineItem


def test_compute_order_pricing():
    items = [
        OrderLineItem(name="Wash", quantity=1, unit_price=100000, amount=100000),
        OrderLineItem(name="Fold", quantity=1, unit_price=50000, amount=50000),
    ]
    subtotal, vat, discount, total = compute_order_pricing(items, discount=10000, vat_rate_percent=7.5)
    assert subtotal == 150000
    assert vat == 11250
    assert discount == 10000
    assert total == 151250
