"""order line item service_id

Revision ID: 004
Revises: 003
Create Date: 2026-07-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "order_line_items",
        sa.Column("service_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_order_line_items_service_id",
        "order_line_items",
        ["service_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_order_line_items_service_id", table_name="order_line_items")
    op.drop_column("order_line_items", "service_id")
