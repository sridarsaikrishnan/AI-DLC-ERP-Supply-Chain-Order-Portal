"""Add tax_rate/line_discount to items — a flat per-item tax rate and per-unit discount,
mirroring the unit_price pattern (ADR-0013: tax/discount source).

Revision ID: 0007_item_tax_discount
Revises: 0006_connection_credentials
Create Date: 2026-10-03
"""

from __future__ import annotations

from alembic import op

revision = "0007_item_tax_discount"
down_revision = "0006_connection_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE items ADD COLUMN tax_rate JSONB;
        ALTER TABLE items ADD COLUMN line_discount TEXT;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE items DROP COLUMN tax_rate;
        ALTER TABLE items DROP COLUMN line_discount;
        """
    )
