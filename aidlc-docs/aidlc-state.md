# AI-DLC State Tracking

## Project Information
- **Project Name**: ERP & Supply Chain Order Portal
- **Project Type**: Greenfield
- **Start Date**: 2026-09-21T00:00:00Z
- **Current Phase**: CONSTRUCTION
- **Current Stage**: U1 Platform Foundation — NFR Design

## Workspace State
- **Existing Code**: No
- **Programming Languages**: None detected
- **Build System**: None detected
- **Project Structure**: Empty (only .kiro/ present)
- **Reverse Engineering Needed**: No
- **Workspace Root**: c:\Users\sridar.cs\erp-platform

## Code Location Rules
- **Application Code**: Workspace root (NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/ only
- **Structure patterns**: See code-generation.md Critical Rules

## Key Technology Decisions (updated 2026-09-21)
- **Backend**: Java 21 + Spring Boot (was .NET)
- **Identity**: Amazon Cognito (was Keycloak) — closes O-10
- **Messaging**: Amazon SQS FIFO + SNS fan-out (was Kafka/MSK); transactional outbox retained
- **Datastore**: RDS PostgreSQL (kept; DynamoDB rejected); Aurora Serverless v2 = upgrade path
- **Local dev**: Floci AWS emulator (Cognito/SQS/SNS) + real PostgreSQL container
- **Principle**: portable-core (NFR-05) retired → AWS-native; emulator not authoritative for security-critical (auth) behavior
- **Event sourcing + CQRS**: adopted 2026-09-21 (reverses earlier "no ES" decision) via **Axon Framework**; the `Order` aggregate is event-sourced (event store on PostgreSQL, no Axon Server); reads from CQRS projections (eventual consistency, NFR-13); reference/config data stays CRUD
- **Axon**: event store = PostgreSQL (JPA/JDBC); command/query buses; projectors build read models

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes | Requirements Analysis |
| Resiliency Baseline | Yes | Requirements Analysis |
| Property-Based Testing | Yes (Full) | Requirements Analysis |

## Stage Progress
### 🔵 INCEPTION PHASE
- [x] Workspace Detection
- [x] Reverse Engineering (SKIPPED - Greenfield)
- [x] Requirements Analysis (approved 2026-09-21; Q29=A, Q30=A confirmed; O-01, O-02 closed)
- [x] User Stories (approved 2026-09-21; 4 personas, 8 epics, 38 stories)
- [x] Workflow Planning (approved 2026-09-21)
- [x] Application Design - EXECUTE (approved 2026-09-21; 7 artifacts incl. canonical-model, events, tenancy-and-routing, status mapping; modules renamed for clarity)
- [x] Units Generation - EXECUTE (approved 2026-09-21; 7 units U1-U7; build sequence = walking skeleton across both ERPs first)

### 🟢 CONSTRUCTION PHASE (per unit; order U1→U2→U3→U4→U5→U6, U7 alongside)
**U1 Platform Foundation**
- [x] Functional Design - approved 2026-09-21
- [x] NFR Requirements - approved 2026-09-21
- [~] NFR Design - in progress
- [ ] NFR Design
- [ ] Infrastructure Design
- [ ] Code Generation
(remaining units U2-U7 follow)
- [ ] Build and Test (after all units)

### 🟡 OPERATIONS PHASE
- [ ] Operations (placeholder)

## Execution Plan Summary
- **Stages to Execute**: Application Design, Units Generation, Functional Design, NFR Requirements, NFR Design, Infrastructure Design, Code Generation, Build and Test
- **Stages Skipped**: Reverse Engineering (greenfield)
- **Risk Level**: High (system-wide greenfield, integrations, guaranteed delivery, blocking Security/Resiliency/PBT)
- **Next Stage**: Application Design
