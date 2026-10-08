import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { graphqlRequest } from "../api/client";
import { CANCEL_ORDER_MUTATION, ORDER_QUERY, type ResellerOrder } from "../api/queries/orders";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";

const LIVE_REFETCH_MS = 5000;

export function useOrder(orderId: string) {
  const { idToken, isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["order", orderId],
    queryFn: () =>
      graphqlRequest<{ order: ResellerOrder | null }, { orderId: string }>("reseller", ORDER_QUERY, { orderId }, idToken).then(
        (d) => d.order,
      ),
    enabled: isAuthenticated && !!orderId,
    refetchInterval: LIVE_REFETCH_MS,
  });
}

export function useCancelOrder() {
  const { idToken } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  return useMutation({
    mutationFn: (input: { orderId: string; reason: string }) =>
      graphqlRequest("reseller", CANCEL_ORDER_MUTATION, input, idToken),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["order", variables.orderId] });
      notify("Order cancelled.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
  });
}
