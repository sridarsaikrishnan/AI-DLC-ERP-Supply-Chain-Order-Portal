import { useQuery } from "@tanstack/react-query";

import { graphqlRequest } from "../api/client";
import { DELIVERY_LOG_QUERY, type WebhookDelivery } from "../api/queries/webhooks";
import { useAuth } from "../auth/AuthContext";

const LIVE_REFETCH_MS = 5000;

export function useDeliveryLog() {
  const { idToken, isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["deliveryLog"],
    queryFn: () =>
      graphqlRequest<{ deliveryLog: WebhookDelivery[] }>("reseller", DELIVERY_LOG_QUERY, {}, idToken).then((d) => d.deliveryLog),
    enabled: isAuthenticated,
    refetchInterval: LIVE_REFETCH_MS,
  });
}
