"""Increment 7: office-to-ERP routing decided at quote-issue time; drop the catalog;
rename "operating company" to "subsidiary" (matches EXN's own BusinessEntity
terminology — SubsidiaryEntity — so the business and the code use one name).

- `operating_companies` (from 0008) is renamed `subsidiaries`; its PK and every
  `operating_company_id` column (`subsidiaries`, `orders`, `quotes`) is renamed
  `subsidiary_id`. Folded into this migration rather than a separate one because 0010
  had not shipped anywhere yet — no data to preserve, no reason to rename twice.
- Routing no longer derives from item ownership at order time — it's decided once, when
  the quote is issued, from the issuing subsidiary's current route. New table
  `subsidiary_routes` (one row per subsidiary = its current route; no separate
  "active" flag needed, since replacing the row *is* switching the route).
- `quotes` gains `routed_to_connection_id`, stamped once at issue time and never
  re-derived.
- The shared catalog (`items`) is dropped entirely. Every quote line now carries its own
  product description (`name`, `kind`) inline, inside `quotes.lines` (JSONB) — no DDL
  needed for that, same as every other per-line fact already living there.

Dev/PoC data stance (consistent with every prior increment's migrations): dropping
`items` does not preserve its data, and existing quotes are not backfilled with
`name`/`kind` on their lines — there is no production data to protect yet.

Revision ID: 0010_erp_routing_drop_catalog
Revises: 0009_order_number_unique
Create Date: 2026-10-05
"""

from __future__ import annotations

from alembic import op

revision = "0010_erp_routing_drop_catalog"
down_revision = "0009_order_number_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE operating_companies RENAME TO subsidiaries;
        ALTER TABLE subsidiaries RENAME COLUMN operating_company_id TO subsidiary_id;
        ALTER TABLE orders RENAME COLUMN operating_company_id TO subsidiary_id;
        ALTER TABLE quotes RENAME COLUMN operating_company_id TO subsidiary_id;

        CREATE TABLE subsidiary_routes (
            subsidiary_id TEXT PRIMARY KEY
                REFERENCES subsidiaries (subsidiary_id),
            connection_id TEXT NOT NULL REFERENCES erp_connections (connection_id)
        );

        ALTER TABLE quotes ADD COLUMN routed_to_connection_id TEXT NOT NULL DEFAULT '';

        DROP TABLE IF EXISTS items;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE TABLE items (
            item_id              TEXT PRIMARY KEY,
            sku                  TEXT NOT NULL UNIQUE,
            name                 TEXT NOT NULL,
            owning_connection_id TEXT NOT NULL REFERENCES erp_connections (connection_id),
            kind                 TEXT NOT NULL DEFAULT 'PHYSICAL'
        );

        ALTER TABLE quotes DROP COLUMN IF EXISTS routed_to_connection_id;

        DROP TABLE IF EXISTS subsidiary_routes;

        ALTER TABLE quotes RENAME COLUMN subsidiary_id TO operating_company_id;
        ALTER TABLE orders RENAME COLUMN subsidiary_id TO operating_company_id;
        ALTER TABLE subsidiaries RENAME COLUMN subsidiary_id TO operating_company_id;
        ALTER TABLE subsidiaries RENAME TO operating_companies;
        """
    )
