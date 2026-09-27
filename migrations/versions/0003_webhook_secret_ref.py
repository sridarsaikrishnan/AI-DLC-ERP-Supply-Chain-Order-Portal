"""Add `webhook_secret_ref` to `erp_connections`.

Separate from `secret_ref` (the ERP login credential) — see the docstring on
`ErpConnection.webhook_secret_ref` for why these must not be the same secret. Nullable:
a connection's webhook is an opt-in onboarding step (target-architecture.md 5a); until
set, that connection relies on the reconciliation sweeper only.

Revision ID: 0003_webhook_secret_ref
Revises: 0002_order_lines
Create Date: 2026-09-27
"""

from __future__ import annotations

from alembic import op

revision = "0003_webhook_secret_ref"
down_revision = "0002_order_lines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE erp_connections ADD COLUMN webhook_secret_ref TEXT;")


def downgrade() -> None:
    op.execute("ALTER TABLE erp_connections DROP COLUMN webhook_secret_ref;")
