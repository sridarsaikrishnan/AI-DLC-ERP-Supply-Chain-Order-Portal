import { useState, type FormEvent } from "react";

import { DataTable, type Column } from "../../components/DataTable";
import { InfoTag } from "../../components/InfoTag";
import { useCreateOperatingCompany, useOperatingCompanies } from "../../hooks/useAdmin";
import type { OperatingCompany } from "../../api/queries/admin";

export function OperatingCompaniesPage() {
  const { data: companies, isLoading, error } = useOperatingCompanies();
  const createCompany = useCreateOperatingCompany();
  const EMPTY = { name: "", country: "", language: "" };
  const [form, setForm] = useState(EMPTY);
  const [showForm, setShowForm] = useState(false);

  const columns: Column<OperatingCompany>[] = [
    { key: "id", header: "ID", render: (c) => <span className="id">{c.operatingCompanyId}</span> },
    { key: "name", header: "Name", render: (c) => c.name },
    { key: "country", header: "Country", render: (c) => c.country },
    { key: "language", header: "Language", render: (c) => c.language },
  ];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await createCompany.mutateAsync(form);
    setForm(EMPTY);
    setShowForm(false);
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Operating companies</h1>
          <p>
            The company you are. Country and language live here <InfoTag text="So document numbers and emails have a home — the office card." />, and quotes are issued under one of these.
          </p>
        </div>
        <div className="actions">
          <button className="erp-btn erp-btn--primary" type="button" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "Add company"}
          </button>
        </div>
      </div>
      {showForm && (
        <form className="panel stack" onSubmit={handleSubmit}>
          <div className="grid2">
            <div className="field">
              <label htmlFor="oc-name">Name</label>
              <input className="input" id="oc-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="field">
              <label htmlFor="oc-country">Country</label>
              <input className="input" id="oc-country" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value.toUpperCase() })} maxLength={2} placeholder="e.g. DE" required />
            </div>
            <div className="field">
              <label htmlFor="oc-language">Language</label>
              <input className="input" id="oc-language" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })} maxLength={5} placeholder="e.g. de" required />
            </div>
          </div>
          {createCompany.error && <div className="callout callout--danger">{(createCompany.error as Error).message}</div>}
          <div className="actions">
            <button className="erp-btn erp-btn--primary" type="submit" disabled={createCompany.isPending}>
              {createCompany.isPending ? "Saving…" : "Save company"}
            </button>
          </div>
        </form>
      )}
      {error && <div className="callout callout--danger">Could not load companies: {error.message}</div>}
      <DataTable columns={columns} rows={companies ?? []} rowKey={(c) => c.operatingCompanyId} emptyMessage={isLoading ? "Loading…" : "No operating companies yet"} />
    </>
  );
}
