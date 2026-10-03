import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { graphqlRequest } from "../api/client";
import {
  CANCEL_ORDER_MUTATION,
  ORDERS_QUERY,
  ORDER_QUERY,
  PLACE_ORDER_MUTATION,
  QUOTES_QUERY,
  type OrderLineInput,
  type Quote,
  type ResellerOrder,
} from "../api/queries/orders";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";

// Orders move on their own timeline (worker-driven) — poll so status changes show up
// without a manual reload.
const LIVE_REFETCH_MS = 5000;

export function useOrders() {
  const { idToken, isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["orders"],
    queryFn: () => graphqlRequest<{ orders: ResellerOrder[] }>("reseller", ORDERS_QUERY, {}, idToken).then((d) => d.orders),
    enabled: isAuthenticated,
    refetchInterval: LIVE_REFETCH_MS,
  });
}

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

export function useQuotes() {
  const { idToken, isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["quotes"],
    queryFn: () => graphqlRequest<{ quotes: Quote[] }>("reseller", QUOTES_QUERY, {}, idToken).then((d) => d.quotes),
    enabled: isAuthenticated,
  });
}

export function usePlaceOrder() {
  const { idToken } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  return useMutation({
    mutationFn: (input: { quoteId: string; ref: string; lines: OrderLineInput[] }) =>
      graphqlRequest("reseller", PLACE_ORDER_MUTATION, input, idToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      notify("Order submitted.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
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
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["order", variables.orderId] });
      notify("Order cancelled.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
  });
}
