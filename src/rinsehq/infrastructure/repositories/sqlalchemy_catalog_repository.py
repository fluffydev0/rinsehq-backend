from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from rinsehq.domain.entities.account import AdminPermissions, BusinessInfo, PersonalInfo, SubAdmin
from rinsehq.domain.entities.customer import Customer
from rinsehq.domain.entities.invoice import Invoice, InvoiceLineItem
from rinsehq.domain.entities.service import ConfigItem, Service, ServicesConfiguration
from rinsehq.domain.entities.transaction import Transaction
from rinsehq.domain.repositories.catalog_repository import CatalogRepository
from rinsehq.infrastructure.auth.permissions import PermissionLevel, resolve_permissions
from rinsehq.infrastructure.db.id_generator import next_prefixed_id
from rinsehq.infrastructure.db.models import (
    BusinessProfileModel,
    CustomerModel,
    InvoiceLineItemModel,
    InvoiceModel,
    OrderModel,
    ServiceConfigModel,
    ServiceModel,
    StoreAssignmentModel,
    StoreModel,
    TransactionModel,
    UserModel,
)
from rinsehq.infrastructure.security.passwords import hash_password

DEFAULT_CONFIG = {
    "laundryModes": [
        {"id": "wash", "label": "Wash system", "enabled": True},
        {"id": "count", "label": "Count system", "enabled": True},
        {"id": "scale", "label": "Scale system", "enabled": True},
    ],
    "serviceTypes": [
        {"id": "wash-fold", "label": "Wash & Fold", "enabled": True},
        {"id": "dry-clean", "label": "Dry Cleaning", "enabled": True},
    ],
    "orderTypes": [
        {"id": "pickup-delivery", "label": "Pickup & Delivery", "enabled": True},
        {"id": "drop-off", "label": "Store Drop-off", "enabled": True},
    ],
}


def _format_ngn(amount_kobo: int) -> str:
    naira = amount_kobo / 100
    return f"N{naira:,.0f}"


class SqlAlchemyCatalogRepository(CatalogRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    async def list_services(
        self, store_id: str, status: str | None = None, category: str | None = None
    ) -> list[Service]:
        stmt = select(ServiceModel).where(ServiceModel.store_id == store_id)
        if status:
            stmt = stmt.where(ServiceModel.status == status)
        if category:
            stmt = stmt.where(ServiceModel.category == category)
        rows = self._session.scalars(stmt.order_by(ServiceModel.name)).all()
        return [self._service_entity(r) for r in rows]

    async def service_summary(self, store_id: str) -> dict:
        rows = self._session.scalars(
            select(ServiceModel).where(ServiceModel.store_id == store_id)
        ).all()
        categories = {r.category for r in rows}
        return {
            "total": len(rows),
            "active": sum(1 for r in rows if r.status == "active"),
            "inactive": sum(1 for r in rows if r.status == "inactive"),
            "categories": len(categories),
        }

    async def find_service(self, service_id: str, store_id: str) -> Optional[Service]:
        row = self._session.scalar(
            select(ServiceModel).where(
                ServiceModel.id == service_id, ServiceModel.store_id == store_id
            )
        )
        return self._service_entity(row) if row else None

    async def create_service(self, store_id: str, **fields: object) -> Service:
        svc_id = next_prefixed_id(self._session, "SRV-")
        row = ServiceModel(id=svc_id, store_id=store_id, **fields)  # type: ignore[arg-type]
        self._session.add(row)
        self._session.flush()
        return self._service_entity(row)

    async def update_service(
        self, service_id: str, store_id: str, **fields: object
    ) -> Optional[Service]:
        row = self._session.scalar(
            select(ServiceModel).where(
                ServiceModel.id == service_id, ServiceModel.store_id == store_id
            )
        )
        if not row:
            return None
        for k, v in fields.items():
            if v is not None and hasattr(row, k):
                setattr(row, k, v)
        row.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return self._service_entity(row)

    async def get_config(self, store_id: str) -> ServicesConfiguration:
        row = self._session.get(ServiceConfigModel, store_id)
        data = row.config if row else DEFAULT_CONFIG
        return self._config_entity(data)

    async def set_config(self, store_id: str, config: ServicesConfiguration) -> ServicesConfiguration:
        data = self._config_to_dict(config)
        row = self._session.get(ServiceConfigModel, store_id)
        if row:
            row.config = data
        else:
            self._session.add(ServiceConfigModel(store_id=store_id, config=data))
        self._session.flush()
        return config

    async def add_config_item(self, store_id: str, section: str, label: str) -> ServicesConfiguration:
        row = self._session.get(ServiceConfigModel, store_id)
        data = dict(row.config) if row else dict(DEFAULT_CONFIG)
        key = section if section.endswith("s") else f"{section}s"
        if key not in data:
            data[key] = []
        item_id = str(uuid.uuid4())[:8]
        data[key].append({"id": item_id, "label": label, "enabled": True})
        if row:
            row.config = data
        else:
            self._session.add(ServiceConfigModel(store_id=store_id, config=data))
        self._session.flush()
        return self._config_entity(data)

    async def seed_default_services(self, store_id: str, laundry_modes: list[str]) -> None:
        defaults = [
            ("Wash only", "wash", "Wash system", 200000, "per_load"),
            ("Wash & Fold", "wash", "Wash system", 350000, "per_load"),
            ("Dry Cleaning", "dry_clean", "Count system", 500000, "per_item"),
        ]
        for name, category, mode, price, unit in defaults:
            if mode in laundry_modes or not laundry_modes:
                await self.create_service(
                    store_id,
                    name=name,
                    category=category,
                    laundry_mode=mode,
                    unit_price=price,
                    pricing_unit=unit,
                    turnaround_hours=24,
                    status="active",
                    description=f"Default {name} service",
                )

    async def increment_service_orders_count(
        self, store_id: str, service_ids: list[str]
    ) -> None:
        unique_ids = {sid for sid in service_ids if sid}
        if not unique_ids:
            return
        rows = self._session.scalars(
            select(ServiceModel).where(
                ServiceModel.store_id == store_id,
                ServiceModel.id.in_(unique_ids),
            )
        ).all()
        for row in rows:
            row.orders_count += 1
        self._session.flush()

    async def list_customers(self, store_id: str, limit: int = 20) -> list[Customer]:
        rows = self._session.scalars(
            select(CustomerModel)
            .where(CustomerModel.store_id == store_id)
            .order_by(CustomerModel.name)
            .limit(limit)
        ).all()
        return [self._customer_entity(r) for r in rows]

    async def search_customers(self, store_id: str, search: str) -> list[Customer]:
        term = f"%{search}%"
        rows = self._session.scalars(
            select(CustomerModel).where(
                CustomerModel.store_id == store_id,
                or_(
                    CustomerModel.name.ilike(term),
                    CustomerModel.email.ilike(term),
                    CustomerModel.phone.ilike(term),
                ),
            )
        ).all()
        return [self._customer_entity(r) for r in rows]

    async def upsert_customer(
        self, store_id: str, name: str, email: str, phone: str, address: str
    ) -> Customer:
        row = self._session.scalar(
            select(CustomerModel).where(
                CustomerModel.store_id == store_id,
                CustomerModel.email == email.lower(),
            )
        )
        if row:
            row.name = name
            row.phone = phone
            row.address = address
        else:
            row = CustomerModel(
                store_id=store_id, name=name, email=email.lower(), phone=phone, address=address
            )
            self._session.add(row)
        self._session.flush()
        return self._customer_entity(row)

    @staticmethod
    def _service_entity(row: ServiceModel) -> Service:
        return Service(
            id=row.id,
            store_id=row.store_id,
            name=row.name,
            category=row.category,
            laundry_mode=row.laundry_mode,
            unit_price=row.unit_price,
            pricing_unit=row.pricing_unit,
            turnaround_hours=row.turnaround_hours,
            status=row.status,
            description=row.description,
            orders_count=row.orders_count,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _customer_entity(row: CustomerModel) -> Customer:
        return Customer(
            id=row.id, name=row.name, email=row.email, phone=row.phone, address=row.address
        )

    @staticmethod
    def _config_entity(data: dict) -> ServicesConfiguration:
        def items(key: str) -> list[ConfigItem]:
            return [
                ConfigItem(id=i["id"], label=i["label"], enabled=i.get("enabled", True))
                for i in data.get(key, [])
            ]

        return ServicesConfiguration(
            laundry_modes=items("laundryModes"),
            service_types=items("serviceTypes"),
            order_types=items("orderTypes"),
        )

    @staticmethod
    def _config_to_dict(config: ServicesConfiguration) -> dict:
        def to_list(items: list[ConfigItem]) -> list[dict]:
            return [{"id": i.id, "label": i.label, "enabled": i.enabled} for i in items]

        return {
            "laundryModes": to_list(config.laundry_modes),
            "serviceTypes": to_list(config.service_types),
            "orderTypes": to_list(config.order_types),
        }


class SqlAlchemyBillingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def create_invoice_for_order(self, order_id: str, store_id: str) -> Invoice:
        order = self._session.scalar(
            select(OrderModel)
            .where(OrderModel.id == order_id)
            .options(selectinload(OrderModel.line_items))
        )
        if not order:
            raise ValueError("Order not found")
        store = self._session.get(StoreModel, store_id)
        profile = self._session.scalar(
            select(BusinessProfileModel).where(
                BusinessProfileModel.user_id == store.owner_user_id  # type: ignore[union-attr]
            )
        )
        invoice_no = f"INV-{order.id[:8].upper()}"
        inv = InvoiceModel(
            order_id=order.id,
            store_id=store_id,
            invoice_no=invoice_no,
            status=order.payment_status,
            subtotal=order.subtotal,
            vat=order.vat,
            discount=order.discount,
            total=order.total,
            invoice_date=datetime.now(timezone.utc),
        )
        self._session.add(inv)
        self._session.flush()
        for idx, li in enumerate(order.line_items or []):
            self._session.add(
                InvoiceLineItemModel(
                    invoice_id=inv.id,
                    index=idx + 1,
                    laundry_mode=li.laundry_mode or order.laundry_mode,
                    items_label=li.name,
                    unit_price=li.unit_price,
                    amount=li.amount,
                )
            )
        self._session.flush()
        return self._invoice_entity(inv, order, profile, store)

    async def find_invoice(self, invoice_id: str) -> Optional[Invoice]:
        inv = self._session.scalar(
            select(InvoiceModel)
            .where(InvoiceModel.id == invoice_id)
            .options(selectinload(InvoiceModel.line_items), selectinload(InvoiceModel.order))
        )
        if not inv:
            return None
        store = self._session.get(StoreModel, inv.store_id)
        profile = self._session.scalar(
            select(BusinessProfileModel).where(
                BusinessProfileModel.user_id == store.owner_user_id  # type: ignore[union-attr]
            )
        )
        return self._invoice_entity(inv, inv.order, profile, store)

    async def find_invoice_for_store(self, invoice_id: str, store_id: str) -> Optional[Invoice]:
        inv = self._session.scalar(
            select(InvoiceModel)
            .where(InvoiceModel.id == invoice_id, InvoiceModel.store_id == store_id)
            .options(selectinload(InvoiceModel.line_items), selectinload(InvoiceModel.order))
        )
        if not inv:
            return None
        store = self._session.get(StoreModel, store_id)
        profile = self._session.scalar(
            select(BusinessProfileModel).where(
                BusinessProfileModel.user_id == store.owner_user_id  # type: ignore[union-attr]
            )
        )
        return self._invoice_entity(inv, inv.order, profile, store)

    async def mark_invoice_paid(self, invoice_id: str) -> None:
        inv = self._session.get(InvoiceModel, invoice_id)
        if inv:
            inv.status = "paid"
            self._session.flush()

    async def list_transactions(
        self, store_id: str, status: str | None, tx_type: str | None, page: int, limit: int
    ) -> tuple[list[Transaction], int]:
        stmt = select(TransactionModel).where(TransactionModel.store_id == store_id)
        if status:
            stmt = stmt.where(TransactionModel.status == status)
        if tx_type:
            stmt = stmt.where(TransactionModel.type == tx_type)
        stmt = stmt.order_by(TransactionModel.created_at.desc())
        total = self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = self._session.scalars(stmt.offset((page - 1) * limit).limit(limit)).all()
        return [self._txn_entity(r) for r in rows], total

    async def find_transaction(self, txn_id: str, store_id: str) -> Optional[Transaction]:
        row = self._session.scalar(
            select(TransactionModel).where(
                TransactionModel.id == txn_id, TransactionModel.store_id == store_id
            )
        )
        return self._txn_entity(row) if row else None

    async def create_payment_transaction(self, **fields: object) -> Transaction:
        txn_id = next_prefixed_id(self._session, "TXN-")
        row = TransactionModel(id=txn_id, **fields)  # type: ignore[arg-type]
        self._session.add(row)
        self._session.flush()
        return self._txn_entity(row)

    async def create_refund_transaction(
        self, payment_id: str, reason: str, store_id: str
    ) -> Transaction:
        payment = await self.find_transaction(payment_id, store_id)
        if not payment:
            raise ValueError("Transaction not found")
        return await self.create_payment_transaction(
            store_id=store_id,
            order_id=payment.order_id,
            reference=f"ref_{payment.reference}",
            customer=payment.customer,
            amount_cents=payment.amount_cents,
            type="refund",
            payment_method=payment.payment_method,
            status="successful",
            fee_cents=0,
            net_amount_cents=payment.amount_cents,
            channel=payment.channel,
            description=reason,
            customer_email=payment.customer_email,
            customer_phone=payment.customer_phone,
            paid_at=datetime.now(timezone.utc),
        )

    async def revenue_summary(self, store_id: str) -> dict:
        rows = self._session.scalars(
            select(TransactionModel).where(
                TransactionModel.store_id == store_id, TransactionModel.type == "payment"
            )
        ).all()
        if not rows:
            return {"total": 0, "successRate": 0}
        successful = [r for r in rows if r.status == "successful"]
        total = sum(r.amount_cents for r in successful)
        rate = int(len(successful) / len(rows) * 100) if rows else 0
        return {"total": total, "successRate": rate}

    async def update_order_payment(self, order_id: str, status: str, method: str) -> None:
        order = self._session.get(OrderModel, order_id)
        if order:
            order.payment_status = status
            order.payment_method = method
            self._session.flush()

    async def find_transaction_by_reference(self, reference: str) -> Optional[Transaction]:
        row = self._session.scalar(
            select(TransactionModel).where(TransactionModel.reference == reference)
        )
        return self._txn_entity(row) if row else None

    async def mark_transaction_successful(
        self,
        transaction_id: str,
        *,
        channel: str = "card",
        fee_kobo: int = 0,
        net_kobo: int = 0,
    ) -> None:
        txn = self._session.get(TransactionModel, transaction_id)
        if txn:
            txn.status = "successful"
            txn.channel = channel
            txn.fee_cents = fee_kobo
            txn.net_amount_cents = net_kobo
            txn.paid_at = datetime.now(timezone.utc)
            self._session.flush()

    async def mark_transaction_failed(self, transaction_id: str) -> None:
        txn = self._session.get(TransactionModel, transaction_id)
        if txn:
            txn.status = "failed"
            self._session.flush()

    async def find_invoice_by_order_id(self, order_id: str) -> Optional[Invoice]:
        inv = self._session.scalar(
            select(InvoiceModel)
            .where(InvoiceModel.order_id == order_id)
            .options(selectinload(InvoiceModel.line_items), selectinload(InvoiceModel.order))
        )
        if not inv:
            return None
        store = self._session.get(StoreModel, inv.store_id)
        profile = self._session.scalar(
            select(BusinessProfileModel).where(
                BusinessProfileModel.user_id == store.owner_user_id  # type: ignore[union-attr]
            )
        )
        return self._invoice_entity(inv, inv.order, profile, store)

    async def find_invoice_by_account_ref(self, account_ref: str) -> Optional[Invoice]:
        suffix = account_ref.removeprefix("rinse_inv_").removeprefix("rinse_")
        invoice_no = suffix.replace("_", "-").upper()
        if not invoice_no.startswith("INV-"):
            invoice_no = f"INV-{invoice_no}"
        inv = self._session.scalar(
            select(InvoiceModel)
            .where(InvoiceModel.invoice_no == invoice_no)
            .options(selectinload(InvoiceModel.line_items), selectinload(InvoiceModel.order))
        )
        if not inv:
            return None
        store = self._session.get(StoreModel, inv.store_id)
        profile = self._session.scalar(
            select(BusinessProfileModel).where(
                BusinessProfileModel.user_id == store.owner_user_id  # type: ignore[union-attr]
            )
        )
        return self._invoice_entity(inv, inv.order, profile, store)

    def _invoice_entity(
        self, inv: InvoiceModel, order: OrderModel, profile: BusinessProfileModel | None, store: StoreModel
    ) -> Invoice:
        business_name = profile.business_name if profile else store.name
        return Invoice(
            id=inv.id,
            order_id=inv.order_id,
            store_id=inv.store_id,
            business_name=business_name,
            status=inv.status,  # type: ignore[arg-type]
            invoice_no=inv.invoice_no,
            invoice_date=inv.invoice_date,
            payment_method=order.payment_method or "Nomba",
            subtotal=inv.subtotal,
            vat=inv.vat,
            discount=inv.discount,
            total=inv.total,
            customer_name=order.customer,
            customer_email=order.customer_email,
            customer_phone=order.customer_phone,
            customer_address=order.customer_address,
            line_items=[
                InvoiceLineItem(
                    index=li.index,
                    laundry_mode=li.laundry_mode,
                    items_label=li.items_label,
                    unit_price=li.unit_price,
                    amount=li.amount,
                )
                for li in inv.line_items
            ],
            business_address=profile.address if profile else store.address,
            business_phone=profile.phone if profile else store.phone,
            business_whatsapp=profile.whatsapp if profile else store.phone,
        )

    @staticmethod
    def _txn_entity(row: TransactionModel) -> Transaction:
        return Transaction(
            id=row.id,
            reference=row.reference,
            order_id=row.order_id,
            customer=row.customer,
            amount_cents=row.amount_cents,
            type=row.type,  # type: ignore[arg-type]
            payment_method=row.payment_method,
            status=row.status,  # type: ignore[arg-type]
            date=row.created_at,
            customer_email=row.customer_email,
            customer_phone=row.customer_phone,
            description=row.description,
            fee_cents=row.fee_cents,
            net_amount_cents=row.net_amount_cents,
            channel=row.channel,
            paid_at=row.paid_at,
        )


class SqlAlchemyAccountRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def get_personal(self, user_id: str) -> PersonalInfo:
        user = self._session.get(UserModel, user_id)
        if not user:
            raise ValueError("User not found")
        return PersonalInfo(full_name=user.name, email=user.email, phone=user.phone)

    async def get_business(self, user_id: str) -> BusinessInfo:
        profile = self._session.scalar(
            select(BusinessProfileModel).where(BusinessProfileModel.user_id == user_id)
        )
        if not profile:
            store = self._session.scalar(
                select(StoreModel).where(
                    StoreModel.owner_user_id == user_id, StoreModel.is_main_store.is_(True)
                )
            )
            return BusinessInfo(
                business_name=store.name if store else "",
                bio="",
                registration_no="",
                address=store.address if store else "",
                city=store.city if store else "",
                postal_code="",
                country="nigeria",
                phone=store.phone if store else "",
                whatsapp=store.phone if store else "",
            )
        return self._business_entity(profile)

    async def update_business(self, user_id: str, **fields: object) -> BusinessInfo:
        profile = self._session.scalar(
            select(BusinessProfileModel).where(BusinessProfileModel.user_id == user_id)
        )
        if not profile:
            profile = BusinessProfileModel(user_id=user_id)
            self._session.add(profile)
        for k, v in fields.items():
            if v is not None and hasattr(profile, k):
                setattr(profile, k, v)
        self._session.flush()
        return self._business_entity(profile)

    async def update_business_profile_files(
        self, user_id: str, logo_url: str | None, banner_url: str | None, document_url: str | None
    ) -> BusinessInfo:
        profile = self._session.scalar(
            select(BusinessProfileModel).where(BusinessProfileModel.user_id == user_id)
        )
        if not profile:
            profile = BusinessProfileModel(user_id=user_id)
            self._session.add(profile)
        if logo_url:
            profile.logo_url = logo_url
        if banner_url:
            profile.banner_url = banner_url
        if document_url:
            profile.document_url = document_url
        self._session.flush()
        return self._business_entity(profile)

    async def list_sub_admins(self, owner_user_id: str) -> list[SubAdmin]:
        store_ids = [
            s.id
            for s in self._session.scalars(
                select(StoreModel).where(StoreModel.owner_user_id == owner_user_id)
            ).all()
        ]
        rows = self._session.scalars(
            select(StoreAssignmentModel).where(
                StoreAssignmentModel.store_id.in_(store_ids),
                StoreAssignmentModel.role != "owner",
            )
        ).all()
        grouped: dict[str, list[str]] = {}
        for r in rows:
            grouped.setdefault(r.user_id, []).append(r.store_id)
        result = []
        for user_id, sids in grouped.items():
            asn = next(r for r in rows if r.user_id == user_id)
            user = self._session.get(UserModel, user_id)
            if not user:
                continue
            perms = resolve_permissions(asn.permission_level, asn.custom_permissions)  # type: ignore[arg-type]
            result.append(
                SubAdmin(
                    id=f"ADM-{asn.id.split('-')[-1]}",
                    name=asn.name,
                    email=asn.email,
                    permission_level=asn.permission_level,  # type: ignore[arg-type]
                    permissions=AdminPermissions(
                        orders=perms["orders"],
                        services=perms["services"],
                        transactions=perms["transactions"],
                        reports=perms["reports"],
                        settings=perms["settings"],
                        admin_management=perms["adminManagement"],
                    ),
                    status=asn.status,
                    store_ids=sids,
                )
            )
        return result

    async def create_sub_admin(
        self,
        owner_user_id: str,
        name: str,
        email: str,
        permission_level: PermissionLevel,
        permissions: dict[str, bool],
        status: str,
        store_ids: list[str],
        password: str,
    ) -> SubAdmin:
        user = self._session.scalar(select(UserModel).where(UserModel.email == email.lower()))
        if not user:
            user = UserModel(
                email=email.lower(),
                name=name,
                password_hash=hash_password(password),
                email_verified=True,
            )
            self._session.add(user)
            self._session.flush()
        custom = {k: v for k, v in permissions.items()}
        for sid in store_ids:
            asn_id = next_prefixed_id(self._session, "ASG-")
            self._session.add(
                StoreAssignmentModel(
                    id=asn_id,
                    store_id=sid,
                    user_id=user.id,
                    email=email.lower(),
                    name=name,
                    role="sub_admin",
                    permission_level=permission_level,
                    custom_permissions=custom,
                    status=status,
                )
            )
        self._session.flush()
        admins = await self.list_sub_admins(owner_user_id)
        return next(a for a in admins if a.email == email.lower())

    async def update_sub_admin(self, admin_id: str, owner_user_id: str, **fields: object) -> Optional[SubAdmin]:
        asn_suffix = admin_id.replace("ADM-", "")
        rows = self._session.scalars(select(StoreAssignmentModel)).all()
        target = next((r for r in rows if r.id.endswith(asn_suffix)), None)
        if not target:
            return None
        if "name" in fields and fields["name"]:
            target.name = fields["name"]  # type: ignore[assignment]
        if "permission_level" in fields and fields["permission_level"]:
            target.permission_level = fields["permission_level"]  # type: ignore[assignment]
        if "permissions" in fields and fields["permissions"]:
            target.custom_permissions = fields["permissions"]  # type: ignore[assignment]
        if "status" in fields and fields["status"]:
            target.status = fields["status"]  # type: ignore[assignment]
        self._session.flush()
        admins = await self.list_sub_admins(owner_user_id)
        return next((a for a in admins if a.email == target.email), None)

    async def delete_sub_admin(self, admin_id: str, owner_user_id: str) -> bool:
        asn_suffix = admin_id.replace("ADM-", "")
        rows = self._session.scalars(select(StoreAssignmentModel)).all()
        targets = [r for r in rows if r.id.endswith(asn_suffix)]
        if not targets:
            return False
        for t in targets:
            t.status = "inactive"
        self._session.flush()
        return True

    @staticmethod
    def _business_entity(profile: BusinessProfileModel) -> BusinessInfo:
        return BusinessInfo(
            business_name=profile.business_name,
            bio=profile.bio,
            registration_no=profile.registration_no,
            address=profile.address,
            city=profile.city,
            postal_code=profile.postal_code,
            country=profile.country,
            phone=profile.phone,
            whatsapp=profile.whatsapp,
        )
