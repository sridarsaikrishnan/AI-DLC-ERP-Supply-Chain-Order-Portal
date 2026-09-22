# Domain Entities — U2 Ordering & Lifecycle

U2 reuses U0 canonical models and order/status tables. It defines API DTOs (request/response shapes).

## Request DTOs
- `PlaceOrderRequest` — canonical sales order fields (tenant_id ignored; taken from context)
- `AmendRequest` — full amended canonical order
- (Cancel/Resubmit need only the path order id)

## Response DTOs
- `OrderAck` — { order_id, lifecycle_state }
- `OrderView` — { order_id, client_reference, lifecycle_state, erp_reference, created_at }
- `OrderDetailView` — OrderView + line items + latest status
- `StatusHistoryView` — [ { state, reason, occurred_at } ]
- `ProductView`, `InventoryView` — canonical product / availability
- `ActionAck` — { order_id, accepted: true }

## Reused (U0)
- CanonicalSalesOrder / OrderLine, LifecycleState, OrderRow, OrderStatusHistoryRow, tenant-scoped repositories.
