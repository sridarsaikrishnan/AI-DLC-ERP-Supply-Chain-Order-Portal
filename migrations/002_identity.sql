-- U1 Identity & Access schema (Step 2)

CREATE TABLE IF NOT EXISTS users (
    id        TEXT PRIMARY KEY,
    username  TEXT UNIQUE NOT NULL,
    tenant_id TEXT NOT NULL,
    role      TEXT NOT NULL DEFAULT 'CLIENT_USER',
    status    TEXT NOT NULL DEFAULT 'active'
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

CREATE TABLE IF NOT EXISTS credentials (
    user_id         TEXT PRIMARY KEY,
    password        TEXT NOT NULL,          -- stored as-is for MVP (Q7=A); hash before production
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    throttled_until TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS mfa_enrollments (
    user_id     TEXT PRIMARY KEY,
    totp_secret TEXT NOT NULL,
    enrolled    BOOLEAN NOT NULL DEFAULT TRUE
);

-- PoC seed data (a tenant, an admin, and a client user). Passwords are plaintext per Q7=A.
INSERT INTO tenants (id, name, status) VALUES ('tenant-demo', 'Demo Client', 'active')
    ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, username, tenant_id, role, status) VALUES
    ('user-admin', 'admin', 'tenant-demo', 'ADMIN', 'active'),
    ('user-client', 'client', 'tenant-demo', 'CLIENT_USER', 'active')
    ON CONFLICT (id) DO NOTHING;

INSERT INTO credentials (user_id, password, failed_attempts) VALUES
    ('user-admin', 'admin123', 0),
    ('user-client', 'client123', 0)
    ON CONFLICT (user_id) DO NOTHING;
