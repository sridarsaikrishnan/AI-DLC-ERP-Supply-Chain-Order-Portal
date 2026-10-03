# Architecture

- **High-Level Design:** [`hld.svg`](hld.svg) — the system at a glance (clients → API →
  domain modules → shared kernel → worker/messaging → data → external), with the two
  primary flows (place-order-to-ERP, and ERP-status-back-to-reseller).

## Why SVG, not Mermaid

Mermaid is great for small flows but gets cramped and hard to lay out for a wide,
multi-layer system diagram like this one. The HLD is authored as a hand-laid-out **SVG**:
it is text/diffable in git, scales without pixelation, renders in any browser/IDE/PR, and
gives full control over placement for a large diagram. Edit `hld.svg` directly.

Other good non-Mermaid options if you prefer a source-language with auto-layout:
- **Graphviz (DOT)** — terse text, solid auto-layout for big graphs; render with `dot -Tsvg`.
- **D2** — modern diagram language, excellent for large/layered diagrams (`d2 in.d2 out.svg`).
- **PlantUML / C4-PlantUML** — C4 model (context/container/component) suits HLD→LLD levels.
- **Structurizr** — define the C4 model once, render multiple views.
- **draw.io / Excalidraw** — GUI, but exports SVG that still diffs reasonably.
