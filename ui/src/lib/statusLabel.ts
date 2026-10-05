/** SCREAMING_SNAKE_CASE backend status/score value -> human words for display.
 * e.g. PARTIALLY_FULFILLED -> "Partially fulfilled", SENT_TO_ERP -> "Sent to ERP".
 * Presentation lives here, not on the backend — every status field (order lifecycle,
 * fulfillment/delivery/invoice score) uses this one function. */
export function statusLabel(value: string): string {
  const text = value
    .split("_")
    .map((w) => (w === "ERP" ? "ERP" : w.toLowerCase()))
    .join(" ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}
