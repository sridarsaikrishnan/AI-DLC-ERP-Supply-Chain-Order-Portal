import { Link } from "react-router-dom";

import { DataTable, type Column } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { useQuotes } from "../../hooks/useOrders";
import type { Quote } from "../../api/queries/orders";
import { formatMoney } from "../../lib/money";

export function QuotesPage() {
  const { data: quotes, isLoading, error } = useQuotes();

  const columns: Column<Quote>[] = [
    { key: "quoteId", header: "Quote", render: (q) => <span className="id">{q.quoteId}</span> },
    { key: "customer", header: "End customer", render: (q) => q.endCustomerName },
    { key: "shipTo", header: "Ship to", render: (q) => q.shipTo },
    { key: "items", header: "Items", render: (q) => q.lines.map((l) => `${l.productKey} ${formatMoney(l.unitPrice)}`).join(", ") },
    { key: "valid", header: "Prices hold", render: (q) => <span className="mono">{q.validFrom} → {q.validUntil}</span> },
    { key: "status", header: "Status", render: (q) => <StatusBadge status={q.status === "ISSUED" ? "Active" : q.status} /> },
  ];

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Quotes</h1>
          <p>Quotes issued to you. Place an order against an active quote — its prices and units are what the order uses.</p>
        </div>
        <div className="actions">
          <Link className="erp-btn erp-btn--primary" to="/orders/new">
            New order from a quote
          </Link>
        </div>
      </div>
      {error && <div className="callout callout--danger">Could not load quotes: {error.message}</div>}
      <DataTable columns={columns} rows={quotes ?? []} rowKey={(q) => q.quoteId} emptyMessage={isLoading ? "Loading…" : "No quotes yet"} />
    </>
  );
}
