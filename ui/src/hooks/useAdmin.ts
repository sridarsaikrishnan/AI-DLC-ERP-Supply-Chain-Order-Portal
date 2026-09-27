import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { graphqlRequest } from "../api/client";
import {
  BINDINGS_QUERY,
  CONNECTIONS_QUERY,
  CREATE_BINDING_MUTATION,
  ITEMS_QUERY,
  OPERATOR_ORDERS_QUERY,
  OPERATOR_ORDER_QUERY,
  PAUSE_CONNECTION_MUTATION,
  REGISTER_CONNECTION_MUTATION,
  REMOVE_BINDING_MUTATION,
  RESUME_CONNECTION_MUTATION,
  SYNC_ITEM_MUTATION,
  VERIFY_BINDING_MUTATION,
  type Binding,
  type Connection,
  type Item,
  type OperatorOrder,
} from "../api/queries/admin";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";

// Orders move on their own timeline (worker-driven) — poll so status changes show up
// without a manual reload, which is most of what "the UI feels static" complaints were.
const LIVE_REFETCH_MS = 5000;

export function useConnections() {
  const { idToken, isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["connections"],
    queryFn: () => graphqlRequest<{ connections: Connection[] }>("operator", CONNECTIONS_QUERY, {}, idToken).then((d) => d.connections),
    enabled: isAuthenticated,
  });
}

export function useBindings() {
  const { idToken, isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["bindings"],
    queryFn: () => graphqlRequest<{ bindings: Binding[] }>("operator", BINDINGS_QUERY, {}, idToken).then((d) => d.bindings),
    enabled: isAuthenticated,
  });
}

export function useItems() {
  const { idToken, isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["items"],
    queryFn: () => graphqlRequest<{ items: Item[] }>("operator", ITEMS_QUERY, {}, idToken).then((d) => d.items),
    enabled: isAuthenticated,
  });
}

export function useOperatorOrder(orderId: string) {
  const { idToken, isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["operatorOrder", orderId],
    queryFn: () =>
      graphqlRequest<{ order: OperatorOrder | null }, { orderId: string }>("operator", OPERATOR_ORDER_QUERY, { orderId }, idToken).then(
        (d) => d.order,
      ),
    enabled: isAuthenticated && !!orderId,
    refetchInterval: LIVE_REFETCH_MS,
  });
}

export function useOperatorOrders() {
  const { idToken, isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["operatorOrders"],
    queryFn: () =>
      graphqlRequest<{ orders: OperatorOrder[] }>("operator", OPERATOR_ORDERS_QUERY, {}, idToken).then((d) => d.orders),
    enabled: isAuthenticated,
    refetchInterval: LIVE_REFETCH_MS,
  });
}

export function useRegisterConnection() {
  const { idToken } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  return useMutation({
    mutationFn: (input: {
      erpType: string;
      instanceLabel: string;
      baseUrl: string;
      database: string;
      username: string;
      secretRef: string;
      webhookSecretRef?: string;
    }) => graphqlRequest("operator", REGISTER_CONNECTION_MUTATION, input, idToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connections"] });
      notify("Connection registered.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
  });
}

export function usePauseConnection() {
  const { idToken } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  return useMutation({
    mutationFn: (input: { connectionId: string }) => graphqlRequest("operator", PAUSE_CONNECTION_MUTATION, input, idToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connections"] });
      notify("Connection paused — new orders will not be routed to it.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
  });
}

export function useResumeConnection() {
  const { idToken } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  return useMutation({
    mutationFn: (input: { connectionId: string }) => graphqlRequest("operator", RESUME_CONNECTION_MUTATION, input, idToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connections"] });
      notify("Connection resumed.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
  });
}

export function useCreateBinding() {
  const { idToken } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  return useMutation({
    mutationFn: (input: { tenantId: string; connectionId: string; erpCustomerId: string }) =>
      graphqlRequest("operator", CREATE_BINDING_MUTATION, input, idToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bindings"] });
      notify("Reseller linked to connection.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
  });
}

export function useVerifyBinding() {
  const { idToken } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  return useMutation({
    mutationFn: (input: { bindingId: string }) => graphqlRequest("operator", VERIFY_BINDING_MUTATION, input, idToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bindings"] });
      notify("Customer link verified.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
  });
}

export function useRemoveBinding() {
  const { idToken } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  return useMutation({
    mutationFn: (input: { bindingId: string }) => graphqlRequest("operator", REMOVE_BINDING_MUTATION, input, idToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bindings"] });
      notify("Customer link removed.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
  });
}

export function useSyncItem() {
  const { idToken } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  return useMutation({
    mutationFn: (input: { sku: string; name: string; owningConnectionId: string }) =>
      graphqlRequest("operator", SYNC_ITEM_MUTATION, input, idToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["items"] });
      notify("Item saved.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
  });
}
