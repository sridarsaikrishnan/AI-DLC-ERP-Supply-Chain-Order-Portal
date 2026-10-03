import { useState, type FormEvent } from "react";

import { DataTable, type Column } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { useIssueQuote, useOperatingCompanies, useOperatorQuotes } from "../../hooks/useAdmin";
import type { OperatorQuote } from "../../api/queries/admin";

interface LineForm {
  productKey: string;
  unitPrice: string;
  unitOfMeasure: string;
}

const EMPTY_LINE: LineForm = { productKey: "", unitPrice: "", unitOfMeasure: "EA" };

export function QuotesPage() {
  const { data: quotes, isLoading, error } = useOperatorQuotes();
  const { data: companies } = useOperatingCompanies();
  const issueQuote = useIssueQuote();

  const today = new Date().toISOString().slice(0, 10);
  const EMPTY = {
    tenantId: "",
    operatingCompanyId: "",
    endCustomerName: "",
    shipTo: "",
    currency: "USD",
    validFrom: today,
    validUntil: today,
  };
  const [form, setForm] = useState(EMPTY);
  const [lines, setLines] = useState<LineForm[]>([{ ...EMPTY_LINE }]);
  const [showForm, setShowForm] = useState(false);

  const columns: Column<OperatorQuote>[] = [
    { key: "quoteId", header: "Quote", render: (q) => <span className="id">{q.quoteId}</span> },
    { key: "tenant", header: "Reseller", render: (q) => <span className="mono">{q.tenantId}</span> },
    { key: "customer", header: "End customer", render: (q) => q.endCustomerName },
    { key: "lines", header: "Lines", render: (q) => q.lines.length },
    { key: "valid", header: "Prices hold", render: (q) => <span className="mono">{q.validFrom} → {q.validUntil}</span> },
    { key: "status", header: "Status", render: (q) => <StatusBadge status={q.status === "ISSUED" ? "Active" : q.status} /> },
  ];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await issueQuote.mutateAsync({
      ...form,
      lines: lines
        .filter((l) => l.productKey && l.unitPrice)
        .map((l) => ({ productKey: l.productKey, unitPrice: Number(l.unitPrice), unitOfMeasure: l.unitOfMeasure })),
    });
    setForm(EMPTY);
    setLines([{ ...EMPTY_LINE }]);
    setShowForm(false);
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Quotes</h1>
          <p>Issue a quote to a reseller — the items, prices, how long they hold, and where the goods go. Orders reply to a quote.</p>
        </div>
        <div className="actions">
          <button className="erp-btn erp-btn--primary" type="button" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "Issue quote"}
          </button>
        </div>
      </div>
      {showForm && (
        <form className="panel stack" onSubmit={handleSubmit}>
          <div className="grid2">
            <div className="field">
              <label htmlFor="q-tenant">Reseller (tenant id)</label>
              <input className="input" id="q-tenant" value={form.tenantId} onChange={(e) => setForm({ ...form, tenantId: e.target.value })} required />
            </div>
            <div className="field">
              <label htmlFor="q-company">Operating company</label>
              <select className="input" id="q-company" value={form.operatingCompanyId} onChange={(e) => setForm({ ...form, operatingCompanyId: e.target.value })} required>
                <option value="">Select a company</option>
                {(companies ?? []).map((c) => (
                  <option key={c.operatingCompanyId} value={c.operatingCompanyId}>
                    {c.name} ({c.country})
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="q-customer">End customer</label>
              <input className="input" id="q-customer" value={form.endCustomerName} onChange={(e) => setForm({ ...form, endCustomerName: e.target.value })} required />
            </div>
            <div className="field">
              <label htmlFor="q-shipto">Ship to</label>
              <input className="input" id="q-shipto" value={form.shipTo} onChange={(e) => setForm({ ...form, shipTo: e.target.value })} required />
            </div>
            <div className="field">
              <label htmlFor="q-currency">Currency</label>
              <input className="input" id="q-currency" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value.toUpperCase() })} maxLength={3} required />
            </div>
            <div className="field">
              <label htmlFor="q-from">Valid from</label>
              <input className="input" id="q-from" type="date" value={form.validFrom} onChange={(e) => setForm({ ...form, validFrom: e.target.value })} required />
            </div>
            <div className="field">
              <label htmlFor="q-until">Valid until</label>
              <input className="input" id="q-until" type="date" value={form.validUntil} onChange={(e) => setForm({ ...form, validUntil: e.target.value })} required />
            </div>
          </div>
          <div className="panel-head">
            <h2>Lines</h2>
            <button className="erp-btn erp-btn--secondary erp-btn--sm" type="button" onClick={() => setLines((p) => [...p, { ...EMPTY_LINE }])}>
              Add line
            </button>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Item (SKU)</th>
                  <th className="num">Unit price</th>
                  <th>Unit</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line, i) => (
                  <tr key={i}>
                    <td>
                      <input className="input" value={line.productKey} onChange={(e) => setLines((p) => p.map((l, j) => (j === i ? { ...l, productKey: e.target.value } : l)))} required />
                    </td>
                    <td className="num">
                      <input className="input" type="number" step="0.01" min="0" style={{ width: 110 }} value={line.unitPrice} onChange={(e) => setLines((p) => p.map((l, j) => (j === i ? { ...l, unitPrice: e.target.value } : l)))} required />
                    </td>
                    <td>
                      <input className="input" style={{ width: 90 }} value={line.unitOfMeasure} onChange={(e) => setLines((p) => p.map((l, j) => (j === i ? { ...l, unitOfMeasure: e.target.value } : l)))} required />
                    </td>
                    <td>
                      <button className="erp-btn erp-btn--ghost erp-btn--sm" type="button" disabled={lines.length === 1} onClick={() => setLines((p) => p.filter((_, j) => j !== i))}>
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {issueQuote.error && <div className="callout callout--danger">{(issueQuote.error as Error).message}</div>}
          <div className="actions">
            <button className="erp-btn erp-btn--primary" type="submit" disabled={issueQuote.isPending}>
              {issueQuote.isPending ? "Issuing…" : "Issue quote"}
            </button>
          </div>
        </form>
      )}
      {error && <div className="callout callout--danger">Could not load quotes: {error.message}</div>}
      <DataTable columns={columns} rows={quotes ?? []} rowKey={(q) => q.quoteId} emptyMessage={isLoading ? "Loading…" : "No quotes yet"} />
    </>
  );
}
