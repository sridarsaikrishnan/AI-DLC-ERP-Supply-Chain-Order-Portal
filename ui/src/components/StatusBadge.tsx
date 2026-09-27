type Role = "neutral" | "progress" | "success" | "warning" | "danger";

// design/README.md "Status badge roles" — the exact, closed vocabulary this app uses.
// Order statuses come from the backend Title Case (read_models.STATUS_LABELS);
// connection/binding statuses come through as raw enum values (ConnectionStatus,
// BindingStatus) — both forms are mapped here.
const ROLE_BY_STATUS: Record<string, Role> = {
  Draft: "neutral",
  Closed: "neutral",
  Paused: "neutral",
  PAUSED: "neutral",
  Submitted: "progress",
  Validated: "progress",
  "Sent to ERP": "progress",
  Onboarding: "progress",
  Confirmed: "success",
  Fulfilled: "success",
  Delivered: "success",
  Active: "success",
  ACTIVE: "success",
  Verified: "success",
  VERIFIED: "success",
  Retrying: "warning",
  "To verify": "warning",
  TO_VERIFY: "warning",
  "Needs owner": "warning",
  Slow: "warning",
  Rejected: "danger",
  Failed: "danger",
  Unreachable: "danger",
  "Dead-lettered": "danger",
  Cancelled: "danger",
  CANCELLED: "danger",
  REMOVED: "danger",
};

function roleFor(status: string): Role {
  return ROLE_BY_STATUS[status] ?? "neutral";
}

/** design/design-system/components/StatusBadge.md — word + glyph, never color alone. */
export function StatusBadge({ status }: { status: string }) {
  return <span className={`erp-badge erp-badge--${roleFor(status)}`}>{status}</span>;
}
