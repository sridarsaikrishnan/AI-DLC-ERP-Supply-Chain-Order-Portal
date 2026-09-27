import { useState } from "react";
import { Link } from "react-router-dom";

import { StatusBadge } from "../../components/StatusBadge";
import { useDeliveryLog } from "../../hooks/useWebhooks";
import type { WebhookDelivery } from "../../api/queries/webhooks";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function DeliveryLogPage() {
  const { data: deliveries, isLoading, error } = useDeliveryLog();
  const [selected, setSelected] = useState<WebhookDelivery | null>(null);

  const sorted = [...(deliveries ?? [])].sort((a, b) => b.occurredAt.localeCompare(a.occurredAt));
  const active = selected ?? sorted[0] ?? null;

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Delivery log</h1>
          <p>Every notification we sent to your endpoints, with the payload, attempts, and response.</p>
        </div>
      </div>
      {error && <div className="callout callout--danger">Could not load the delivery log: {error.message}</div>}
      <div className="split">
        <div className="erp-table-wrap">
          <table className="erp-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Event</th>
                <th>Order</th>
                <th>Status</th>
                <th className="num">Attempts</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={5} className="muted">
                    Loading…
                  </td>
                </tr>
              )}
              {!isLoading && sorted.length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">
                    No deliveries yet
                  </td>
                </tr>
              )}
              {sorted.map((d) => (
                <tr key={d.deliveryId} aria-selected={active === d} onClick={() => setSelected(d)} style={{ cursor: "pointer" }}>
                  <td className="id">{formatTime(d.occurredAt)}</td>
                  <td className="id">{d.eventType}</td>
                  <td className="id">{d.orderId}</td>
                  <td>
                    <StatusBadge status={d.status === "DELIVERED" ? "Delivered" : d.status === "RETRYING" ? "Retrying" : "Failed"} />
                  </td>
                  <td className="num">{d.attempts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <section className="panel" aria-label="Delivery detail">
          <div className="panel-head">
            <h2>Delivery detail</h2>
            {active && <StatusBadge status={active.status === "DELIVERED" ? "Delivered" : active.status === "RETRYING" ? "Retrying" : "Failed"} />}
          </div>
          {active ? (
            <>
              <dl className="kv">
                <dt>Event</dt>
                <dd className="mono">{active.eventType}</dd>
                <dt>Order</dt>
                <dd>
                  <Link className="mono" to={`/orders/${active.orderId}`}>
                    {active.orderId}
                  </Link>
                </dd>
                <dt>Attempts</dt>
                <dd>{active.attempts}</dd>
                <dt>Last response</dt>
                <dd className="mono">{active.lastResponse ?? "—"}</dd>
              </dl>
              <div className="heading" style={{ font: "600 14px/20px var(--font-sans)" }}>
                Payload
              </div>
              <pre className="code">{JSON.stringify(active.payload, null, 2)}</pre>
            </>
          ) : (
            <p className="muted">Select a delivery to see its payload.</p>
          )}
        </section>
      </div>
    </>
  );
}
