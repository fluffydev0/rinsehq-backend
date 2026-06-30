from typing import List, Optional, Union
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from rinsehq.domain.entities.order import Order
from rinsehq.domain.repositories.order_repository import (
    CreateOrderInput,
    OrderFilters,
    OrderRepository,
    OrderSummary,
    UpdateOrderInput,
)
from rinsehq.infrastructure.db.models import OrderModel


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    async def list_orders(self, filters: Optional[OrderFilters] = None) -> List[Order]:
        stmt = select(OrderModel).order_by(OrderModel.created_at.desc())
        if filters:
            if filters.status:
                stmt = stmt.where(OrderModel.status == filters.status)
            if filters.search:
                term = f"%{filters.search}%"
                stmt = stmt.where(
                    or_(
                        OrderModel.customer.ilike(term),
                        OrderModel.id.ilike(term),
                        OrderModel.delivery_mode.ilike(term),
                    )
                )
        rows = self._session.scalars(stmt).all()
        return [self._to_entity(row) for row in rows]

    async def find_by_id(self, order_id: str) -> Optional[Order]:
        row = self._session.get(OrderModel, order_id)
        return self._to_entity(row) if row else None

    async def create(self, input: CreateOrderInput) -> Order:
        row = OrderModel(
            type=input.type,
            customer=input.customer,
            amount_cents=input.amount_cents,
            status=input.status,
            order_date=input.order_date,
            delivery_date=input.delivery_date,
            delivery_mode=input.delivery_mode,
        )
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    async def update(self, order_id: str, input: UpdateOrderInput) -> Optional[Order]:
        row = self._session.get(OrderModel, order_id)
        if not row:
            return None
        if input.type is not None:
            row.type = input.type
        if input.customer is not None:
            row.customer = input.customer
        if input.amount_cents is not None:
            row.amount_cents = input.amount_cents
        if input.status is not None:
            row.status = input.status
        if input.order_date is not None:
            row.order_date = input.order_date  # type: ignore[assignment]
        if input.delivery_date is not None:
            row.delivery_date = input.delivery_date  # type: ignore[assignment]
        if input.delivery_mode is not None:
            row.delivery_mode = input.delivery_mode
        self._session.flush()
        return self._to_entity(row)

    async def count_by_status(self) -> OrderSummary:
        rows = self._session.execute(
            select(OrderModel.status, func.count()).group_by(OrderModel.status)
        ).all()
        counts = {status: count for status, count in rows}
        return OrderSummary(
            active=counts.get("active", 0),
            pending=counts.get("pending", 0),
            completed=counts.get("completed", 0),
        )

    @staticmethod
    def _to_entity(row: OrderModel) -> Order:
        return Order(
            id=row.id,
            type=row.type,  # type: ignore[arg-type]
            customer=row.customer,
            amount_cents=row.amount_cents,
            status=row.status,  # type: ignore[arg-type]
            order_date=row.order_date,
            delivery_date=row.delivery_date,
            delivery_mode=row.delivery_mode,
            created_at=row.created_at,
        )
