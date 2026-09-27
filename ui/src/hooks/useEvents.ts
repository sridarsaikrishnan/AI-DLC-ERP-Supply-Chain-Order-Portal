import { useQuery } from "@tanstack/react-query";

import { graphqlRequest } from "../api/client";
import { ORDER_EVENTS_QUERY, type OrderEvent } from "../api/queries/events";
import { useAuth } from "../auth/AuthContext";

export function useOrderEvents(orderId: string) {
  const { idToken, isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["orderEvents", orderId],
    queryFn: () =>
      graphqlRequest<{ orderEvents: OrderEvent[] }, { orderId: string }>("operator", ORDER_EVENTS_QUERY, { orderId }, idToken).then(
        (d) => d.orderEvents,
      ),
    enabled: isAuthenticated && !!orderId,
  });
}
