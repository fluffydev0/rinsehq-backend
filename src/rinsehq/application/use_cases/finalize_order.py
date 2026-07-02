from __future__ import annotations

from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.application.dtos.order import validate_finalize_order
from rinsehq.application.services.order_line_items import collect_service_ids
from rinsehq.application.services.order_pricing import compute_order_pricing
from rinsehq.config import get_settings
from rinsehq.domain.entities.invoice import Invoice
from rinsehq.domain.entities.order import Order
from rinsehq.domain.repositories.catalog_repository import CatalogRepository
from rinsehq.domain.repositories.order_repository import OrderRepository, UpdateOrderInput
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import SqlAlchemyBillingRepository


class FinalizeOrderUseCase:
    def __init__(
        self,
        order_repository: OrderRepository,
        catalog_repository: CatalogRepository,
        billing_repository: SqlAlchemyBillingRepository,
    ) -> None:
        self._orders = order_repository
        self._catalog = catalog_repository
        self._billing = billing_repository

    async def execute(self, order_id: str, store_id: str) -> Result[tuple[Order, Invoice]]:
        order = await self._orders.find_by_id(order_id, store_id)
        if not order:
            return ErrorResult("Order not found")
        if order.status != "draft":
            return ErrorResult("Only draft orders can be finalized")
        if order.invoice_id:
            return ErrorResult("Order already has an invoice")

        line_items = order.line_items or []
        settings = get_settings()
        subtotal, vat, discount, total = compute_order_pricing(
            line_items,
            discount=order.discount,
            vat_rate_percent=settings.default_vat_rate_percent,
        )

        validated = validate_finalize_order(order.customer, line_items, total)
        if isinstance(validated, ErrorResult):
            return validated

        if order.customer_email.strip():
            await self._catalog.upsert_customer(
                store_id,
                order.customer,
                order.customer_email,
                order.customer_phone,
                order.customer_address,
            )

        updated = await self._orders.update(
            order_id,
            UpdateOrderInput(
                status="pending",
                subtotal=subtotal,
                vat=vat,
                discount=discount,
                total=total,
                amount_cents=total,
            ),
            store_id,
        )
        if not updated:
            return ErrorResult("Order not found")

        invoice = await self._billing.create_invoice_for_order(order_id, store_id)
        await self._catalog.increment_service_orders_count(
            store_id,
            collect_service_ids(line_items),
        )
        refreshed = await self._orders.find_by_id(order_id, store_id)
        return SuccessResult((refreshed or updated, invoice))
