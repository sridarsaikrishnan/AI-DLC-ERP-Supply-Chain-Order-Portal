"""Add `lines` (JSONB) to `orders`.

0001 modeled the order header + reverse-routing key but not the line items the reseller/
operator read models need (`OrderLineView` per line) — this was a missing column, not a
new table, so the reseller/operator query shape doesn't change.

Revision ID: 0002_order_lines
Revises: 0001_target_architecture
Create Date: 2026-09-27
"""

from __future__ import annotations

from alembic import op

revision = "0002_order_lines"
down_revision = "0001_target_architecture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE orders ADD COLUMN lines JSONB NOT NULL DEFAULT '[]'::jsonb;")


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN lines;")
