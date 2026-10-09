"""The distributor on an adopted order is the company on the quotation.

`subsidiary_routes.erp_company_id` is that company's id inside the connection
(Odoo: `res.company` id). Adopt matches it. A blank id matches nothing.

Revision ID: 0013_subsidiary_erp_company
Revises: 0012_drop_audit_log
Create Date: 2026-10-09
"""

from __future__ import annotations

from alembic import op

revision = "0013_subsidiary_erp_company"
down_revision = "0012_drop_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE subsidiary_routes
            ADD COLUMN erp_company_id TEXT NOT NULL DEFAULT '';
        CREATE UNIQUE INDEX subsidiary_routes_connection_company_uq
            ON subsidiary_routes (connection_id, erp_company_id)
            WHERE erp_company_id <> '';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS subsidiary_routes_connection_company_uq;
        ALTER TABLE subsidiary_routes DROP COLUMN IF EXISTS erp_company_id;
        """
    )
