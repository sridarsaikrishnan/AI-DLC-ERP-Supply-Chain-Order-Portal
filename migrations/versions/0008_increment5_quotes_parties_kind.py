"""Increment 5 schema.

- Catalog becomes product-only (ADR-0016, superseding ADR-0011/0013): drop
  items.unit_price/currency/tax_rate/line_discount; add items.kind (box vs. license).
- Named parties on the order (FR-C): orders gains quote_id/operating_company_id/
  end_customer_name/ship_to.
- Quote-before-order (FR-B) + the office card (FR-C3): new operating_companies and
  quotes tables.

Per-line fulfillment facts (shipped/delivered/invoiced quantities, scheduled/vendor date)
live inside the existing orders.lines JSONB — no DDL needed for those; old rows read with
safe defaults.

Dev/PoC data stance (consistent with prior increments): dropping the item price columns
does not preserve their data — price lives on quotes now, and there is no production
catalog-price data to migrate.

Revision ID: 0008_increment5
Revises: 0007_item_tax_discount
Create Date: 2026-10-03
"""

from __future__ import annotations

from alembic import op

revision = "0008_increment5"
down_revision = "0007_item_tax_discount"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        -- catalog: product-only
        ALTER TABLE items ADD COLUMN kind TEXT NOT NULL DEFAULT 'PHYSICAL';
        ALTER TABLE items DROP COLUMN IF EXISTS unit_price;
        ALTER TABLE items DROP COLUMN IF EXISTS currency;
        ALTER TABLE items DROP COLUMN IF EXISTS tax_rate;
        ALTER TABLE items DROP COLUMN IF EXISTS line_discount;

        -- order parties
        ALTER TABLE orders ADD COLUMN quote_id TEXT NOT NULL DEFAULT '';
        ALTER TABLE orders ADD COLUMN operating_company_id TEXT NOT NULL DEFAULT '';
        ALTER TABLE orders ADD COLUMN end_customer_name TEXT NOT NULL DEFAULT '';
        ALTER TABLE orders ADD COLUMN ship_to TEXT NOT NULL DEFAULT '';

        -- office card
        CREATE TABLE operating_companies (
            operating_company_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            language TEXT NOT NULL
        );

        -- quotes (lines in JSONB, same pattern as orders.lines)
        CREATE TABLE quotes (
            quote_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            operating_company_id TEXT NOT NULL,
            end_customer_name TEXT NOT NULL,
            ship_to TEXT NOT NULL,
            currency TEXT NOT NULL,
            valid_from DATE NOT NULL,
            valid_until DATE NOT NULL,
            status TEXT NOT NULL,
            lines JSONB NOT NULL DEFAULT '[]'::jsonb
        );
        CREATE INDEX ix_quotes_tenant ON quotes (tenant_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS quotes;
        DROP TABLE IF EXISTS operating_companies;

        ALTER TABLE orders DROP COLUMN IF EXISTS quote_id;
        ALTER TABLE orders DROP COLUMN IF EXISTS operating_company_id;
        ALTER TABLE orders DROP COLUMN IF EXISTS end_customer_name;
        ALTER TABLE orders DROP COLUMN IF EXISTS ship_to;

        ALTER TABLE items DROP COLUMN IF EXISTS kind;
        ALTER TABLE items ADD COLUMN unit_price TEXT;
        ALTER TABLE items ADD COLUMN currency TEXT;
        ALTER TABLE items ADD COLUMN tax_rate JSONB;
        ALTER TABLE items ADD COLUMN line_discount TEXT;
        """
    )
