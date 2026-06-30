from __future__ import annotations

from rinsehq.domain.repositories.order_repository import OrderRepository, OrderSummary


class DashboardSummaryUseCase:
    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    async def execute(self, store_id: str) -> OrderSummary:
        return await self._order_repository.count_by_status(store_id)
