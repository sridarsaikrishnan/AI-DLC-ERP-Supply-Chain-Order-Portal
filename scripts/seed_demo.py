"""Seed demo data for local development (idempotent).

Inserts one local Odoo connection, a VERIFIED binding for a demo tenant, and a couple of
owned items — enough to place an order end-to-end once the api/worker hosts land (Phase 2).
Run after `alembic upgrade head`.

Usage:
    DATABASE_URL=postgresql+psycopg2://portal:portal@localhost:5432/portal python -m scripts.seed_demo
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text

_STATEMENTS = [
    text(
        """
        INSERT INTO erp_connections
            (connection_id, erp_type, instance_label, base_url, database, username, secret_ref,
             webhook_secret_ref, status)
        VALUES
            ('conn_odoo_local', 'ODOO', 'Local Odoo (dev)', 'http://odoo:8069', 'odoo', 'admin',
             'local:odoo-admin-secret', 'local:odoo-webhook-demo-secret', 'ACTIVE')
        ON CONFLICT (connection_id) DO UPDATE SET webhook_secret_ref = EXCLUDED.webhook_secret_ref
        """
    ),
    text(
        """
        INSERT INTO tenant_connection_bindings
            (binding_id, tenant_id, connection_id, erp_customer_id, status)
        VALUES
            ('bind_demo', 'tnt_demo', 'conn_odoo_local', 'CUST-DEMO-1', 'VERIFIED')
        ON CONFLICT (binding_id) DO NOTHING
        """
    ),
    text(
        """
        INSERT INTO items (item_id, sku, name, owning_connection_id) VALUES
            ('item_anvil', 'ANVIL', 'Acme Anvil', 'conn_odoo_local'),
            ('item_spring', 'SPRING', 'Acme Spring', 'conn_odoo_local')
        ON CONFLICT (item_id) DO NOTHING
        """
    ),
]


def main() -> None:
    url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://portal:portal@localhost:5432/portal")
    engine = create_engine(url, future=True)
    with engine.begin() as connection:
        for statement in _STATEMENTS:
            connection.execute(statement)
    print("demo data seeded (connection + verified binding + items)")


if __name__ == "__main__":
    main()
