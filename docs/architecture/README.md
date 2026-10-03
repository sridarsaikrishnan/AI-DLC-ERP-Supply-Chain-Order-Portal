# Architecture

- **High-Level Design (document):** [`hld.md`](hld.md) — C4 container-level write-up:
  system context, component responsibilities, key flows, data ownership, boundaries, and
  architecturally-significant NFRs (with `TBD`s called out).
- **HLD diagram (editable):** [`hld.drawio`](hld.drawio) — C4 container view, open in
  diagrams.net or the VS Code Draw.io extension. This is the canonical, maintainable HLD.
- **HLD diagram (quick view):** [`hld.svg`](hld.svg) — a layered overview that renders
  anywhere without a tool.

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
