from rinsehq.domain.entities.order import Order
from rinsehq.domain.entities.user import User
from rinsehq.presentation.schemas.auth import UserResponse
from rinsehq.presentation.schemas.order import OrderResponse, format_amount


def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
    )


def order_to_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        type=order.type,
        customer=order.customer,
        amount_cents=order.amount_cents,
        amount_display=format_amount(order.amount_cents),
        status=order.status,
        order_date=order.order_date,
        delivery_date=order.delivery_date,
        delivery_mode=order.delivery_mode,
        created_at=order.created_at,
    )
