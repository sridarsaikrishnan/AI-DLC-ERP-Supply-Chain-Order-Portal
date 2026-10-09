"""One Odoo database belongs to one subsidiary.

Revision ID: 0014_one_odoo_one_subsidiary
Revises: 0013_subsidiary_erp_company
Create Date: 2026-10-09
"""

from __future__ import annotations

from alembic import op

revision = "0014_one_odoo_one_subsidiary"
down_revision = "0013_subsidiary_erp_company"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX subsidiary_routes_connection_uq
            ON subsidiary_routes (connection_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS subsidiary_routes_connection_uq;")
