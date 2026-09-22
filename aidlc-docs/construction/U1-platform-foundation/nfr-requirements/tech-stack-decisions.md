# Tech Stack Decisions — U1 Platform Foundation

U1 library choices (Q3=A), consistent with `requirements.md` Section 5. These are the concrete dependencies the foundation introduces; other units reuse them.

| Concern | Choice | Rationale |
|---|---|---|
| Language / runtime | Java 21, Spring Boot 3.x | Section 5 decision |
| Event sourcing + CQRS | **Axon Framework** (open source), **PostgreSQL JPA/JDBC event store**, **no Axon Server** | ES/CQRS machinery without extra infra/licensing; RDS-hosted event store |
| Persistence (reference/config + projections) | Spring Data JPA + Hibernate; **Flyway** migrations | Standard, matches relational domain |
| AuthN | **Spring Security OAuth2 Resource Server** validating Cognito JWTs (JWKS) | Standard OIDC JWT validation (SECURITY-08) |
| Identifiers | ULID / UUIDv7 library for prefixed IDs (`ord_`, `conn_`, …) | Time-sortable, opaque (BR-U1-08) |
| Internal object mapping | **MapStruct** (or hand-written mappers) | entity ↔ DTO ↔ GraphQL type mapping only |
| Testing | **JUnit 5**, **jqwik** (PBT-09), **Testcontainers**, AssertJ | unit + property-based + integration with real Postgres |
| Static analysis / arch | SpotBugs, Checkstyle/Spotless, **ArchUnit** | quality + module-boundary enforcement (NFR-U1-M3) |
| Observability | OpenTelemetry SDK (OTLP) | metrics/traces/logs (NFR-07) |
| Crypto | JDK AES-GCM (`javax.crypto`), key via Secrets Manager/KMS | ERP credential encryption (BR-U1-20) |

## Critical clarification — two different "mappings" (do not conflate)
- **MapStruct** handles **internal object mapping**: JPA entity ↔ DTO ↔ GraphQL type. Compile-time, type-safe, within the platform.
- The **`DeclarativeMappingEngine`** (U2) handles **ERP canonical ↔ native** transformation, driven by **version-controlled declarative field maps** (application-design Q2=B). This is configuration executed at runtime, **not** MapStruct.
- These are distinct. MapStruct must never be used for canonical↔ERP mapping, and the MappingEngine is never replaced by MapStruct. Code Generation must keep them separate.

## Notes
- PBT framework confirmation (PBT-09): jqwik selected for Java; declared as a project dependency in the Gradle build.
- No new AWS-only runtime dependency is introduced by U1 beyond the AWS-native decisions already made (Cognito/SQS/SNS via infrastructure ports).
