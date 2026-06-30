from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.application.dtos.order import CreateOrderDto, validate_create_order
from rinsehq.domain.entities.order import Order
from rinsehq.domain.repositories.order_repository import CreateOrderInput, OrderRepository


class CreateOrderUseCase:
    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    async def execute(self, dto: CreateOrderDto) -> Result[Order]:
        validated = validate_create_order(dto)
        if isinstance(validated, ErrorResult):
            return validated

        data = validated.data
        order = await self._order_repository.create(
            CreateOrderInput(
                type=data.type,
                customer=data.customer.strip(),
                amount_cents=data.amount_cents,
                status=data.status,
                order_date=data.order_date,
                delivery_date=data.delivery_date,
                delivery_mode=data.delivery_mode.strip(),
            )
        )
        return SuccessResult(order)
