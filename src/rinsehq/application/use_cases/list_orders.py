from __future__ import annotations

from typing import Optional

from rinsehq.domain.entities.order import Order, OrderStatus
from rinsehq.domain.repositories.order_repository import OrderFilters, OrderRepository, PaginatedOrders


class ListOrdersUseCase:
    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    async def execute(
        self,
        store_id: str,
        status: Optional[OrderStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> PaginatedOrders:
        return await self._order_repository.list_orders(
            OrderFilters(
                store_id=store_id,
                status=status,
                search=search,
                page=page,
                limit=limit,
            )
        )
