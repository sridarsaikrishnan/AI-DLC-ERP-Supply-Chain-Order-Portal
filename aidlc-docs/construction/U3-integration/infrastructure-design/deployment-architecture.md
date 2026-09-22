# Deployment Architecture — U3 Integration

Topology unchanged from U0 (Nginx -> 2 app replicas -> shared PostgreSQL). U3 adds worker handlers that run inside each replica's poller loop. In MVP, stub adapters mean no outbound ERP calls; when real adapters are added, replicas make outbound HTTPS to ERP instances.

See `U0-foundation/infrastructure-design/deployment-architecture.md` for the diagram. Future: extract U3 as a dedicated worker service (first extraction candidate).
