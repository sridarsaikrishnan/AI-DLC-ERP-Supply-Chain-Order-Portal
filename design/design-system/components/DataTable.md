The dense table for order, item and customer lists: an `erp-table` inside an `erp-table-wrap`.

**You provide:** a real `<table>` with `<thead>` and `<tbody>`, one row per record, and a fixed column order.

- Put the record's identifier first, with `class="id"` (mono): order number, item code.
- Right-align every numeric column with `class="num"` and put the currency or unit in the cell, not the header alone.
- Show status with StatusBadge in its own column; do not tint rows by status.
- Mark the sorted column with `aria-sort="ascending"` or `"descending"` on its `<th>`; the arrow is drawn for you.
- Mark the open record with `aria-selected="true"` on its `<tr>`; the row gets `brand-soft`.
- Rows are 32px. Do not wrap cell text; truncate long client names and put the full value in a title or the detail view.
- The wrapper scrolls horizontally on narrow screens; do not shrink the type to fit.
- Do not add zebra striping or per-cell borders; row dividers and hover are enough.
