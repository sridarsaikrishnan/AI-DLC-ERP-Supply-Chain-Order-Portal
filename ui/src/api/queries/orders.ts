export interface Money {
  amount: number;
  currency: string;
}

export interface OrderLine {
  productKey: string;
  quantity: number;
  unitOfMeasure: string;
  unitPrice: Money | null;
  lineTotal: Money | null;
}

// What a reseller actually submits — no price. The server resolves unitPrice from the
// catalog at submission time (OrderService._priced); trusting a client-supplied price
// would be a real security hole, not just an unused field.
export interface OrderLineInput {
  productKey: string;
  quantity: number;
  unitOfMeasure: string;
}

export interface TimelineEntry {
  status: string;
  occurredAt: string;
}

export interface ResellerOrder {
  orderId: string;
  clientReference: string;
  status: string;
  lines: OrderLine[];
  timeline: TimelineEntry[];
  subtotal: Money | null;
}

export const ORDERS_QUERY = /* GraphQL */ `
  query Orders {
    orders {
      orderId
      clientReference
      status
      lines { productKey quantity unitOfMeasure unitPrice { amount currency } lineTotal { amount currency } }
      timeline { status occurredAt }
      subtotal { amount currency }
    }
  }
`;

export const ORDER_QUERY = /* GraphQL */ `
  query Order($orderId: String!) {
    order(orderId: $orderId) {
      orderId
      clientReference
      status
      lines { productKey quantity unitOfMeasure unitPrice { amount currency } lineTotal { amount currency } }
      timeline { status occurredAt }
      subtotal { amount currency }
    }
  }
`;

export const PLACE_ORDER_MUTATION = /* GraphQL */ `
  mutation PlaceOrder($ref: String!, $lines: [OrderLineInput!]!) {
    placeOrder(clientReference: $ref, lines: $lines)
  }
`;

export const CANCEL_ORDER_MUTATION = /* GraphQL */ `
  mutation CancelOrder($orderId: String!, $reason: String!) {
    cancelOrder(orderId: $orderId, reason: $reason)
  }
`;
