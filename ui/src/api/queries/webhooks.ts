export interface WebhookEndpoint {
  endpointId: string;
  name: string;
  url: string;
  eventTypes: string[] | null;
  isActive: boolean;
}

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

export const WEBHOOK_ENDPOINTS_QUERY = /* GraphQL */ `
  query WebhookEndpoints {
    webhookEndpoints { endpointId name url eventTypes isActive }
  }
`;

export const DELIVERY_LOG_QUERY = /* GraphQL */ `
  query DeliveryLog {
    deliveryLog { deliveryId endpointId orderId eventType occurredAt status attempts lastResponse payload }
  }
`;

export const REGISTER_WEBHOOK_ENDPOINT_MUTATION = /* GraphQL */ `
  mutation RegisterWebhookEndpoint($name: String!, $url: String!, $eventTypes: [String!]) {
    registerWebhookEndpoint(name: $name, url: $url, eventTypes: $eventTypes) {
      endpoint { endpointId name url eventTypes isActive }
      signingSecret
    }
  }
`;

export const PAUSE_WEBHOOK_ENDPOINT_MUTATION = /* GraphQL */ `
  mutation PauseWebhookEndpoint($endpointId: String!) {
    pauseWebhookEndpoint(endpointId: $endpointId) { endpointId isActive }
  }
`;

export const RESUME_WEBHOOK_ENDPOINT_MUTATION = /* GraphQL */ `
  mutation ResumeWebhookEndpoint($endpointId: String!) {
    resumeWebhookEndpoint(endpointId: $endpointId) { endpointId isActive }
  }
`;
