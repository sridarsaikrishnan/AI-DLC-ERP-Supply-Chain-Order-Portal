# Deployment Architecture — U2 Ordering & Lifecycle

Topology unchanged from U0 (Nginx -> 2 app replicas -> shared PostgreSQL). U2 adds client-facing order/catalog/inventory endpoints served by the same replicas. See `U0-foundation/infrastructure-design/deployment-architecture.md`.
