from __future__ import annotations

from rinsehq.application.dtos.order import CreateOrderDto, UpdateOrderDto, validate_create_order
from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.domain.entities.order import Order
from rinsehq.domain.repositories.catalog_repository import CatalogRepository
from rinsehq.domain.repositories.order_repository import CreateOrderInput, OrderRepository
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import SqlAlchemyBillingRepository


ORDER_TYPE_MAP = {
    "pickup-delivery": "Pickup & Delivery",
    "drop-off": "Store Drop-off",
    "pickup-only": "Pickup only",
    "customer-rider": "Customer Rider",
    "delivery-only": "Delivery only",
}


class CreateOrderUseCase:
    def __init__(
        self,
        order_repository: OrderRepository,
        catalog_repository: CatalogRepository,
        billing_repository: SqlAlchemyBillingRepository,
    ) -> None:
        self._orders = order_repository
        self._catalog = catalog_repository
        self._billing = billing_repository

    async def execute(self, store_id: str, dto: CreateOrderDto) -> Result[tuple[Order, object]]:
        validated = validate_create_order(dto)
        if isinstance(validated, ErrorResult):
            return validated
        data = validated.data
        customer = await self._catalog.upsert_customer(
            store_id,
            data.customer_name,
            data.customer_email,
            data.customer_phone,
            data.customer_address,
        )
        delivery_mode = ORDER_TYPE_MAP.get(data.order_type, data.order_type)
        order = await self._orders.create(
            CreateOrderInput(
                store_id=store_id,
                type=data.type,
                customer=data.customer_name,
                amount_cents=data.total,
                status="pending",
                order_date=data.order_date,
                delivery_date=data.delivery_date,
                delivery_mode=delivery_mode,
                customer_email=data.customer_email,
                customer_phone=data.customer_phone,
                customer_address=data.customer_address,
                order_type=data.order_type,
                laundry_mode=data.laundry_mode,
                service_type=data.service_type,
                pickup_date=data.pickup_date,
                pickup_time=data.pickup_time,
                delivery_time=data.delivery_time,
                description=data.description,
                subtotal=data.subtotal,
                vat=data.vat,
                discount=data.discount,
                total=data.total,
                line_items=data.line_items,
                customer_id=customer.id,
            )
        )
        invoice = await self._billing.create_invoice_for_order(order.id, store_id)
        refreshed = await self._orders.find_by_id(order.id, store_id)
        return SuccessResult((refreshed or order, invoice))
