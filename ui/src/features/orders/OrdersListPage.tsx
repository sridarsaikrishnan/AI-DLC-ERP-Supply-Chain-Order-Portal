import { useState } from "react";
import { Link } from "react-router-dom";

import { DataTable, type Column } from "../../components/DataTable";
import { StatusBadge } from "../../components/StatusBadge";
import { useOrders } from "../../hooks/useOrders";
import type { ResellerOrder } from "../../api/queries/orders";
import { statusLabel } from "../../lib/statusLabel";

export function OrdersListPage() {
  const { data: orders, isLoading, error } = useOrders();
  const [search, setSearch] = useState("");

  const filtered = (orders ?? []).filter(
    (o) => o.orderId.toLowerCase().includes(search.toLowerCase()) || o.clientReference.toLowerCase().includes(search.toLowerCase()),
  );

  const columns: Column<ResellerOrder>[] = [
    { key: "orderId", header: "Order", render: (o) => <Link to={`/orders/${o.orderId}`}>{o.orderId}</Link> },
    { key: "ref", header: "Your reference", render: (o) => <span className="id">{o.clientReference}</span> },
    { key: "lines", header: "Lines", align: "right", render: (o) => o.lines.length },
    { key: "status", header: "Status", render: (o) => <StatusBadge status={statusLabel(o.status)} /> },
  ];

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Orders</h1>
          <p>Sales and purchase orders you have placed. Status changes appear here as they happen.</p>
        </div>
        <div className="actions">
          <Link className="erp-btn erp-btn--primary" to="/orders/new">
            New order
          </Link>
        </div>
      </div>
      <div className="toolbar">
        <label className="sr" htmlFor="q">
          Search orders
        </label>
        <input
          className="input"
          id="q"
          type="search"
          placeholder="Search by order or reference"
          style={{ width: 300 }}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      {error && <div className="callout callout--danger">Could not load orders: {error.message}</div>}
      <DataTable columns={columns} rows={filtered} rowKey={(o) => o.orderId} emptyMessage={isLoading ? "Loading…" : "No orders yet"} />
    </>
  );
}
