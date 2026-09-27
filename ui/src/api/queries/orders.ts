export interface OrderLine {
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
}

export const ORDERS_QUERY = /* GraphQL */ `
  query Orders {
    orders {
      orderId
      clientReference
      status
      lines { productKey quantity unitOfMeasure }
      timeline { status occurredAt }
    }
  }
`;

export const ORDER_QUERY = /* GraphQL */ `
  query Order($orderId: String!) {
    order(orderId: $orderId) {
      orderId
      clientReference
      status
      lines { productKey quantity unitOfMeasure }
      timeline { status occurredAt }
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
