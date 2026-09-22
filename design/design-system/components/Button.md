The action control: `<button class="erp-btn erp-btn--{variant}">` with an optional `erp-btn--sm`.

**You provide:** a `<button>` element and a text label that says what happens ("Submit order", "Retry now").

- `primary`: the one main action of a screen or panel. At most one per view.
- `secondary`: other actions that change data (Save draft, Edit).
- `ghost`: navigation-like actions that change nothing (View details, Download).
- `danger`: destructive actions only (Cancel order). Ask for confirmation before it runs.
- Use `erp-btn--sm` (24px) inside table rows and timeline steps; the default is 32px.
- Set `disabled` on the element and explain why nearby, never rely on the greyed look alone.
- Do not use color alone to mark the primary action's state; keep the label truthful ("Submitting").
