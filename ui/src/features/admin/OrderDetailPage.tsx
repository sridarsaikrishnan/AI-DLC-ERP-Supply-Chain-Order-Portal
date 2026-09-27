import { Link, useNavigate, useParams } from "react-router-dom";

import { InfoTag } from "../../components/InfoTag";
import { OrderTimeline } from "../../components/OrderTimeline";
import { StatusBadge } from "../../components/StatusBadge";
import { useOperatorOrder } from "../../hooks/useAdmin";

/** Operator view of one order: everything the reseller sees, plus ERP identity (owning
 * connection, ERP order id) — never shown on the reseller-facing OrderDetailPage. */
export function OrderDetailPage() {
  const { orderId = "" } = useParams();
  const navigate = useNavigate();
  const { data: order, isLoading, error } = useOperatorOrder(orderId);

  if (isLoading) return <p className="muted">Loading…</p>;
  if (error) return <div className="callout callout--danger">Could not load order: {error.message}</div>;
  if (!order) return <p className="muted">Order not found.</p>;

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>
            Order {order.orderId} <StatusBadge status={order.status} />
          </h1>
          <p>
            Tenant {order.tenantId}, reference {order.clientReference}.
          </p>
        </div>
        <div className="actions">
          <button className="erp-btn erp-btn--secondary" type="button" onClick={() => navigate(`/orders/${order.orderId}/events`)}>
            Open event stream
          </button>
        </div>
      </div>
      <div className="split">
        <div className="stack">
          <section className="panel">
            <h2>Order lines</h2>
            <div className="erp-table-wrap">
              <table className="erp-table">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th className="num">Qty</th>
                    <th>Unit</th>
                  </tr>
                </thead>
                <tbody>
                  {order.lines.map((line) => (
                    <tr key={line.productKey}>
                      <td className="id">{line.productKey}</td>
                      <td className="num">{line.quantity}</td>
                      <td>{line.unitOfMeasure}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="panel">
            <h2>ERP identity</h2>
            <dl className="kv">
              <dt>
                Owning connection <InfoTag text="Which ERP connection owns the items on this order and receives it." />
              </dt>
              <dd>{order.owningConnectionId ?? "Not yet routed"}</dd>
              <dt>
                ERP order ID <InfoTag text="The order's identifier inside the ERP itself, once it has been sent." />
              </dt>
              <dd className="mono">{order.erpOrderId ?? "—"}</dd>
            </dl>
          </section>
        </div>
        <div className="stack">
          <section className="panel">
            <h2>Timeline</h2>
            <OrderTimeline timeline={order.timeline} currentStatus={order.status} />
          </section>
        </div>
      </div>
      <p>
        <Link to="/admin/orders">Back to orders</Link>
      </p>
    </>
  );
}
