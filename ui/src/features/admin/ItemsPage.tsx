import { useState, type FormEvent } from "react";

import { DataTable, type Column } from "../../components/DataTable";
import { InfoTag } from "../../components/InfoTag";
import { useConnections, useItems, useSyncItem } from "../../hooks/useAdmin";
import type { Item } from "../../api/queries/admin";

export function ItemsPage() {
  const { data: items, isLoading, error } = useItems();
  const { data: connections } = useConnections();
  const syncItem = useSyncItem();
  const EMPTY_FORM = { sku: "", name: "", owningConnectionId: "", kind: "PHYSICAL" };
  const [form, setForm] = useState(EMPTY_FORM);
  const [showForm, setShowForm] = useState(false);

  const columns: Column<Item>[] = [
    { key: "sku", header: "SKU", render: (i) => <span className="id">{i.sku}</span> },
    { key: "name", header: "Name", render: (i) => i.name },
    { key: "owner", header: "Owning connection", render: (i) => i.owningConnectionId },
    { key: "kind", header: "Kind", render: (i) => (i.kind === "LICENSE" ? "License" : "Box") },
  ];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await syncItem.mutateAsync({
      sku: form.sku,
      name: form.name,
      owningConnectionId: form.owningConnectionId,
      kind: form.kind,
    });
    setForm(EMPTY_FORM);
    setShowForm(false);
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Item ownership</h1>
          <p>
            Every item is owned by exactly one ERP connection and says only what the product is. Price lives on the quote, not here.
          </p>
        </div>
        <div className="actions">
          <button className="erp-btn erp-btn--primary" type="button" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "Add item"}
          </button>
        </div>
      </div>
      {showForm && (
        <form className="panel stack" onSubmit={handleSubmit}>
          <div className="grid2">
            <div className="field">
              <label htmlFor="sku">SKU</label>
              <input className="input" id="sku" value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} required />
            </div>
            <div className="field">
              <label htmlFor="name">Name</label>
              <input className="input" id="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="field">
              <label htmlFor="owningConnectionId">
                Owning connection <InfoTag text="Submitting an existing SKU with a different connection re-assigns ownership — orders already placed keep the connection they were routed to." />
              </label>
              <select
                className="input"
                id="owningConnectionId"
                value={form.owningConnectionId}
                onChange={(e) => setForm({ ...form, owningConnectionId: e.target.value })}
                required
              >
                <option value="">Select a connection</option>
                {(connections ?? []).map((c) => (
                  <option key={c.connectionId} value={c.connectionId}>
                    {c.instanceLabel} ({c.connectionId})
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="kind">
                Kind <InfoTag text="A box needs a carrier or proof-of-delivery before it counts as delivered; a license is delivered the moment it ships." />
              </label>
              <select className="input" id="kind" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })} required>
                <option value="PHYSICAL">Box (physical good)</option>
                <option value="LICENSE">License</option>
              </select>
            </div>
          </div>
          {syncItem.error && <div className="callout callout--danger">{(syncItem.error as Error).message}</div>}
          <div className="actions">
            <button className="erp-btn erp-btn--primary" type="submit" disabled={syncItem.isPending}>
              {syncItem.isPending ? "Saving…" : "Save item"}
            </button>
          </div>
        </form>
      )}
      {error && <div className="callout callout--danger">Could not load items: {error.message}</div>}
      <DataTable columns={columns} rows={items ?? []} rowKey={(i) => i.itemId} emptyMessage={isLoading ? "Loading…" : "No items yet"} />
    </>
  );
}
