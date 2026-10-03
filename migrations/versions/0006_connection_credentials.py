"""Generalize erp_connections' fixed database/username columns into a credentials JSONB
bag — Odoo's shape (a DB name + username) doesn't fit OAuth-token ERPs (NetSuite,
ERPNext). See ADR (Odoo-perspective genericization work) and `ErpTarget`/`ErpConnection`.

Revision ID: 0006_connection_credentials
Revises: 0005_item_price
Create Date: 2026-10-03
"""

from __future__ import annotations

from alembic import op

revision = "0006_connection_credentials"
down_revision = "0005_item_price"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE erp_connections ADD COLUMN credentials JSONB NOT NULL DEFAULT '{}'::jsonb;
        UPDATE erp_connections
            SET credentials = jsonb_build_object('database', database, 'username', username);
        ALTER TABLE erp_connections DROP COLUMN database;
        ALTER TABLE erp_connections DROP COLUMN username;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE erp_connections ADD COLUMN database TEXT NOT NULL DEFAULT '';
        ALTER TABLE erp_connections ADD COLUMN username TEXT NOT NULL DEFAULT '';
        UPDATE erp_connections
            SET database = COALESCE(credentials->>'database', ''),
                username = COALESCE(credentials->>'username', '');
        ALTER TABLE erp_connections DROP COLUMN credentials;
        """
    )
