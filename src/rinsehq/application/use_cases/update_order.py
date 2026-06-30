from __future__ import annotations

from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.application.dtos.order import UpdateOrderDto
from rinsehq.domain.entities.order import Order
from rinsehq.domain.repositories.order_repository import OrderRepository, UpdateOrderInput


class UpdateOrderUseCase:
    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    async def execute(self, order_id: str, dto: UpdateOrderDto) -> Result[Order]:
        order = await self._order_repository.update(
            order_id,
            UpdateOrderInput(
                type=dto.type,
                customer=dto.customer,
                amount_cents=dto.amount_cents,
                status=dto.status,
                order_date=dto.order_date,
                delivery_date=dto.delivery_date,
                delivery_mode=dto.delivery_mode,
            ),
        )
        if not order:
            return ErrorResult("Order not found")
        return SuccessResult(order)
