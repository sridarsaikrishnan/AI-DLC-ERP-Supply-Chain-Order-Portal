export interface Connection {
  connectionId: string;
  erpType: string;
  instanceLabel: string;
  baseUrl: string;
  credentials: Record<string, string>;
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

export interface Money {
  // string, not number: the server sends Decimal-exact money as a string (fixed
  // 2026-10-04 — float couldn't represent e.g. 19.99 exactly). Parse with Number()
  // only for display formatting, never for further arithmetic.
  amount: string;
  currency: string;
}

export interface Subsidiary {
  subsidiaryId: string;
  name: string;
  country: string;
  language: string;
}

export interface OperatorQuoteLine {
  productKey: string;
  name: string;
  kind: string; // PHYSICAL (box) | LICENSE
  unitPrice: Money;
  unitOfMeasure: string;
  taxCode: string | null;
  taxRate: number | null;
  lineDiscount: Money | null;
}

export interface OperatorQuote {
  quoteId: string;
  tenantId: string;
  subsidiaryId: string;
  endCustomerName: string;
  shipTo: string;
  currency: string;
  validFrom: string;
  validUntil: string;
  routedToConnectionId: string;
  status: string;
  lines: OperatorQuoteLine[];
}

export interface OperatorOrderLine {
  lineId: string;
  productKey: string;
  quantity: number;
  unitOfMeasure: string;
  kind: string;
  unitPrice: Money | null;
  lineTotal: Money | null;
  shippedQuantity: number;
  deliveredQuantity: number;
  invoicedQuantity: number;
  scheduledDate: string | null;
}

export interface OperatorOrder {
  orderId: string;
  tenantId: string;
  clientReference: string;
  status: string;
  owningConnectionId: string | null;
  erpOrderId: string | null;
  lines: OperatorOrderLine[];
  timeline: { status: string; occurredAt: string }[];
  subtotal: Money | null;
  fulfillmentStatus: string;
  deliveryStatus: string;
  invoiceStatus: string;
  parties: { endCustomerName: string; shipTo: string; subsidiaryId: string; quoteId: string };
}

export const CONNECTIONS_QUERY = /* GraphQL */ `
  query Connections {
    connections { connectionId erpType instanceLabel baseUrl credentials status secretRef hasWebhookSecret }
  }
`;

export const BINDINGS_QUERY = /* GraphQL */ `
  query Bindings {
    bindings { bindingId tenantId connectionId erpCustomerId status }
  }
`;

export const SUBSIDIARIES_QUERY = /* GraphQL */ `
  query Subsidiaries {
    subsidiaries { subsidiaryId name country language }
  }
`;

export const ERP_ROUTE_QUERY = /* GraphQL */ `
  query ErpRoute($subsidiaryId: String!) {
    erpRoute(subsidiaryId: $subsidiaryId)
  }
`;

export const OPERATOR_QUOTES_QUERY = /* GraphQL */ `
  query OperatorQuotes {
    quotes {
      quoteId tenantId subsidiaryId endCustomerName shipTo currency validFrom validUntil routedToConnectionId status
      lines { productKey name kind unitPrice { amount currency } unitOfMeasure taxCode taxRate lineDiscount { amount currency } }
    }
  }
`;

const OPERATOR_ORDER_FIELDS = /* GraphQL */ `
  orderId
  tenantId
  clientReference
  status
  owningConnectionId
  erpOrderId
  fulfillmentStatus
  deliveryStatus
  invoiceStatus
  parties { endCustomerName shipTo subsidiaryId quoteId }
  lines {
    lineId productKey quantity unitOfMeasure kind
    unitPrice { amount currency } lineTotal { amount currency }
    shippedQuantity deliveredQuantity invoicedQuantity scheduledDate
  }
  timeline { status occurredAt }
  subtotal { amount currency }
`;

export const OPERATOR_ORDER_QUERY = /* GraphQL */ `
  query OperatorOrder($orderId: String!) { order(orderId: $orderId) { ${OPERATOR_ORDER_FIELDS} } }
`;

export const OPERATOR_ORDERS_QUERY = /* GraphQL */ `
  query OperatorOrders { orders { ${OPERATOR_ORDER_FIELDS} } }
`;

export const REGISTER_CONNECTION_MUTATION = /* GraphQL */ `
  mutation RegisterConnection(
    $erpType: String!
    $instanceLabel: String!
    $baseUrl: String!
    $credentials: JSON!
    $secretRef: String!
    $webhookSecretRef: String
  ) {
    registerConnection(
      erpType: $erpType
      instanceLabel: $instanceLabel
      baseUrl: $baseUrl
      credentials: $credentials
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
    verifyBinding(bindingId: $bindingId) { bindingId status }
  }
`;

export const SET_ERP_ROUTE_MUTATION = /* GraphQL */ `
  mutation SetErpRoute($subsidiaryId: String!, $connectionId: String!) {
    setErpRoute(subsidiaryId: $subsidiaryId, connectionId: $connectionId) {
      subsidiaryId
    }
  }
`;

export const PAUSE_CONNECTION_MUTATION = /* GraphQL */ `
  mutation PauseConnection($connectionId: String!) {
    pauseConnection(connectionId: $connectionId) { connectionId status }
  }
`;

export const RESUME_CONNECTION_MUTATION = /* GraphQL */ `
  mutation ResumeConnection($connectionId: String!) {
    resumeConnection(connectionId: $connectionId) { connectionId status }
  }
`;

export const REMOVE_BINDING_MUTATION = /* GraphQL */ `
  mutation RemoveBinding($bindingId: String!) {
    removeBinding(bindingId: $bindingId) { bindingId status }
  }
`;

export const CREATE_SUBSIDIARY_MUTATION = /* GraphQL */ `
  mutation CreateSubsidiary($name: String!, $country: String!, $language: String!) {
    createSubsidiary(name: $name, country: $country, language: $language) {
      subsidiaryId
    }
  }
`;

export interface IssueQuoteLineInput {
  productKey: string;
  name: string;
  kind: string;
  unitPrice: number;
  unitOfMeasure: string;
  taxCode?: string | null;
  taxRate?: number | null;
  taxInclusive?: boolean;
  lineDiscount?: number | null;
}

export const ISSUE_QUOTE_MUTATION = /* GraphQL */ `
  mutation IssueQuote(
    $tenantId: String!
    $subsidiaryId: String!
    $endCustomerName: String!
    $shipTo: String!
    $currency: String!
    $validFrom: String!
    $validUntil: String!
    $lines: [QuoteLineInput!]!
  ) {
    issueQuote(
      tenantId: $tenantId
      subsidiaryId: $subsidiaryId
      endCustomerName: $endCustomerName
      shipTo: $shipTo
      currency: $currency
      validFrom: $validFrom
      validUntil: $validUntil
      lines: $lines
    ) {
      quoteId
    }
  }
`;

export const RECORD_SHIPMENT_MUTATION = /* GraphQL */ `
  mutation RecordShipment(
    $orderId: String!
    $lines: [LineQuantityInput!]!
    $carrier: String
    $trackingNumber: String
    $proofOfDelivery: String
  ) {
    recordShipment(
      orderId: $orderId
      lines: $lines
      carrier: $carrier
      trackingNumber: $trackingNumber
      proofOfDelivery: $proofOfDelivery
    ) {
      shipmentId
    }
  }
`;

export const SET_VENDOR_DATE_MUTATION = /* GraphQL */ `
  mutation SetVendorDate($orderId: String!, $lineId: String!, $vendorDate: String!) {
    setVendorDate(orderId: $orderId, lineId: $lineId, vendorDate: $vendorDate)
  }
`;
