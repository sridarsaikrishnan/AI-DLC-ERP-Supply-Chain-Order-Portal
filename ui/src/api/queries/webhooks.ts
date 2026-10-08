export interface WebhookDelivery {
  deliveryId: string;
  endpointId: string;
  orderId: string;
  eventType: string;
  occurredAt: string;
  status: string;
  attempts: number;
  lastResponse: string | null;
  payload: Record<string, unknown>;
}

export const DELIVERY_LOG_QUERY = /* GraphQL */ `
  query DeliveryLog {
    deliveryLog { deliveryId endpointId orderId eventType occurredAt status attempts lastResponse payload }
  }
`;
