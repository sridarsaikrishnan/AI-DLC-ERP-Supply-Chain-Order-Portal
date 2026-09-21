A dense, data-first interface for an order portal that routes client orders to ERPs. Neutral green-grey surfaces, one teal accent, and color spent almost only on order status.

## Content fundamentals

- Write plain, active, sentence-case copy: "Retry now", "Order sent to ERP", never "Click here to retry".
- Name things the way a client's buyer does: order, customer, item, status. Not "payload", "adapter" or "webhook".
- Use the lifecycle words exactly: Draft, Submitted, Validated, Sent to ERP, Confirmed, Fulfilled, Closed. Two more exist for exceptions: Retrying (the order is queued and will be sent again) and Rejected (the order was refused and the reason is shown).
- An error says what happened and what to do: "Line 3 was rejected: item ITM-2210 is no longer available. Replace the item and resubmit."
- Reseller-facing screens, errors, webhooks and logs never name an ERP, an ERP instance or an ERP record ID. Say what happened in the reseller's terms. Only operator-only screens may show them. Everything else is `body`.
- No emoji, no exclamation marks, no marketing tone.

## Visual foundations

- Ground is `surface`; panels are `surface-raised` with a 1px `line` edge and `radius-lg`. Separate with borders, not shadows. `shadow-overlay` is for menus and dialogs only.
- Text is `ink`; secondary text is `ink-muted`. Both hold at least 4.5:1 on `surface`, `surface-raised` and `surface-sunken` in light and dark.
- `brand` is the only accent: primary button fill (text `on-brand`), links, the focus ring and completed timeline steps. Do not use it to decorate.
- Color carries meaning only through the five status pairs (`status-neutral`, `status-progress`, `status-success`, `status-warning`, `status-danger`). Every status also carries a word and a glyph, so it never depends on hue alone.
- Controls are bordered with `line-strong` (3:1 or better). Hairlines that only divide content use `line`.
- Focus is a solid 2px `brand` outline with a 2px offset, on every interactive element. It reaches 3:1 on `surface`, `surface-raised`, `surface-sunken` and `brand-soft` in both themes.
- Density: table rows are 32px, buttons 32px (24px small). Cell padding is `space-3`, panel padding `space-4`, gap between panels `space-6`.
- Radii: `radius-sm` badges, `radius-md` buttons, inputs and tables, `radius-lg` panels.
- Type is IBM Plex Sans with IBM Plex Mono for data. Headings step `page-title`, `title`, `heading`. Column headers use `label` in uppercase. Use tabular numerals for every number column.
- Motion: none by default. State changes are instant; add a 120ms fade only for menus and dialogs.

## Iconography

No icon library is bundled. The five status glyphs (ring, half-disc, check, triangle, cross) ship inside `bundle.css` and belong to StatusBadge and OrderTimeline. When an action needs an icon, use one line-icon set at 16px with a 1.5px stroke and `currentColor`, and keep the text label next to it.

## Components

Components are plain CSS classes from `bundle.css` (no framework, no script). Read a component's guideline before using it: Button, StatusBadge, DataTable, OrderTimeline. Preview data in each card is illustrative.
