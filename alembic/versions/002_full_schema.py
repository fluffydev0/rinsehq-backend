"""full schema

Revision ID: 002
Revises: 001
Create Date: 2026-06-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "id_sequences",
        sa.Column("prefix", sa.String(length=16), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("prefix"),
    )

    op.add_column("users", sa.Column("phone", sa.String(length=32), nullable=False, server_default=""))
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )

    op.create_table(
        "verification_codes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=6), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verification_codes_email", "verification_codes", ["email"])

    op.create_table(
        "stores",
        sa.Column("id", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("city", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("is_main_store", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stores_owner_user_id", "stores", ["owner_user_id"])

    op.create_table(
        "store_assignments",
        sa.Column("id", sa.String(length=16), nullable=False),
        sa.Column("store_id", sa.String(length=16), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("permission_level", sa.String(length=32), nullable=False),
        sa.Column("custom_permissions", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_store_assignments_store_id", "store_assignments", ["store_id"])
    op.create_index("ix_store_assignments_user_id", "store_assignments", ["user_id"])

    op.create_table(
        "business_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("store_id", sa.String(length=16), nullable=True),
        sa.Column("business_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("bio", sa.Text(), nullable=False, server_default=""),
        sa.Column("registration_no", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("address", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("city", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("postal_code", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("country", sa.String(length=64), nullable=False, server_default="nigeria"),
        sa.Column("phone", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("whatsapp", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("logo_url", sa.String(length=512), nullable=True),
        sa.Column("banner_url", sa.String(length=512), nullable=True),
        sa.Column("document_url", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "service_configs",
        sa.Column("store_id", sa.String(length=16), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("store_id"),
    )

    op.create_table(
        "services",
        sa.Column("id", sa.String(length=16), nullable=False),
        sa.Column("store_id", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("laundry_mode", sa.String(length=64), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("pricing_unit", sa.String(length=32), nullable=False),
        sa.Column("turnaround_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("orders_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_services_store_id", "services", ["store_id"])

    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("store_id", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("address", sa.String(length=500), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_store_id", "customers", ["store_id"])

    op.drop_table("orders")

    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("store_id", sa.String(length=16), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("customer", sa.String(length=255), nullable=False),
        sa.Column("customer_email", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("customer_phone", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("customer_address", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("order_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_mode", sa.String(length=255), nullable=False),
        sa.Column("order_type", sa.String(length=32), nullable=False, server_default="offline"),
        sa.Column("laundry_mode", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("service_type", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("payment_status", sa.String(length=16), nullable=False, server_default="not_paid"),
        sa.Column("payment_method", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("pickup_date", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("pickup_time", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("delivery_time", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("subtotal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vat", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_store_id", "orders", ["store_id"])

    op.create_table(
        "order_line_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("laundry_mode", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_line_items_order_id", "order_line_items", ["order_id"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("store_id", sa.String(length=16), nullable=False),
        sa.Column("invoice_no", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="not_paid"),
        sa.Column("subtotal", sa.Integer(), nullable=False),
        sa.Column("vat", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("invoice_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_invoices_invoice_no", "invoices", ["invoice_no"])
    op.create_index("ix_invoices_store_id", "invoices", ["store_id"])

    op.create_table(
        "invoice_line_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("laundry_mode", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("items_label", sa.String(length=255), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_line_items_invoice_id", "invoice_line_items", ["invoice_id"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.String(length=16), nullable=False),
        sa.Column("store_id", sa.String(length=16), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("reference", sa.String(length=128), nullable=False),
        sa.Column("customer", sa.String(length=255), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False, server_default="payment"),
        sa.Column("payment_method", sa.String(length=64), nullable=False, server_default="Paystack"),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("fee_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("net_amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("channel", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("customer_email", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("customer_phone", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_reference", "transactions", ["reference"], unique=True)
    op.create_index("ix_transactions_status", "transactions", ["status"])
    op.create_index("ix_transactions_store_id", "transactions", ["store_id"])


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("invoice_line_items")
    op.drop_table("invoices")
    op.drop_table("order_line_items")
    op.drop_table("orders")
    op.drop_table("customers")
    op.drop_table("services")
    op.drop_table("service_configs")
    op.drop_table("business_profiles")
    op.drop_table("store_assignments")
    op.drop_table("stores")
    op.drop_index("ix_verification_codes_email", table_name="verification_codes")
    op.drop_table("verification_codes")
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "phone")
    op.drop_table("id_sequences")

    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("customer", sa.String(length=255), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("order_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_mode", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_status", "orders", ["status"])
