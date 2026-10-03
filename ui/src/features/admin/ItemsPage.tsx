import { useState, type FormEvent } from "react";

import { DataTable, type Column } from "../../components/DataTable";
import { InfoTag } from "../../components/InfoTag";
import { useConnections, useItems, useSyncItem } from "../../hooks/useAdmin";
import type { Item } from "../../api/queries/admin";
import { formatMoney } from "../../lib/money";

export function ItemsPage() {
  const { data: items, isLoading, error } = useItems();
  const { data: connections } = useConnections();
  const syncItem = useSyncItem();
  const [form, setForm] = useState({ sku: "", name: "", owningConnectionId: "", unitPrice: "", currency: "USD" });
  const [showForm, setShowForm] = useState(false);

  const columns: Column<Item>[] = [
    { key: "sku", header: "SKU", render: (i) => <span className="id">{i.sku}</span> },
    { key: "name", header: "Name", render: (i) => i.name },
    { key: "owner", header: "Owning connection", render: (i) => i.owningConnectionId },
    { key: "price", header: "Unit price", render: (i) => formatMoney(i.unitPrice) },
  ];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await syncItem.mutateAsync({
      sku: form.sku,
      name: form.name,
      owningConnectionId: form.owningConnectionId,
      unitPrice: form.unitPrice === "" ? null : Number(form.unitPrice),
      currency: form.unitPrice === "" ? null : form.currency,
    });
    setForm({ sku: "", name: "", owningConnectionId: "", unitPrice: "", currency: "USD" });
    setShowForm(false);
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Item ownership</h1>
          <p>Every item is owned by exactly one ERP connection. Orders for an item are routed to its owner.</p>
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
              <label htmlFor="unitPrice">
                Unit price <InfoTag text="Resolved onto every order line for this SKU at submission time — a reseller's order never carries its own price." />
              </label>
              <input
                className="input"
                id="unitPrice"
                type="number"
                step="0.01"
                min="0"
                value={form.unitPrice}
                onChange={(e) => setForm({ ...form, unitPrice: e.target.value })}
                placeholder="Leave blank for no price yet"
              />
            </div>
            <div className="field">
              <label htmlFor="currency">Currency</label>
              <input
                className="input"
                id="currency"
                value={form.currency}
                onChange={(e) => setForm({ ...form, currency: e.target.value.toUpperCase() })}
                maxLength={3}
                disabled={form.unitPrice === ""}
              />
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
