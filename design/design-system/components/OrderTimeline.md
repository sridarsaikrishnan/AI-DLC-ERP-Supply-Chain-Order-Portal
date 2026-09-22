The vertical history of an order through its lifecycle: an `erp-timeline` list of `erp-step` items.

**You provide:** one `<li>` per lifecycle step in order (Draft, Submitted, Validated, Sent to ERP, Confirmed, Fulfilled, Closed), each with a `erp-step__mark`, a label, and a `<time>` in `erp-step__time` when it happened.

- Step state classes: `--done` (check mark on `brand`), `--current` (filled dot with ring), `--todo` (empty ring, muted label), `--failed` (cross on `status-danger-fg`).
- A done step carries the check svg from the preview; a failed step carries the cross. The current and todo marks stay empty.
- There is one current step at most. After a failure, end the list at the failed step; do not draw the steps that will never happen.
- Put the reason and next action in `erp-step__note` ("Line 3 was rejected: item ITM-2210 is no longer available. Replace the item and resubmit." Never name the ERP.). Keep it to one or two lines.
- Show times as the viewer's local time in `data` style; leave `erp-step__time` empty for future steps.
- Put the timeline in a `surface-raised` panel with a `line` border; do not add a shadow.
