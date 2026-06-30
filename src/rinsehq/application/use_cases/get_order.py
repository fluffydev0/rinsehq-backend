from __future__ import annotations

from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.domain.entities.order import Order
from rinsehq.domain.repositories.order_repository import OrderRepository, UpdateOrderInput


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

    async def execute(self, order_id: str, store_id: str, status: str | None, description: str | None) -> Result[Order]:
        order = await self._order_repository.update(
            order_id,
            UpdateOrderInput(status=status, description=description),  # type: ignore[arg-type]
            store_id,
        )
        if not order:
            return ErrorResult("Order not found")
        return SuccessResult(order)
