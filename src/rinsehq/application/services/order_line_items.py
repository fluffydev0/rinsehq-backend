from __future__ import annotations

from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.domain.entities.order import OrderLineItem
from rinsehq.domain.repositories.catalog_repository import CatalogRepository


async def resolve_order_line_items(
    catalog: CatalogRepository,
    store_id: str,
    items: list[OrderLineItem],
) -> Result[list[OrderLineItem]]:
    """Resolve catalog-backed line items and validate manual entries."""
    if not items:
        return ErrorResult("At least one line item is required")

    resolved: list[OrderLineItem] = []
    for index, item in enumerate(items, start=1):
        if item.service_id:
            service = await catalog.find_service(item.service_id, store_id)
            if not service:
                return ErrorResult(f"Service not found: {item.service_id}")
            if service.status != "active":
                return ErrorResult(f"Service is not active: {service.name}")
            if item.quantity <= 0:
                return ErrorResult(f"Quantity must be greater than zero for {service.name}")

            amount = service.unit_price * item.quantity
            resolved.append(
                OrderLineItem(
                    name=service.name,
                    quantity=item.quantity,
                    unit_price=service.unit_price,
                    amount=amount,
                    laundry_mode=item.laundry_mode or service.laundry_mode,
                    service_id=service.id,
                )
            )
            continue

        if not item.name.strip():
            return ErrorResult(f"Line item {index}: name is required when serviceId is omitted")
        if item.quantity <= 0:
            return ErrorResult(f"Line item {index}: quantity must be greater than zero")
        if item.unit_price < 0 or item.amount <= 0:
            return ErrorResult(f"Line item {index}: invalid price or amount")

        resolved.append(item)

    return SuccessResult(resolved)


def collect_service_ids(items: list[OrderLineItem]) -> list[str]:
    return [item.service_id for item in items if item.service_id]
