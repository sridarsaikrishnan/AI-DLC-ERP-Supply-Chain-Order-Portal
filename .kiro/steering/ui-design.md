---
inclusion: always
---

# UI design source of truth

This project has proposed UI designs (not yet formally approved) and a design system in `design/`. Use them as the source of truth for every UI-related stage until the user changes them.

- Read `design/README.md` first. It lists the ten screens, their proposed routes, the requirements they cover, and the rules that must hold.
- Screens are in `design/screens/*.dc.html`. Styles and tokens are in `design/screens/ui.css` and `design/screens/ds/erpportal/`. Component usage rules are in `design/design-system/`.

## When to use it

- **Application Design and Functional Design** for any unit that has a UI (reseller portal, operator admin): map each screen to components, routes, data needs and API operations. Use the screen inventory in `design/README.md`.
- **NFR Requirements and NFR Design:** carry the accessibility, theming and self-hosted font rules into the UI requirements.
- **Code Generation:** implement screens by translating the markup in `design/screens/` and taking every color, spacing and radius from the tokens. Do not add new hex values or fonts.

## Rules

- Reseller-facing UI must never show an ERP name, instance or ERP record ID. Only the operator UI may (FR-19, AC-02).
- Use the exact lifecycle and status wording and the badge roles listed in `design/README.md`.
- If a needed screen or component is not designed (sign in, new-order form, item catalog, mapping editor, empty and error states), design it in the same style and ask the user before changing any existing screen.
- Behavior the design marks as proposed is not a requirement until the user confirms it. List it as an open item, do not silently implement it.
- Sample data in the screens is fictional. Do not copy it into code, fixtures or seed data as if it were real.
