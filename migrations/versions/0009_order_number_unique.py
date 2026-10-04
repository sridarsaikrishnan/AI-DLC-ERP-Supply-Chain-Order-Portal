"""Stop two orders from the same reseller sharing one order number.

What was wrong: a reseller's own order number (`client_reference`, e.g. "PO-2024-1182")
had no uniqueness check anywhere. Two orders from the same reseller could be saved with
the exact same order number, and the database would accept both without complaint.

What this does: adds a database rule saying "order number + reseller must be unique
together." Two different resellers can still both use "PO-1" — only the same reseller
re-using the same number is now blocked.

What this does NOT do on its own: the platform never actually used `client_reference` to
tell orders apart internally — it always used its own generated order ID for that
(see ADR-0011). So this constraint alone only protects the reporting table; the primary
check is `OrderService.place_order` (`DuplicateOrderReference`), which refuses a submission
up front. This constraint is the backstop for the narrow race window that check documents:
two near-simultaneous submissions with the same number can both pass the app-level check
before either one's projection exists. See `PostgresOrderProjectionStore.create`, which
catches the `IntegrityError` this constraint raises and drops that one projection row
instead of retrying.

Revision ID: 0009_order_number_unique
Revises: 0008_increment5
Create Date: 2026-10-04
"""

from __future__ import annotations

from alembic import op

revision = "0009_order_number_unique"
down_revision = "0008_increment5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE orders ADD CONSTRAINT orders_tenant_client_reference_key
            UNIQUE (tenant_id, client_reference);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE orders DROP CONSTRAINT orders_tenant_client_reference_key;
        """
    )
