# Infrastructure Design — U4 Admin & Configuration

No new infrastructure. Admin router runs in the same app image; uses shared PostgreSQL config tables (from U0 migration 001). Connectivity checks use U3 in-process stub adapters. See `U0-foundation/infrastructure-design/`.

## Extension Compliance
- Security/Resiliency: DISABLED — N/A (ADMIN guard; inline creds per Q7=A flagged).
