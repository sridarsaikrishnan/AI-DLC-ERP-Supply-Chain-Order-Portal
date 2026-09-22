# Deployment Architecture — U4 Admin & Configuration

Topology unchanged (Nginx -> 2 app replicas -> shared PostgreSQL). U4 adds `/admin/*` endpoints on the same replicas. Config tables already exist from U0 migration 001. See `U0-foundation/infrastructure-design/deployment-architecture.md`.
