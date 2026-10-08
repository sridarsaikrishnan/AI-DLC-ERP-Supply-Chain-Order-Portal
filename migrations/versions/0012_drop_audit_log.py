"""Drop audit_log. Nothing in the application reads or writes it.

Revision ID: 0012_drop_audit_log
Revises: 0011_erp_event_inbox
Create Date: 2026-10-09
"""

from __future__ import annotations

from alembic import op

revision = "0012_drop_audit_log"
down_revision = "0011_erp_event_inbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log;")


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE audit_log (
            id          BIGSERIAL PRIMARY KEY,
            actor       TEXT NOT NULL,
            action      TEXT NOT NULL,
            entity      TEXT NOT NULL,
            before      JSONB,
            after       JSONB,
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
