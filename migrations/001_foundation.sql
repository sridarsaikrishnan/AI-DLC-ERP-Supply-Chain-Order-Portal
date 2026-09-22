-- U0 Platform Foundation schema (Step 8)
-- Applied automatically by the postgres container on first init.

CREATE TABLE IF NOT EXISTS tenants (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS orders (
    id               TEXT PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    client_reference TEXT NOT NULL,
    payload          JSONB NOT NULL DEFAULT '{}'::jsonb,
    lifecycle_state  TEXT NOT NULL DEFAULT 'Submitted',
    erp_reference    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_orders_tenant ON orders (tenant_id);

CREATE TABLE IF NOT EXISTS order_status_history (
    id          TEXT PRIMARY KEY,
    order_id    TEXT NOT NULL,
    tenant_id   TEXT NOT NULL,
    state       TEXT NOT NULL,
    reason      TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_status_order ON order_status_history (order_id);
CREATE INDEX IF NOT EXISTS idx_status_tenant ON order_status_history (tenant_id);

CREATE TABLE IF NOT EXISTS erp_instances (
    id             TEXT PRIMARY KEY,
    erp_type       TEXT NOT NULL,
    display_name   TEXT NOT NULL,
    connection_ref TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS routing_rules (
    id                 TEXT PRIMARY KEY,
    order_index        INTEGER NOT NULL,
    conditions         JSONB NOT NULL DEFAULT '[]'::jsonb,
    target_instance_id TEXT NOT NULL,
    enabled            BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS mapping_definitions (
    id            TEXT PRIMARY KEY,
    instance_id   TEXT NOT NULL,
    data_type     TEXT NOT NULL,
    direction     TEXT NOT NULL,
    field_entries JSONB NOT NULL DEFAULT '[]'::jsonb,
    expressions   JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT PRIMARY KEY,
    type            TEXT NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    tenant_id       TEXT NOT NULL,
    dedupe_key      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PENDING',
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    max_attempts    INTEGER NOT NULL DEFAULT 5,
    next_visible_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    correlation_id  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_jobs_due ON jobs (status, next_visible_at);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    dedupe_key TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
