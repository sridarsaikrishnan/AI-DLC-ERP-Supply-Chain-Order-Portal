# `shared/eventsourcing` — the event-sourcing kernel

A small, **dependency-free** core that domain services reuse. It is the shared kernel;
it contains **no business logic and no infrastructure** (no boto3, no SQLAlchemy, no web
framework).

## What's here
- `DomainEvent` — base for immutable domain facts (frozen, kw-only dataclass).
- `Aggregate` — base for aggregate roots; state changes ONLY by applying events.
- `StoredEvent` — the persisted/transported envelope (payload + metadata).
- `EventStore` (port) + `InMemoryEventStore` — append with optimistic concurrency, load, snapshots.
- `EventSourcedRepository[A]` — rebuild by replay (+ snapshot), save by append (+ outbox/publish).
- `Outbox` / `EventPublisher` (ports) + in-memory/collecting/null impls.
- `Snapshot`, `register_event`, and typed errors.

## How a domain service uses it
```python
@register_event
@dataclass(frozen=True, kw_only=True)
class Incremented(DomainEvent):
    by: int

class Counter(Aggregate):
    aggregate_type = "Counter"
    def __init__(self, id: str) -> None:
        super().__init__(id); self.total = 0
    def increment(self, by: int) -> None:      # behavior + invariant
        if by <= 0: raise ValueError("by must be positive")
        self.emit(Incremented(by=by))
    def _apply_Incremented(self, e: Incremented) -> None:
        self.total += e.by

repo = EventSourcedRepository(InMemoryEventStore(), Counter)
c = Counter("counter-1"); c.increment(5); repo.save(c)
same = repo.get("counter-1")   # total == 5, rebuilt from events
```

## Rules that keep it clean (and the anti-patterns we avoid)
- **Behavior in the aggregate, not services.** Services orchestrate; the aggregate decides and `emit`s. (Avoids the anemic-domain anti-pattern.)
- **Only event-source aggregates that need it.** `Order` uses this kernel; CRUD aggregates (connections, bindings, items) do not. The kernel is shared; event-sourcing is not mandatory. (Avoids "event sourcing everywhere".)
- **No domain types in the kernel.** It stays generic and stable. (Avoids the god/shared-mutable-kernel anti-pattern.)
- **The store is the only persistence seam.** Swap in-memory ↔ Postgres behind `EventStore`; domain never knows. (Avoids vendor lock-in.)
- **Kernel is thin.** It does not wrap a heavyweight ES framework — so we are not double-abstracting one.

## Production note
The in-memory store/outbox/publisher power tests and simple local runs. Postgres event
store + SNS-FIFO publisher adapters (in `shared/messaging` + `infrastructure`) implement the
same ports in Phase 2/3 — no domain change.
