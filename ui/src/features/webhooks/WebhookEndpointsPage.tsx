import { useState, type FormEvent } from "react";

import { DataTable, type Column } from "../../components/DataTable";
import { InfoTag } from "../../components/InfoTag";
import { useToast } from "../../components/Toast";
import { usePauseWebhookEndpoint, useRegisterWebhookEndpoint, useResumeWebhookEndpoint, useWebhookEndpoints } from "../../hooks/useWebhooks";
import type { WebhookEndpoint } from "../../api/queries/webhooks";

export function WebhookEndpointsPage() {
  const { data: endpoints, isLoading, error } = useWebhookEndpoints();
  const registerEndpoint = useRegisterWebhookEndpoint();
  const pauseEndpoint = usePauseWebhookEndpoint();
  const resumeEndpoint = useResumeWebhookEndpoint();
  const { notify } = useToast();
  const [form, setForm] = useState({ name: "", url: "" });
  const [showForm, setShowForm] = useState(false);
  const [justCreatedSecret, setJustCreatedSecret] = useState<string | null>(null);

  const columns: Column<WebhookEndpoint>[] = [
    { key: "name", header: "Name", render: (e) => e.name },
    { key: "url", header: "URL", render: (e) => <span className="id">{e.url}</span> },
    { key: "events", header: "Events", render: (e) => (e.eventTypes ? e.eventTypes.join(", ") : "All events") },
    {
      key: "status",
      header: "Status",
      render: (e) => <span className={`erp-badge erp-badge--${e.isActive ? "success" : "neutral"}`}>{e.isActive ? "Active" : "Paused"}</span>,
    },
    {
      key: "actions",
      header: "",
      render: (e) =>
        e.isActive ? (
          <button className="erp-btn erp-btn--ghost erp-btn--sm" type="button" onClick={() => pauseEndpoint.mutate({ endpointId: e.endpointId })}>
            Pause
          </button>
        ) : (
          <button className="erp-btn erp-btn--ghost erp-btn--sm" type="button" onClick={() => resumeEndpoint.mutate({ endpointId: e.endpointId })}>
            Resume
          </button>
        ),
    },
  ];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const result = await registerEndpoint.mutateAsync({ name: form.name, url: form.url });
    setJustCreatedSecret(result.signingSecret);
    setForm({ name: "", url: "" });
    setShowForm(false);
  }

  function copySecret() {
    if (!justCreatedSecret) return;
    navigator.clipboard?.writeText(justCreatedSecret).then(() => notify("Copied."));
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Webhook endpoints</h1>
          <p>Where we send order notifications. Each request is signed so your system can confirm it came from us.</p>
        </div>
        <div className="actions">
          <button className="erp-btn erp-btn--primary" type="button" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "Add endpoint"}
          </button>
        </div>
      </div>
      {justCreatedSecret && (
        <div className="callout callout--info" role="status">
          <span>
            <strong>Endpoint created.</strong> Copy the signing secret now. We will not show it again.
          </span>
          <span className="mono" style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {justCreatedSecret}
            <button className="erp-btn erp-btn--sm erp-btn--secondary" type="button" onClick={copySecret}>
              Copy
            </button>
          </span>
        </div>
      )}
      {showForm && (
        <form className="panel stack" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="name">Name</label>
            <input className="input" id="name" placeholder="Procurement system" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div className="field">
            <label htmlFor="url">
              Endpoint URL <InfoTag text="Must be reachable from this server. We send a signed POST request with a JSON body." />
            </label>
            <input
              className="input"
              id="url"
              type="url"
              placeholder="https://"
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
              required
            />
          </div>
          {registerEndpoint.error && <div className="callout callout--danger">{(registerEndpoint.error as Error).message}</div>}
          <div className="actions" style={{ justifyContent: "flex-end" }}>
            <button className="erp-btn erp-btn--primary" type="submit" disabled={registerEndpoint.isPending}>
              {registerEndpoint.isPending ? "Creating…" : "Create endpoint"}
            </button>
          </div>
        </form>
      )}
      {error && <div className="callout callout--danger">Could not load endpoints: {error.message}</div>}
      <DataTable columns={columns} rows={endpoints ?? []} rowKey={(e) => e.endpointId} emptyMessage={isLoading ? "Loading…" : "No endpoints yet"} />
    </>
  );
}
