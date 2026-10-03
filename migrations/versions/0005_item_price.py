"""Add unit_price/currency to items — the catalog becomes the price source for order
lines (resolved at submission time, never trusted from reseller input).

Revision ID: 0005_item_price
Revises: 0004_webhook_outbound
Create Date: 2026-10-03
"""

from __future__ import annotations

from alembic import op

revision = "0005_item_price"
down_revision = "0004_webhook_outbound"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE items ADD COLUMN unit_price TEXT;
        ALTER TABLE items ADD COLUMN currency TEXT;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE items DROP COLUMN unit_price;
        ALTER TABLE items DROP COLUMN currency;
        """
    )
