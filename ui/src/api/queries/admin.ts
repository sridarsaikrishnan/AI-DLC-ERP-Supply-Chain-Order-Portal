export interface Connection {
  connectionId: string;
  erpType: string;
  instanceLabel: string;
  baseUrl: string;
  database: string;
  username: string;
  status: string;
  secretRef: string;
  hasWebhookSecret: boolean;
}

export interface Binding {
  bindingId: string;
  tenantId: string;
  connectionId: string;
  erpCustomerId: string;
  status: string;
}

export interface Item {
  itemId: string;
  sku: string;
  name: string;
  owningConnectionId: string;
}

export interface OperatorOrder {
  orderId: string;
  tenantId: string;
  clientReference: string;
  status: string;
  owningConnectionId: string | null;
  erpOrderId: string | null;
  lines: { productKey: string; quantity: number; unitOfMeasure: string }[];
  timeline: { status: string; occurredAt: string }[];
}

export const CONNECTIONS_QUERY = /* GraphQL */ `
  query Connections {
    connections { connectionId erpType instanceLabel baseUrl database username status secretRef hasWebhookSecret }
  }
`;

export const BINDINGS_QUERY = /* GraphQL */ `
  query Bindings {
    bindings { bindingId tenantId connectionId erpCustomerId status }
  }
`;

export const ITEMS_QUERY = /* GraphQL */ `
  query Items {
    items { itemId sku name owningConnectionId }
  }
`;

export const OPERATOR_ORDER_QUERY = /* GraphQL */ `
  query OperatorOrder($orderId: String!) {
    order(orderId: $orderId) {
      orderId
      tenantId
      clientReference
      status
      owningConnectionId
      erpOrderId
      lines { productKey quantity unitOfMeasure }
      timeline { status occurredAt }
    }
  }
`;

export const OPERATOR_ORDERS_QUERY = /* GraphQL */ `
  query OperatorOrders {
    orders {
      orderId
      tenantId
      clientReference
      status
      owningConnectionId
      erpOrderId
      lines { productKey quantity unitOfMeasure }
      timeline { status occurredAt }
    }
  }
`;

export const REGISTER_CONNECTION_MUTATION = /* GraphQL */ `
  mutation RegisterConnection(
    $erpType: String!
    $instanceLabel: String!
    $baseUrl: String!
    $database: String!
    $username: String!
    $secretRef: String!
    $webhookSecretRef: String
  ) {
    registerConnection(
      erpType: $erpType
      instanceLabel: $instanceLabel
      baseUrl: $baseUrl
      database: $database
      username: $username
      secretRef: $secretRef
      webhookSecretRef: $webhookSecretRef
    ) {
      connectionId
    }
  }
`;

export const CREATE_BINDING_MUTATION = /* GraphQL */ `
  mutation CreateBinding($tenantId: String!, $connectionId: String!, $erpCustomerId: String!) {
    createBinding(tenantId: $tenantId, connectionId: $connectionId, erpCustomerId: $erpCustomerId) {
      bindingId
    }
  }
`;

export const VERIFY_BINDING_MUTATION = /* GraphQL */ `
  mutation VerifyBinding($bindingId: String!) {
    verifyBinding(bindingId: $bindingId) {
      bindingId
      status
    }
  }
`;

export const SYNC_ITEM_MUTATION = /* GraphQL */ `
  mutation SyncItem($sku: String!, $name: String!, $owningConnectionId: String!) {
    syncItem(sku: $sku, name: $name, owningConnectionId: $owningConnectionId) {
      itemId
    }
  }
`;

export const PAUSE_CONNECTION_MUTATION = /* GraphQL */ `
  mutation PauseConnection($connectionId: String!) {
    pauseConnection(connectionId: $connectionId) {
      connectionId
      status
    }
  }
`;

export const RESUME_CONNECTION_MUTATION = /* GraphQL */ `
  mutation ResumeConnection($connectionId: String!) {
    resumeConnection(connectionId: $connectionId) {
      connectionId
      status
    }
  }
`;

export const REMOVE_BINDING_MUTATION = /* GraphQL */ `
  mutation RemoveBinding($bindingId: String!) {
    removeBinding(bindingId: $bindingId) {
      bindingId
      status
    }
  }
`;
