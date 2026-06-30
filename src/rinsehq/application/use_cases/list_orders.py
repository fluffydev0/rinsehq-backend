from typing import List, Optional, Union
from rinsehq.domain.entities.order import Order
from rinsehq.domain.repositories.order_repository import OrderFilters, OrderRepository


class ListOrdersUseCase:
    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    async def execute(
        self,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Order]:
        filters = OrderFilters(
            status=status,  # type: ignore[arg-type]
            search=search.strip() if search else None,
        )
        return await self._order_repository.list_orders(filters)
