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

export const ORDER_QUERY = /* GraphQL */ `
  query Order($orderId: String!) { order(orderId: $orderId) { ${ORDER_FIELDS} } }
`;

export const CANCEL_ORDER_MUTATION = /* GraphQL */ `
  mutation CancelOrder($orderId: String!, $reason: String!) {
    cancelOrder(orderId: $orderId, reason: $reason)
  }
`;
