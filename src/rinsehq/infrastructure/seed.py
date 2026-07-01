from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from rinsehq.domain.entities.order import OrderLineItem
from rinsehq.domain.entities.service import ConfigItem, ServicesConfiguration
from rinsehq.domain.repositories.auth_repository import CreateUserInput
from rinsehq.domain.repositories.order_repository import CreateOrderInput
from rinsehq.domain.repositories.store_repository import CreateAssignmentInput, CreateStoreInput
from rinsehq.infrastructure.db.models import (
    BusinessProfileModel,
    CustomerModel,
    IdSequenceModel,
    InvoiceLineItemModel,
    InvoiceModel,
    OrderLineItemModel,
    OrderModel,
    ServiceConfigModel,
    ServiceModel,
    StoreAssignmentModel,
    StoreModel,
    TransactionModel,
    UserModel,
    VerificationCodeModel,
    PasswordResetCodeModel,
)
from rinsehq.infrastructure.db.session import get_session_factory
from rinsehq.infrastructure.repositories.sqlalchemy_auth_repository import SqlAlchemyAuthRepository
from rinsehq.infrastructure.repositories.sqlalchemy_catalog_repository import (
    DEFAULT_CONFIG,
    SqlAlchemyBillingRepository,
    SqlAlchemyCatalogRepository,
)
from rinsehq.infrastructure.repositories.sqlalchemy_order_repository import SqlAlchemyOrderRepository
from rinsehq.infrastructure.repositories.sqlalchemy_store_repository import SqlAlchemyStoreRepository

DEMO_PASSWORD = "Demo1234!"

DEMO_USERS = [
    {
        "email": "demo@rinsehq.com",
        "name": "Adeola Johnson",
        "phone": "+2348012345678",
        "email_verified": True,
        "onboarding_completed": True,
    },
    {
        "email": "chioma@laundrycare.ng",
        "name": "Chioma Okafor",
        "phone": "+2348023456781",
        "email_verified": True,
        "onboarding_completed": True,
    },
    {
        "email": "emeka@laundrycare.ng",
        "name": "Emeka Nwosu",
        "phone": "+2348034567892",
        "email_verified": True,
        "onboarding_completed": True,
    },
    {
        "email": "fatima@laundrycare.ng",
        "name": "Fatima Bello",
        "phone": "+2348045678903",
        "email_verified": True,
        "onboarding_completed": True,
    },
]

DEMO_STORES = [
    {
        "id": "STR-001",
        "name": "Laundry Care — Main Store",
        "address": "12 Admiralty Way",
        "city": "Lekki",
        "phone": "+2348012345678",
        "is_main_store": True,
    },
    {
        "id": "STR-002",
        "name": "Laundry Care — Lekki Branch",
        "address": "15 Admiralty Way",
        "city": "Lekki",
        "phone": "+2348023456789",
        "is_main_store": False,
    },
    {
        "id": "STR-003",
        "name": "Laundry Care — Ikeja Branch",
        "address": "18 Allen Avenue",
        "city": "Ikeja",
        "phone": "+2348034567890",
        "is_main_store": False,
    },
]

ASSIGNMENTS = [
    ("chioma@laundrycare.ng", "STR-002", "manager", "manager"),
    ("chioma@laundrycare.ng", "STR-003", "manager", "manager"),
    ("emeka@laundrycare.ng", "STR-003", "sub_admin", "staff"),
    ("fatima@laundrycare.ng", "STR-001", "sub_admin", "viewer"),
    ("fatima@laundrycare.ng", "STR-002", "sub_admin", "viewer"),
]

DEMO_CUSTOMERS = [
    {
        "store_id": "STR-001",
        "name": "Collin Chukwuemeka Abraham",
        "email": "kollinchukwu12@gmail.com",
        "phone": "+23481090445567",
        "address": "House 25, Apt 5 blk7 Ogudu G.R.A Lagos",
    },
    {
        "store_id": "STR-001",
        "name": "Jane Doe",
        "email": "jane@email.com",
        "phone": "+2348011111111",
        "address": "14 Victoria Island, Lagos",
    },
    {
        "store_id": "STR-002",
        "name": "Olayiwola Samuel",
        "email": "samuel@email.com",
        "phone": "+2348022222222",
        "address": "22 Chevron Drive, Lekki",
    },
    {
        "store_id": "STR-003",
        "name": "Amaka Eze",
        "email": "amaka@email.com",
        "phone": "+2348033333333",
        "address": "5 Allen Avenue, Ikeja",
    },
]

DEMO_ORDERS = [
    {
        "store_id": "STR-001",
        "customer_key": "Collin Chukwuemeka Abraham",
        "type": "offline",
        "status": "active",
        "delivery_mode": "Pickup & Delivery",
        "payment_status": "paid",
        "payment_method": "Paystack",
        "amount_cents": 430000,
        "total": 430000,
        "subtotal": 455000,
        "vat": 25000,
        "discount": 50000,
        "laundry_mode": "Wash system",
        "line_items": [
            OrderLineItem(name="Wash Only", quantity=1, unit_price=200000, amount=200000, laundry_mode="Wash system"),
            OrderLineItem(name="Fold", quantity=1, unit_price=150000, amount=150000, laundry_mode="Wash system"),
        ],
        "create_txn": True,
        "txn_status": "successful",
        "txn_ref": "pay_a8f2k9m1x7",
    },
    {
        "store_id": "STR-001",
        "customer_key": "Jane Doe",
        "type": "mobile_app",
        "status": "pending",
        "delivery_mode": "Store Drop-off",
        "payment_status": "not_paid",
        "payment_method": "",
        "amount_cents": 350000,
        "total": 350000,
        "subtotal": 350000,
        "vat": 0,
        "discount": 0,
        "laundry_mode": "Count system",
        "line_items": [
            OrderLineItem(name="Dry Cleaning", quantity=2, unit_price=175000, amount=350000, laundry_mode="Count system"),
        ],
        "create_txn": False,
    },
    {
        "store_id": "STR-001",
        "customer_key": "Jane Doe",
        "type": "offline",
        "status": "completed",
        "delivery_mode": "Pickup only",
        "payment_status": "paid",
        "payment_method": "Bank transfer",
        "amount_cents": 1500000,
        "total": 1500000,
        "subtotal": 1500000,
        "vat": 0,
        "discount": 0,
        "laundry_mode": "Wash system",
        "line_items": [
            OrderLineItem(name="Wash & Fold", quantity=1, unit_price=1500000, amount=1500000, laundry_mode="Wash system"),
        ],
        "create_txn": True,
        "txn_status": "successful",
        "txn_ref": "pay_b7g3l0n2y8",
    },
    {
        "store_id": "STR-002",
        "customer_key": "Olayiwola Samuel",
        "type": "mobile_app",
        "status": "active",
        "delivery_mode": "Customer Rider",
        "payment_status": "not_paid",
        "payment_method": "",
        "amount_cents": 1500000,
        "total": 1500000,
        "subtotal": 1500000,
        "vat": 0,
        "discount": 0,
        "laundry_mode": "Wash system",
        "line_items": [
            OrderLineItem(name="Wash & Fold", quantity=1, unit_price=1500000, amount=1500000),
        ],
        "create_txn": False,
    },
    {
        "store_id": "STR-002",
        "customer_key": "Olayiwola Samuel",
        "type": "offline",
        "status": "completed",
        "delivery_mode": "Pickup & Delivery",
        "payment_status": "paid",
        "payment_method": "Paystack",
        "amount_cents": 850000,
        "total": 850000,
        "subtotal": 850000,
        "vat": 0,
        "discount": 0,
        "laundry_mode": "Count system",
        "line_items": [
            OrderLineItem(name="Press Only", quantity=5, unit_price=170000, amount=850000),
        ],
        "create_txn": True,
        "txn_status": "successful",
        "txn_ref": "pay_c9h4m2p5z1",
    },
    {
        "store_id": "STR-003",
        "customer_key": "Amaka Eze",
        "type": "offline",
        "status": "pending",
        "delivery_mode": "Store Drop-off",
        "payment_status": "not_paid",
        "payment_method": "",
        "amount_cents": 500000,
        "total": 500000,
        "subtotal": 500000,
        "vat": 0,
        "discount": 0,
        "laundry_mode": "Scale system",
        "line_items": [
            OrderLineItem(name="Dry Cleaning", quantity=1, unit_price=500000, amount=500000),
        ],
        "create_txn": False,
    },
    {
        "store_id": "STR-003",
        "customer_key": "Amaka Eze",
        "type": "mobile_app",
        "status": "completed",
        "delivery_mode": "Delivery only",
        "payment_status": "paid",
        "payment_method": "Paystack",
        "amount_cents": 620000,
        "total": 620000,
        "subtotal": 620000,
        "vat": 0,
        "discount": 0,
        "laundry_mode": "Wash system",
        "line_items": [
            OrderLineItem(name="Wash only", quantity=1, unit_price=620000, amount=620000),
        ],
        "create_txn": True,
        "txn_status": "failed",
        "txn_ref": "pay_d1i5n3q6a2",
    },
]

EXTRA_SERVICES = [
    ("STR-001", "Press only", "press", "Count system", 150000, "per_item", "active"),
    ("STR-001", "Starch", "addon", "Count system", 50000, "per_item", "inactive"),
    ("STR-002", "Wash only", "wash", "Wash system", 200000, "per_load", "active"),
    ("STR-002", "Express wash", "special", "Wash system", 450000, "per_load", "active"),
    ("STR-003", "Dry cleaning suit", "dry_clean", "Count system", 800000, "per_item", "active"),
]


def _config_from_default() -> ServicesConfiguration:
    return ServicesConfiguration(
        laundry_modes=[ConfigItem(id=i["id"], label=i["label"], enabled=i["enabled"]) for i in DEFAULT_CONFIG["laundryModes"]],
        service_types=[ConfigItem(id=i["id"], label=i["label"], enabled=i["enabled"]) for i in DEFAULT_CONFIG["serviceTypes"]],
        order_types=[ConfigItem(id=i["id"], label=i["label"], enabled=i["enabled"]) for i in DEFAULT_CONFIG["orderTypes"]],
    )


def _reset_demo_data(session) -> None:
    for model in (
        TransactionModel,
        InvoiceLineItemModel,
        InvoiceModel,
        OrderLineItemModel,
        OrderModel,
        CustomerModel,
        ServiceModel,
        ServiceConfigModel,
        StoreAssignmentModel,
        BusinessProfileModel,
        StoreModel,
        VerificationCodeModel,
        PasswordResetCodeModel,
        UserModel,
        IdSequenceModel,
    ):
        session.execute(delete(model))
    session.flush()


async def seed_demo_data(force: bool = False) -> None:
    session = get_session_factory()()
    try:
        existing = session.scalar(
            select(UserModel).where(UserModel.email == "demo@rinsehq.com")
        )
        if existing and not force:
            print("Demo data already exists — skipping seed. Use --force to reseed.")
            session.commit()
            return
        if existing and force:
            print("Removing existing demo data...")
            _reset_demo_data(session)

        auth_repo = SqlAlchemyAuthRepository(session)
        store_repo = SqlAlchemyStoreRepository(session)
        order_repo = SqlAlchemyOrderRepository(session)
        catalog_repo = SqlAlchemyCatalogRepository(session)
        billing_repo = SqlAlchemyBillingRepository(session)

        for prefix, val in [("STR-", 3), ("SRV-", 10), ("TXN-", 10), ("ASG-", 10)]:
            session.add(IdSequenceModel(prefix=prefix, last_value=val))
        session.flush()

        user_ids: dict[str, str] = {}
        owner_id = None
        for u in DEMO_USERS:
            user = await auth_repo.create(
                CreateUserInput(email=u["email"], password=DEMO_PASSWORD, name=u["name"])
            )
            row = session.get(UserModel, user.id)
            row.email_verified = u["email_verified"]
            row.onboarding_completed = u["onboarding_completed"]
            row.phone = u["phone"]
            user_ids[u["email"]] = user.id
            if u["email"] == "demo@rinsehq.com":
                owner_id = user.id

        main_store_id = "STR-001"
        for s in DEMO_STORES:
            await store_repo.create_store(
                CreateStoreInput(
                    store_id=s["id"],
                    name=s["name"],
                    address=s["address"],
                    city=s["city"],
                    phone=s["phone"],
                    status="active",
                    owner_user_id=owner_id,  # type: ignore[arg-type]
                    is_main_store=s["is_main_store"],
                )
            )

        session.add(
            BusinessProfileModel(
                user_id=owner_id,  # type: ignore[arg-type]
                store_id=main_store_id,
                business_name="Laundry Care",
                bio="Premium laundry and dry cleaning services in Lagos.",
                registration_no="RC-1234567",
                address="12 Admiralty Way",
                city="Lekki",
                postal_code="101245",
                country="nigeria",
                phone="+2348012345678",
                whatsapp="+2348012345678",
            )
        )
        session.flush()

        for email, store_id, role, perm in ASSIGNMENTS:
            user_id = user_ids[email]
            u = next(x for x in DEMO_USERS if x["email"] == email)
            await store_repo.create_assignment(
                CreateAssignmentInput(
                    store_id=store_id,
                    user_id=user_id,
                    email=email,
                    name=u["name"],
                    role=role,  # type: ignore[arg-type]
                    permission_level=perm,  # type: ignore[arg-type]
                )
            )

        config = _config_from_default()
        for store in DEMO_STORES:
            await catalog_repo.set_config(store["id"], config)
            await catalog_repo.seed_default_services(
                store["id"], ["Wash system", "Count system", "Scale system"]
            )

        for store_id, name, category, mode, price, unit, status in EXTRA_SERVICES:
            await catalog_repo.create_service(
                store_id,
                name=name,
                category=category,
                laundry_mode=mode,
                unit_price=price,
                pricing_unit=unit,
                turnaround_hours=24,
                status=status,
                description=f"{name} service",
                orders_count=3 if status == "active" else 0,
            )

        customer_map: dict[str, object] = {}
        for c in DEMO_CUSTOMERS:
            customer = await catalog_repo.upsert_customer(
                c["store_id"], c["name"], c["email"], c["phone"], c["address"]
            )
            customer_map[f"{c['store_id']}:{c['name']}"] = customer

        now = datetime.now(timezone.utc)
        txn_counter = 1
        for spec in DEMO_ORDERS:
            cust = next(c for c in DEMO_CUSTOMERS if c["name"] == spec["customer_key"] and c["store_id"] == spec["store_id"])
            customer = customer_map[f"{cust['store_id']}:{cust['name']}"]
            order = await order_repo.create(
                CreateOrderInput(
                    store_id=spec["store_id"],
                    customer_id=customer.id,  # type: ignore[union-attr]
                    type=spec["type"],  # type: ignore[arg-type]
                    customer=cust["name"],
                    amount_cents=spec["amount_cents"],
                    status=spec["status"],  # type: ignore[arg-type]
                    order_date=now - timedelta(days=txn_counter),
                    delivery_date=now + timedelta(days=2),
                    delivery_mode=spec["delivery_mode"],
                    customer_email=cust["email"],
                    customer_phone=cust["phone"],
                    customer_address=cust["address"],
                    payment_status=spec["payment_status"],
                    payment_method=spec["payment_method"],
                    laundry_mode=spec["laundry_mode"],
                    service_type="Wash & Fold",
                    subtotal=spec["subtotal"],
                    vat=spec["vat"],
                    discount=spec["discount"],
                    total=spec["total"],
                    line_items=spec["line_items"],
                )
            )
            await billing_repo.create_invoice_for_order(order.id, spec["store_id"])
            if spec.get("create_txn"):
                fee = int(spec["total"] * 0.015)
                net = spec["total"] - fee
                await billing_repo.create_payment_transaction(
                    store_id=spec["store_id"],
                    order_id=order.id,
                    reference=spec["txn_ref"],  # type: ignore[arg-type]
                    customer=cust["name"],
                    amount_cents=spec["total"],
                    type="payment",
                    payment_method=spec.get("payment_method") or "Paystack",
                    status=spec["txn_status"],  # type: ignore[arg-type]
                    fee_cents=fee if spec["txn_status"] == "successful" else 0,
                    net_amount_cents=net if spec["txn_status"] == "successful" else 0,
                    channel="Card" if spec["txn_status"] == "successful" else "USSD",
                    customer_email=cust["email"],
                    customer_phone=cust["phone"],
                    paid_at=now if spec["txn_status"] == "successful" else None,
                )
            txn_counter += 1

        session.commit()
        print("Demo data seeded successfully.")
        print(f"  Users: {len(DEMO_USERS)} (password: {DEMO_PASSWORD})")
        print(f"  Stores: {len(DEMO_STORES)}")
        print(f"  Orders: {len(DEMO_ORDERS)}")
        print(f"  Customers: {len(DEMO_CUSTOMERS)}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    import sys

    force = "--force" in sys.argv or "-f" in sys.argv
    asyncio.run(seed_demo_data(force=force))


if __name__ == "__main__":
    main()
