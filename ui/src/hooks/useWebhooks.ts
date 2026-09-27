import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { graphqlRequest } from "../api/client";
import {
  DELIVERY_LOG_QUERY,
  PAUSE_WEBHOOK_ENDPOINT_MUTATION,
  REGISTER_WEBHOOK_ENDPOINT_MUTATION,
  RESUME_WEBHOOK_ENDPOINT_MUTATION,
  WEBHOOK_ENDPOINTS_QUERY,
  type WebhookDelivery,
  type WebhookEndpoint,
} from "../api/queries/webhooks";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";

const LIVE_REFETCH_MS = 5000;

export function useWebhookEndpoints() {
  const { idToken, isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["webhookEndpoints"],
    queryFn: () =>
      graphqlRequest<{ webhookEndpoints: WebhookEndpoint[] }>("reseller", WEBHOOK_ENDPOINTS_QUERY, {}, idToken).then(
        (d) => d.webhookEndpoints,
      ),
    enabled: isAuthenticated,
  });
}

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

export function useRegisterWebhookEndpoint() {
  const { idToken } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  return useMutation({
    mutationFn: (input: { name: string; url: string; eventTypes?: string[] }) =>
      graphqlRequest<{ registerWebhookEndpoint: { endpoint: WebhookEndpoint; signingSecret: string } }, typeof input>(
        "reseller",
        REGISTER_WEBHOOK_ENDPOINT_MUTATION,
        input,
        idToken,
      ).then((d) => d.registerWebhookEndpoint),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhookEndpoints"] });
      notify("Endpoint created. Copy the signing secret now — it will not be shown again.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
  });
}

export function usePauseWebhookEndpoint() {
  const { idToken } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  return useMutation({
    mutationFn: (input: { endpointId: string }) => graphqlRequest("reseller", PAUSE_WEBHOOK_ENDPOINT_MUTATION, input, idToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhookEndpoints"] });
      notify("Endpoint paused.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
  });
}

export function useResumeWebhookEndpoint() {
  const { idToken } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  return useMutation({
    mutationFn: (input: { endpointId: string }) => graphqlRequest("reseller", RESUME_WEBHOOK_ENDPOINT_MUTATION, input, idToken),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhookEndpoints"] });
      notify("Endpoint resumed.");
    },
    onError: (err) => notify((err as Error).message, "danger"),
  });
}
