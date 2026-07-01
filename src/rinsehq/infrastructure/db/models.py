from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rinsehq.infrastructure.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class IdSequenceModel(Base):
    __tablename__ = "id_sequences"

    prefix: Mapped[str] = mapped_column(String(16), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class VerificationCodeModel(Base):
    __tablename__ = "verification_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PasswordResetCodeModel(Base):
    __tablename__ = "password_reset_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StoreModel(Base):
    __tablename__ = "stores"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    is_main_store: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    owner_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StoreAssignmentModel(Base):
    __tablename__ = "store_assignments"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    store_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("stores.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    permission_level: Mapped[str] = mapped_column(String(32), nullable=False)
    custom_permissions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")


class BusinessProfileModel(Base):
    __tablename__ = "business_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True, nullable=False
    )
    store_id: Mapped[Optional[str]] = mapped_column(
        String(16), ForeignKey("stores.id"), nullable=True
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    registration_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    address: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    postal_code: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    country: Mapped[str] = mapped_column(String(64), nullable=False, default="nigeria")
    phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    whatsapp: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    document_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)


class ServiceConfigModel(Base):
    __tablename__ = "service_configs"

    store_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("stores.id"), primary_key=True
    )
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ServiceModel(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    store_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("stores.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    laundry_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    pricing_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    turnaround_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CustomerModel(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    store_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("stores.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    address: Mapped[str] = mapped_column(String(500), nullable=False, default="")


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    store_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("stores.id"), nullable=False, index=True
    )
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("customers.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    customer: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    customer_address: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_mode: Mapped[str] = mapped_column(String(255), nullable=False)
    order_type: Mapped[str] = mapped_column(String(32), nullable=False, default="offline")
    laundry_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    service_type: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    payment_status: Mapped[str] = mapped_column(String(16), nullable=False, default="not_paid")
    payment_method: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    pickup_date: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    pickup_time: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    delivery_time: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vat: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    line_items: Mapped[list["OrderLineItemModel"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    invoice: Mapped[Optional["InvoiceModel"]] = relationship(back_populates="order", uselist=False)


class OrderLineItemModel(Base):
    __tablename__ = "order_line_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    laundry_mode: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    order: Mapped[OrderModel] = relationship(back_populates="line_items")


class InvoiceModel(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), unique=True, nullable=False
    )
    store_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("stores.id"), nullable=False, index=True
    )
    invoice_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="not_paid")
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False)
    vat: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    invoice_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped[OrderModel] = relationship(back_populates="invoice")
    line_items: Mapped[list["InvoiceLineItemModel"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLineItemModel(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id"), nullable=False, index=True
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    laundry_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    items_label: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    invoice: Mapped[InvoiceModel] = relationship(back_populates="line_items")


class TransactionModel(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    store_id: Mapped[str] = mapped_column(
        String(16), ForeignKey("stores.id"), nullable=False, index=True
    )
    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id"), nullable=False, index=True
    )
    reference: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    customer: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="payment")
    payment_method: Mapped[str] = mapped_column(String(64), nullable=False, default="Nomba")
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    fee_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    channel: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
