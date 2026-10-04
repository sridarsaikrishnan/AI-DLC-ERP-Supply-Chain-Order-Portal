import type { Money } from "../api/queries/orders";

export function formatMoney(money: Money | null | undefined): string {
  if (money == null) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: money.currency }).format(
    Number(money.amount),
  );
}
