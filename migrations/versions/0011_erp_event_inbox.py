"""Raw inbox for authenticated inbound ERP webhooks.

`body` is the request bytes. Nothing in this table is parsed out of the payload,
because the next ERP may not send JSON or the fields this one sends.

Revision ID: 0011_erp_event_inbox
Revises: 0010_erp_routing_drop_catalog
Create Date: 2026-10-09
"""

from __future__ import annotations

from alembic import op

revision = "0011_erp_event_inbox"
down_revision = "0010_erp_routing_drop_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE erp_event_inbox (
            inbox_id        TEXT PRIMARY KEY,
            connection_id   TEXT NOT NULL,
            received_at     TIMESTAMPTZ NOT NULL,
            body            BYTEA NOT NULL
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE erp_event_inbox;")
