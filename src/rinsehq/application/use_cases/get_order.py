from __future__ import annotations

from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.application.dtos.order import UpdateOrderDto
from rinsehq.domain.entities.order import Order
from rinsehq.domain.repositories.order_repository import OrderRepository, UpdateOrderInput


ORDER_TYPE_MAP = {
    "pickup-delivery": "Pickup & Delivery",
    "drop-off": "Store Drop-off",
    "pickup-only": "Pickup only",
    "customer-rider": "Customer Rider",
    "delivery-only": "Delivery only",
}


class GetOrderUseCase:
    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    async def execute(self, order_id: str, store_id: str) -> Result[Order]:
        order = await self._order_repository.find_by_id(order_id, store_id)
        if not order:
            return ErrorResult("Order not found")
        return SuccessResult(order)


class UpdateOrderUseCase:
    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    async def execute(
        self, order_id: str, store_id: str, dto: UpdateOrderDto
    ) -> Result[Order]:
        order = await self._order_repository.find_by_id(order_id, store_id)
        if not order:
            return ErrorResult("Order not found")

        if order.status == "completed" or order.payment_status == "paid":
            return ErrorResult("Cannot update a completed or paid order")

        has_draft_fields = any(
            v is not None
            for v in (
                dto.customer_name,
                dto.customer_email,
                dto.customer_phone,
                dto.customer_address,
                dto.laundry_mode,
                dto.service_type,
                dto.order_type,
                dto.delivery_date,
                dto.pickup_date,
                dto.pickup_time,
                dto.delivery_time,
                dto.subtotal,
                dto.vat,
                dto.discount,
                dto.total,
                dto.line_items,
            )
        )
        if has_draft_fields and order.status != "draft":
            return ErrorResult("Only draft orders can be edited")

        delivery_mode = None
        if dto.order_type is not None:
            delivery_mode = ORDER_TYPE_MAP.get(dto.order_type, dto.order_type)

        amount_cents = dto.total if dto.total is not None else None

        order = await self._order_repository.update(
            order_id,
            UpdateOrderInput(
                status=dto.status,
                description=dto.description,
                customer=dto.customer_name,
                customer_email=dto.customer_email,
                customer_phone=dto.customer_phone,
                customer_address=dto.customer_address,
                laundry_mode=dto.laundry_mode,
                service_type=dto.service_type,
                delivery_mode=delivery_mode,
                delivery_date=dto.delivery_date,
                pickup_date=dto.pickup_date,
                pickup_time=dto.pickup_time,
                delivery_time=dto.delivery_time,
                subtotal=dto.subtotal,
                vat=dto.vat,
                discount=dto.discount,
                total=dto.total,
                amount_cents=amount_cents,
                line_items=dto.line_items,
            ),
            store_id,
        )
        if not order:
            return ErrorResult("Order not found")
        return SuccessResult(order)
