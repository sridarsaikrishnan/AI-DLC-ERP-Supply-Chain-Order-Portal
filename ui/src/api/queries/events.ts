/** The raw event stream for one order — the developer/event-sourcing view. This is not
 * a projection: it's exactly what's in the `events` table, in order. See
 * docs/event-sourcing-explained.md for why the backend is built this way. */
export interface OrderEvent {
  eventType: string;
  version: number;
  occurredAt: string;
  correlationId: string | null;
  payload: Record<string, unknown>;
}

export const ORDER_EVENTS_QUERY = /* GraphQL */ `
  query OrderEvents($orderId: String!) {
    orderEvents(orderId: $orderId) {
      eventType
      version
      occurredAt
      correlationId
      payload
    }
  }
`;
