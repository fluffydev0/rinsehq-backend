from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from rinsehq.domain.entities.order import Order, OrderLineItem
from rinsehq.domain.repositories.order_repository import (
    CreateOrderInput,
    OrderFilters,
    OrderRepository,
    OrderSummary,
    PaginatedOrders,
    UpdateOrderInput,
)
from rinsehq.infrastructure.db.models import InvoiceModel, OrderLineItemModel, OrderModel


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    async def list_orders(self, filters: OrderFilters) -> PaginatedOrders:
        stmt = (
            select(OrderModel)
            .where(OrderModel.store_id == filters.store_id)
            .options(selectinload(OrderModel.line_items), selectinload(OrderModel.invoice))
            .order_by(OrderModel.created_at.desc())
        )
        if filters.status:
            stmt = stmt.where(OrderModel.status == filters.status)
        if filters.search:
            term = f"%{filters.search}%"
            stmt = stmt.where(
                or_(OrderModel.customer.ilike(term), OrderModel.id.ilike(term))
            )
        total = self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        offset = (filters.page - 1) * filters.limit
        rows = self._session.scalars(stmt.offset(offset).limit(filters.limit)).all()
        return PaginatedOrders(
            items=[self._to_entity(r) for r in rows],
            total=total,
            page=filters.page,
            limit=filters.limit,
        )

    async def find_by_id(self, order_id: str, store_id: str | None = None) -> Optional[Order]:
        stmt = (
            select(OrderModel)
            .where(OrderModel.id == order_id)
            .options(selectinload(OrderModel.line_items), selectinload(OrderModel.invoice))
        )
        if store_id:
            stmt = stmt.where(OrderModel.store_id == store_id)
        row = self._session.scalar(stmt)
        return self._to_entity(row) if row else None

    async def create(self, input: CreateOrderInput) -> Order:
        row = OrderModel(
            store_id=input.store_id,
            customer_id=input.customer_id,
            type=input.type,
            customer=input.customer,
            amount_cents=input.amount_cents,
            status=input.status,
            order_date=input.order_date,  # type: ignore[arg-type]
            delivery_date=input.delivery_date,  # type: ignore[arg-type]
            delivery_mode=input.delivery_mode,
            customer_email=input.customer_email,
            customer_phone=input.customer_phone,
            customer_address=input.customer_address,
            order_type=input.order_type,
            laundry_mode=input.laundry_mode,
            service_type=input.service_type,
            payment_status=input.payment_status,
            payment_method=input.payment_method,
            pickup_date=input.pickup_date,
            pickup_time=input.pickup_time,
            delivery_time=input.delivery_time,
            description=input.description,
            subtotal=input.subtotal,
            vat=input.vat,
            discount=input.discount,
            total=input.total,
        )
        self._session.add(row)
        self._session.flush()
        if input.line_items:
            for item in input.line_items:
                self._session.add(
                    OrderLineItemModel(
                        order_id=row.id,
                        name=item.name,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        amount=item.amount,
                        laundry_mode=item.laundry_mode,
                    )
                )
            self._session.flush()
        self._session.refresh(row)
        return self._to_entity(row)

    async def update(
        self, order_id: str, input: UpdateOrderInput, store_id: str
    ) -> Optional[Order]:
        row = self._session.scalar(
            select(OrderModel)
            .where(OrderModel.id == order_id, OrderModel.store_id == store_id)
            .options(selectinload(OrderModel.line_items), selectinload(OrderModel.invoice))
        )
        if not row:
            return None
        if input.status is not None:
            row.status = input.status
        if input.description is not None:
            row.description = input.description
        if input.payment_status is not None:
            row.payment_status = input.payment_status
        self._session.flush()
        return self._to_entity(row)

    async def count_by_status(self, store_id: str) -> OrderSummary:
        rows = self._session.execute(
            select(OrderModel.status, func.count())
            .where(OrderModel.store_id == store_id)
            .group_by(OrderModel.status)
        ).all()
        counts = {status: count for status, count in rows}
        return OrderSummary(
            active=counts.get("active", 0),
            pending=counts.get("pending", 0),
            completed=counts.get("completed", 0),
        )

    async def recent_orders(self, store_id: str, limit: int) -> list[Order]:
        rows = self._session.scalars(
            select(OrderModel)
            .where(OrderModel.store_id == store_id)
            .options(selectinload(OrderModel.line_items), selectinload(OrderModel.invoice))
            .order_by(OrderModel.created_at.desc())
            .limit(limit)
        ).all()
        return [self._to_entity(r) for r in rows]

    async def hourly_completed_today(self, store_id: str) -> list[int]:
        today = datetime.now(timezone.utc).date()
        rows = self._session.scalars(
            select(OrderModel).where(
                OrderModel.store_id == store_id,
                OrderModel.status == "completed",
            )
        ).all()
        hours = [0] * 9
        for row in rows:
            if row.order_date.date() == today:
                hour = row.order_date.hour
                idx = max(0, min(8, hour - 9))
                hours[idx] += 1
        return hours

    @staticmethod
    def _to_entity(row: OrderModel) -> Order:
        line_items = None
        if row.line_items:
            line_items = [
                OrderLineItem(
                    name=li.name,
                    quantity=li.quantity,
                    unit_price=li.unit_price,
                    amount=li.amount,
                    laundry_mode=li.laundry_mode,
                )
                for li in row.line_items
            ]
        invoice_id = None
        invoice_no = None
        if row.invoice:
            invoice_id = row.invoice.id
            invoice_no = row.invoice.invoice_no
        return Order(
            id=row.id,
            store_id=row.store_id,
            type=row.type,  # type: ignore[arg-type]
            customer=row.customer,
            amount_cents=row.amount_cents,
            status=row.status,  # type: ignore[arg-type]
            order_date=row.order_date,
            delivery_date=row.delivery_date,
            delivery_mode=row.delivery_mode,
            created_at=row.created_at,
            customer_email=row.customer_email,
            customer_phone=row.customer_phone,
            customer_address=row.customer_address,
            payment_status=row.payment_status,  # type: ignore[arg-type]
            payment_method=row.payment_method,
            laundry_mode=row.laundry_mode,
            service_type=row.service_type,
            pickup_date=row.pickup_date,
            pickup_time=row.pickup_time,
            delivery_time=row.delivery_time,
            description=row.description,
            subtotal=row.subtotal,
            vat=row.vat,
            discount=row.discount,
            total=row.total,
            line_items=line_items,
            invoice_id=invoice_id,
            invoice_no=invoice_no,
        )
