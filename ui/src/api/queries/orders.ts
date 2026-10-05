export interface Money {
  // string, not number: the server sends Decimal-exact money as a string (fixed
  // 2026-10-04 — float couldn't represent e.g. 19.99 exactly). Parse with Number()
  // only for display formatting, never for further arithmetic.
  amount: string;
  currency: string;
}

export interface OrderLine {
  lineId: string;
  productKey: string;
  quantity: number;
  unitOfMeasure: string;
  kind: string; // PHYSICAL (box) | LICENSE
  unitPrice: Money | null;
  lineTotal: Money | null;
  shippedQuantity: number;
  deliveredQuantity: number;
  invoicedQuantity: number;
  scheduledDate: string | null; // vendor date — what "scheduled" means
}

// What a reseller submits: the quote being replied to + line quantities. No price and no
// unit of measure — both come from the quote (ADR-0016). Trusting a client-supplied price
// would be a real security hole, not just an unused field.
export interface OrderLineInput {
  productKey: string;
  quantity: number;
}

export interface TimelineEntry {
  status: string;
  occurredAt: string;
}

export interface Parties {
  endCustomerName: string;
  shipTo: string;
  subsidiaryId: string;
  quoteId: string;
}

export interface ResellerOrder {
  orderId: string;
  clientReference: string;
  status: string;
  lines: OrderLine[];
  timeline: TimelineEntry[];
  subtotal: Money | null;
  fulfillmentStatus: string;
  deliveryStatus: string;
  invoiceStatus: string;
  parties: Parties;
}

export interface QuoteLine {
  productKey: string;
  name: string;
  kind: string;
  unitPrice: Money;
  unitOfMeasure: string;
}

export interface Quote {
  quoteId: string;
  subsidiaryId: string;
  endCustomerName: string;
  shipTo: string;
  currency: string;
  validFrom: string;
  validUntil: string;
  status: string;
  lines: QuoteLine[];
}

const ORDER_FIELDS = /* GraphQL */ `
  orderId
  clientReference
  status
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

export const ORDERS_QUERY = /* GraphQL */ `
  query Orders { orders { ${ORDER_FIELDS} } }
`;

export const ORDER_QUERY = /* GraphQL */ `
  query Order($orderId: String!) { order(orderId: $orderId) { ${ORDER_FIELDS} } }
`;

export const QUOTES_QUERY = /* GraphQL */ `
  query Quotes {
    quotes {
      quoteId subsidiaryId endCustomerName shipTo currency validFrom validUntil status
      lines { productKey name kind unitPrice { amount currency } unitOfMeasure }
    }
  }
`;

export const PLACE_ORDER_MUTATION = /* GraphQL */ `
  mutation PlaceOrder($quoteId: String!, $ref: String!, $lines: [OrderLineInput!]!) {
    placeOrder(quoteId: $quoteId, clientReference: $ref, lines: $lines)
  }
`;

export const CANCEL_ORDER_MUTATION = /* GraphQL */ `
  mutation CancelOrder($orderId: String!, $reason: String!) {
    cancelOrder(orderId: $orderId, reason: $reason)
  }
`;
