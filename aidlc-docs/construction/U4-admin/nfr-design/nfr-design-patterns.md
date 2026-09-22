# NFR Design Patterns — U4 Admin & Configuration

Inherits U0/U1 patterns. U4-specific:
- **P-U4-1 Admin authorization**: every route depends on U1 require_role("ADMIN").
- **P-U4-2 Config repositories**: CRUD over U0 config tables (platform-scoped, not tenant-filtered).
- **P-U4-3 Mapping completeness check**: on mapping save, report unmapped required fields (BR-4.4).
- **P-U4-4 Connectivity check**: delegate to U3 AdapterRegistry.check_connectivity.

## Compliance Summary
- Security: DISABLED — N/A (ADMIN guard present; inline creds per Q7=A flagged). Resiliency: DISABLED — N/A. PBT (Partial): N/A (thin CRUD/config layer); covered by unit tests.
