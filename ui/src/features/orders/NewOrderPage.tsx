import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { useQuotes, usePlaceOrder } from "../../hooks/useOrders";
import { formatMoney } from "../../lib/money";

export function NewOrderPage() {
  const navigate = useNavigate();
  const { data: quotes, isLoading } = useQuotes();
  const placeOrder = usePlaceOrder();
  const [ref, setRef] = useState("");
  const [quoteId, setQuoteId] = useState("");
  const [qty, setQty] = useState<Record<string, number>>({});

  const quote = useMemo(() => (quotes ?? []).find((q) => q.quoteId === quoteId), [quotes, quoteId]);

  function selectQuote(id: string) {
    setQuoteId(id);
    const q = (quotes ?? []).find((x) => x.quoteId === id);
    setQty(Object.fromEntries((q?.lines ?? []).map((l) => [l.productKey, 1])));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!quote) return;
    const lines = quote.lines
      .map((l) => ({ productKey: l.productKey, quantity: qty[l.productKey] ?? 0 }))
      .filter((l) => l.quantity > 0);
    if (lines.length === 0) return;
    const result = await placeOrder.mutateAsync({ quoteId, ref, lines });
    const orderId = (result as { placeOrder: string }).placeOrder;
    navigate(`/orders/${orderId}`);
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>New order</h1>
          <p>Place an order against a quote. Prices and units come from the quote; the order is sent to the ERP that owns each item.</p>
        </div>
      </div>
      <form className="stack" onSubmit={handleSubmit}>
        <section className="panel">
          <h2>Details</h2>
          <div className="grid2">
            <div className="field">
              <label htmlFor="quote">Quote</label>
              <select className="input" id="quote" value={quoteId} onChange={(e) => selectQuote(e.target.value)} required>
                <option value="">{isLoading ? "Loading quotes…" : "Select a quote"}</option>
                {(quotes ?? [])
                  .filter((q) => q.status === "ISSUED")
                  .map((q) => (
                    <option key={q.quoteId} value={q.quoteId}>
                      {q.quoteId} — {q.endCustomerName} (valid to {q.validUntil})
                    </option>
                  ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="ref">Your reference</label>
              <input className="input" id="ref" value={ref} onChange={(e) => setRef(e.target.value)} required />
            </div>
          </div>
          {quote && (
            <p className="hint">
              Ship to {quote.endCustomerName}, {quote.shipTo}. Prices hold {quote.validFrom} to {quote.validUntil}.
            </p>
          )}
        </section>
        {quote && (
          <section className="panel">
            <h2>Lines</h2>
            <div className="erp-table-wrap">
              <table className="erp-table">
                <thead>
                  <tr>
                    <th>Item (SKU)</th>
                    <th>Unit</th>
                    <th className="num">Unit price</th>
                    <th className="num">Qty</th>
                  </tr>
                </thead>
                <tbody>
                  {quote.lines.map((line) => (
                    <tr key={line.productKey}>
                      <td className="id">{line.productKey}</td>
                      <td>{line.unitOfMeasure}</td>
                      <td className="num">{formatMoney(line.unitPrice)}</td>
                      <td className="num">
                        <input
                          className="input"
                          type="number"
                          min={0}
                          style={{ width: 80 }}
                          value={qty[line.productKey] ?? 0}
                          onChange={(e) => setQty((prev) => ({ ...prev, [line.productKey]: Number(e.target.value) }))}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="hint">Set a quantity of 0 to leave a quoted line off this order.</p>
          </section>
        )}
        {placeOrder.error && <div className="callout callout--danger">{(placeOrder.error as Error).message}</div>}
        <div className="actions">
          <button className="erp-btn erp-btn--primary" type="submit" disabled={!quote || placeOrder.isPending}>
            {placeOrder.isPending ? "Submitting…" : "Submit order"}
          </button>
        </div>
      </form>
    </>
  );
}
