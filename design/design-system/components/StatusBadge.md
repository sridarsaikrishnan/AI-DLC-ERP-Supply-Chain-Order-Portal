The pill that shows an order's status: `<span class="erp-badge erp-badge--{role}">Label</span>`.

**You provide:** the status word as text. The glyph is drawn by the component, so never add your own icon.

Role by status:
- `neutral` (ring): Draft, Closed
- `progress` (half-disc): Submitted, Validated, Sent to ERP
- `success` (check): Confirmed, Fulfilled
- `warning` (triangle): Retrying
- `danger` (cross): Rejected

- Always show the word. The role, glyph and hue reinforce it but none stands in for it.
- One badge per row or header; do not stack badges to describe sub-states, put that in a note.
- Keep the label to the exact lifecycle word; no custom wording per client.
- Do not use these roles for anything that is not a status (tags, counts, categories).
