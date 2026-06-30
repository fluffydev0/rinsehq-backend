from datetime import datetime, timezone

from sqlalchemy import func, select

from rinsehq.domain.repositories.auth_repository import CreateUserInput
from rinsehq.domain.repositories.order_repository import CreateOrderInput
from rinsehq.infrastructure.db.models import OrderModel, UserModel
from rinsehq.infrastructure.db.session import get_session_factory
from rinsehq.infrastructure.repositories.sqlalchemy_auth_repository import SqlAlchemyAuthRepository
from rinsehq.infrastructure.repositories.sqlalchemy_order_repository import (
    SqlAlchemyOrderRepository,
)

DEMO_EMAIL = "demo@rinsehq.com"
DEMO_PASSWORD = "Demo1234!"
DEMO_NAME = "Laundry Care"

SAMPLE_ORDERS = [
    {
        "type": "mobile_app",
        "customer": "Olayiwola, Samuel",
        "amount_cents": 1_500_000,
        "status": "active",
        "delivery_mode": "Pickup & delivery",
    },
    {
        "type": "offline",
        "customer": "Olayiwola, Samuel",
        "amount_cents": 1_500_000,
        "status": "pending",
        "delivery_mode": "Customer rider",
    },
    {
        "type": "mobile_app",
        "customer": "Olayiwola, Samuel",
        "amount_cents": 1_500_000,
        "status": "completed",
        "delivery_mode": "Pickup only",
    },
]


async def seed_demo_data() -> None:
    session = get_session_factory()()
    try:
        auth_repo = SqlAlchemyAuthRepository(session)
        order_repo = SqlAlchemyOrderRepository(session)

        existing = session.scalar(select(UserModel).where(UserModel.email == DEMO_EMAIL))
        if not existing:
            await auth_repo.create(
                CreateUserInput(email=DEMO_EMAIL, password=DEMO_PASSWORD, name=DEMO_NAME)
            )

        order_count = session.scalar(select(func.count()).select_from(OrderModel)) or 0
        if order_count > 0:
            session.commit()
            return

        now = datetime.now(timezone.utc)
        for sample in SAMPLE_ORDERS:
            await order_repo.create(
                CreateOrderInput(
                    type=sample["type"],  # type: ignore[arg-type]
                    customer=sample["customer"],
                    amount_cents=sample["amount_cents"],
                    status=sample["status"],  # type: ignore[arg-type]
                    order_date=now,
                    delivery_date=now,
                    delivery_mode=sample["delivery_mode"],
                )
            )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
