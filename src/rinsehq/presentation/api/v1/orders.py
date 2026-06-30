from typing import List, Optional, Union, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from rinsehq.application.dtos.common import ErrorResult
from rinsehq.application.dtos.order import CreateOrderDto, UpdateOrderDto
from rinsehq.application.use_cases.create_order import CreateOrderUseCase
from rinsehq.application.use_cases.get_order import GetOrderUseCase
from rinsehq.application.use_cases.list_orders import ListOrdersUseCase
from rinsehq.application.use_cases.update_order import UpdateOrderUseCase
from rinsehq.domain.entities.order import OrderStatus
from rinsehq.infrastructure.di import (
    CurrentUser,
    get_create_order_use_case,
    get_get_order_use_case,
    get_list_orders_use_case,
    get_update_order_use_case,
)
from rinsehq.presentation.schemas.mappers import order_to_response
from rinsehq.presentation.schemas.order import (
    CreateOrderRequest,
    OrderResponse,
    UpdateOrderRequest,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=List[OrderResponse])
async def list_orders(
    _current_user: CurrentUser,
    use_case: Annotated[ListOrdersUseCase, Depends(get_list_orders_use_case)],
    status_filter: Annotated[Optional[OrderStatus], Query(alias="status")] = None,
    search: Optional[str] = None,
) -> List[OrderResponse]:
    orders = await use_case.execute(status=status_filter, search=search)
    return [order_to_response(order) for order in orders]


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: CreateOrderRequest,
    _current_user: CurrentUser,
    use_case: Annotated[CreateOrderUseCase, Depends(get_create_order_use_case)],
) -> OrderResponse:
    result = await use_case.execute(
        CreateOrderDto(
            type=body.type,
            customer=body.customer,
            amount_cents=body.amount_cents,
            status=body.status,
            order_date=body.order_date,
            delivery_date=body.delivery_date,
            delivery_mode=body.delivery_mode,
        )
    )
    if isinstance(result, ErrorResult):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error)
    return order_to_response(result.data)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    _current_user: CurrentUser,
    use_case: Annotated[GetOrderUseCase, Depends(get_get_order_use_case)],
) -> OrderResponse:
    result = await use_case.execute(order_id)
    if isinstance(result, ErrorResult):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.error)
    return order_to_response(result.data)


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str,
    body: UpdateOrderRequest,
    _current_user: CurrentUser,
    use_case: Annotated[UpdateOrderUseCase, Depends(get_update_order_use_case)],
) -> OrderResponse:
    result = await use_case.execute(
        order_id,
        UpdateOrderDto(
            type=body.type,
            customer=body.customer,
            amount_cents=body.amount_cents,
            status=body.status,
            order_date=body.order_date,
            delivery_date=body.delivery_date,
            delivery_mode=body.delivery_mode,
        ),
    )
    if isinstance(result, ErrorResult):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.error)
    return order_to_response(result.data)
