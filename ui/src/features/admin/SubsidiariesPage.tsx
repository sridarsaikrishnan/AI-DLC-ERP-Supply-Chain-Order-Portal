import { useState, type FormEvent } from "react";

import { DataTable, type Column } from "../../components/DataTable";
import { InfoTag } from "../../components/InfoTag";
import {
  useConnections,
  useCreateSubsidiary,
  useErpRoute,
  useSubsidiaries,
  useSetErpRoute,
} from "../../hooks/useAdmin";
import type { Connection, Subsidiary } from "../../api/queries/admin";

/** One subsidiary's current route — its own query/mutation, so switching one
 * subsidiary's route doesn't refetch every row (Increment 7: routing is decided here,
 * at quote-issue time, not re-derived from order line items). */
function RouteCell({ subsidiary, connections }: { subsidiary: Subsidiary; connections: Connection[] }) {
  const { data: connectionId, isLoading } = useErpRoute(subsidiary.subsidiaryId);
  const setRoute = useSetErpRoute();
  const [value, setValue] = useState("");

  if (isLoading) return <span className="muted">Loading…</span>;

  async function handleChange(next: string) {
    setValue(next);
    if (!next) return;
    await setRoute.mutateAsync({ subsidiaryId: subsidiary.subsidiaryId, connectionId: next });
  }

  return (
    <select
      className="input"
      value={value || connectionId || ""}
      onChange={(e) => handleChange(e.target.value)}
      disabled={setRoute.isPending}
    >
      <option value="">{connectionId ? connectionId : "Not routed yet"}</option>
      {connections.map((c) => (
        <option key={c.connectionId} value={c.connectionId}>
          {c.instanceLabel} ({c.connectionId})
        </option>
      ))}
    </select>
  );
}

export function SubsidiariesPage() {
  const { data: subsidiaries, isLoading, error } = useSubsidiaries();
  const { data: connections } = useConnections();
  const createSubsidiary = useCreateSubsidiary();
  const EMPTY = { name: "", country: "", language: "" };
  const [form, setForm] = useState(EMPTY);
  const [showForm, setShowForm] = useState(false);

  const columns: Column<Subsidiary>[] = [
    { key: "id", header: "ID", render: (c) => <span className="id">{c.subsidiaryId}</span> },
    { key: "name", header: "Name", render: (c) => c.name },
    { key: "country", header: "Country", render: (c) => c.country },
    { key: "language", header: "Language", render: (c) => c.language },
    {
      key: "route",
      header: "Routes to",
      render: (c) => <RouteCell subsidiary={c} connections={connections ?? []} />,
    },
  ];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await createSubsidiary.mutateAsync(form);
    setForm(EMPTY);
    setShowForm(false);
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Subsidiaries</h1>
          <p>
            The company you are. Country and language live here <InfoTag text="So document numbers and emails have a home — the subsidiary record." />.
          </p>
        </div>
        <div className="actions">
          <button className="erp-btn erp-btn--primary" type="button" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "Add subsidiary"}
          </button>
        </div>
      </div>
      {showForm && (
        <form className="panel stack" onSubmit={handleSubmit}>
          <div className="grid2">
            <div className="field">
              <label htmlFor="sub-name">Name</label>
              <input className="input" id="sub-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="field">
              <label htmlFor="sub-country">Country</label>
              <input className="input" id="sub-country" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value.toUpperCase() })} maxLength={2} placeholder="e.g. DE" required />
            </div>
            <div className="field">
              <label htmlFor="sub-language">Language</label>
              <input className="input" id="sub-language" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })} maxLength={5} placeholder="e.g. de" required />
            </div>
          </div>
          {createSubsidiary.error && <div className="callout callout--danger">{(createSubsidiary.error as Error).message}</div>}
          <div className="actions">
            <button className="erp-btn erp-btn--primary" type="submit" disabled={createSubsidiary.isPending}>
              {createSubsidiary.isPending ? "Saving…" : "Save subsidiary"}
            </button>
          </div>
        </form>
      )}
      {error && <div className="callout callout--danger">Could not load subsidiaries: {error.message}</div>}
      <p className="hint">
        Sales orders are followed from the reseller's customer on an ERP connection, not from this page.
      </p>
      <DataTable columns={columns} rows={subsidiaries ?? []} rowKey={(c) => c.subsidiaryId} emptyMessage={isLoading ? "Loading…" : "No subsidiaries yet"} />
    </>
  );
}
