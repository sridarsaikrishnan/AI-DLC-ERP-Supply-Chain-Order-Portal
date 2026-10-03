import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { usePlaceOrder } from "../../hooks/useOrders";
import type { OrderLineInput } from "../../api/queries/orders";

const EMPTY_LINE: OrderLineInput = { productKey: "", quantity: 1, unitOfMeasure: "EA" };

export function NewOrderPage() {
  const navigate = useNavigate();
  const placeOrder = usePlaceOrder();
  const [ref, setRef] = useState("");
  const [lines, setLines] = useState<OrderLineInput[]>([{ ...EMPTY_LINE }]);

  function updateLine(index: number, patch: Partial<OrderLineInput>) {
    setLines((prev) => prev.map((l, i) => (i === index ? { ...l, ...patch } : l)));
  }

  function addLine() {
    setLines((prev) => [...prev, { ...EMPTY_LINE }]);
  }

  function removeLine(index: number) {
    setLines((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const result = await placeOrder.mutateAsync({ ref, lines });
    const orderId = (result as { placeOrder: string }).placeOrder;
    navigate(`/orders/${orderId}`);
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>New order</h1>
          <p>Submit a new order. It will be validated and sent to the ERP that owns each item.</p>
        </div>
      </div>
      <form className="stack" onSubmit={handleSubmit}>
        <section className="panel">
          <h2>Details</h2>
          <div className="field">
            <label htmlFor="ref">Your reference</label>
            <input className="input" id="ref" value={ref} onChange={(e) => setRef(e.target.value)} required />
          </div>
        </section>
        <section className="panel">
          <div className="panel-head">
            <h2>Lines</h2>
            <button className="erp-btn erp-btn--secondary erp-btn--sm" type="button" onClick={addLine}>
              Add line
            </button>
          </div>
          <div className="erp-table-wrap">
            <table className="erp-table">
              <thead>
                <tr>
                  <th>Item (SKU)</th>
                  <th className="num">Qty</th>
                  <th>Unit</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line, i) => (
                  <tr key={i}>
                    <td>
                      <input
                        className="input"
                        value={line.productKey}
                        onChange={(e) => updateLine(i, { productKey: e.target.value })}
                        required
                      />
                    </td>
                    <td className="num">
                      <input
                        className="input"
                        type="number"
                        min={1}
                        style={{ width: 80 }}
                        value={line.quantity}
                        onChange={(e) => updateLine(i, { quantity: Number(e.target.value) })}
                        required
                      />
                    </td>
                    <td>
                      <input
                        className="input"
                        style={{ width: 100 }}
                        value={line.unitOfMeasure}
                        onChange={(e) => updateLine(i, { unitOfMeasure: e.target.value })}
                        required
                      />
                    </td>
                    <td>
                      <button className="erp-btn erp-btn--ghost erp-btn--sm" type="button" disabled={lines.length === 1} onClick={() => removeLine(i)}>
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        {placeOrder.error && <div className="callout callout--danger">{(placeOrder.error as Error).message}</div>}
        <div className="actions">
          <button className="erp-btn erp-btn--primary" type="submit" disabled={placeOrder.isPending}>
            {placeOrder.isPending ? "Submitting…" : "Submit order"}
          </button>
        </div>
      </form>
    </>
  );
}
