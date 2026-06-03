# HTML Layout Catalog

Reusable layout families for native Reveal.js decks. These keys are Presentation Director's own abstractions, implemented locally in generated HTML/CSS. Many map onto verified single-page layouts in `lewislulu/html-ppt-skill` (`templates/single-page/*.html`, 31 files). The `Source` column records that mapping: `repo:<file>` = a directly corresponding verified layout exists in the source; `general` = standard deck pattern with no direct source file. PD does not import these files; they are conceptual references only.

## Layout Families

| Key | Use When | Required Slots | Source |
|-----|----------|----------------|--------|
| `cover-hero` | opening with strong topic signal | title, subtitle, source/date, optional full-bleed abstract background | repo: `cover.html` (kicker + title + lede + pill row) |
| `toc-roadmap` | previewing sections | section labels, short descriptions, progress indicator | repo: `toc.html` (2×3 numbered cards) |
| `section-divider` | act breaks | section title, one-line takeaway, optional abstract background | repo: `section-divider.html` |
| `claim-bullets` | simple explanatory slide | conclusion title, 3-5 bullets, source note | repo: `bullets.html` (card-wrapped items) |
| `two-column-proof` | compare claim and evidence | claim column, proof object column, note/footer | repo: `two-column.html` |
| `three-column-compare` | options, personas, tradeoffs | three equal cards, direct labels, short evidence | repo: `three-column.html` |
| `big-quote` | user/customer/research quote | quote, attribution, context, source | repo: `big-quote.html` |
| `stat-highlight` | one dominant metric | large number, label, denominator, interpretation | repo: `stat-highlight.html` (uses counter) |
| `kpi-grid` | operational snapshot | 4-8 KPI cells, trend markers, source line | repo: `kpi-grid.html` (4-up with deltas) |
| `evidence-table` | dense but scan-friendly evidence | row labels, compact columns, highlights | repo: `table.html` (hover rows, right-aligned numerics) |
| `code-terminal` | command, log, or API example | short code block, annotations, outcome label | repo: `code.html` / `terminal.html` |
| `diff-before-after` | changes, migration, refactor | before panel, after panel, delta labels | repo: `diff.html` / `comparison.html` |
| `flow-diagram` | process or data flow | nodes, semantic connectors, direction labels | repo: `flow-diagram.html` (5-node pipeline) |
| `timeline` | chronology or phased rollout | dates/phases, milestones, risk markers | repo: `timeline.html` / `gantt.html` |
| `roadmap` | future plan | now/next/later, dependencies, owner or confidence | repo: `roadmap.html` (NOW/NEXT/LATER/VISION) |
| `mindmap` | concept map | center node, grouped branches, limited depth | repo: `mindmap.html` (radial, SVG path-draw) |
| `pros-cons` | decision tradeoff | pros, cons, recommendation callout | repo: `pros-cons.html` / `todo-checklist.html` |
| `image-hero` | approved visual drives the point | image/background, title, short caption, overlay | repo: `image-hero.html` (Ken Burns bg) |
| `image-grid` | gallery or examples | 3-6 real/approved assets, captions, source labels | repo: `image-grid.html` (bento grid) |
| `chart-bar-line` | quantitative evidence | chart area, direct labels, takeaway subtitle | repo: `chart-bar.html` / `chart-line.html` / `chart-pie.html` / `chart-radar.html` (Chart.js) |
| `architecture-map` | systems and platforms | components, boundaries, data/control flow | repo: `arch-diagram.html` (3-tier grid) |
| `process-steps` | how-it-works | numbered steps, input/output labels | repo: `process-steps.html` (4 numbered cards) |
| `cta-close` | final ask or takeaway | final statement, next action, contact/source note | repo: `cta.html` → `thanks.html` |

## Rhythm Rules

- Do not repeat the same layout family three times in a row.
- Every slide needs one primary proof object: chart, diagram, table, quote, screenshot, or image.
- If no proof object exists, use `claim-bullets` only as a temporary fallback and mark the missing evidence in notes.
- Use `section-divider` to create pacing, not to hide weak content.
- `image-hero` and `image-grid` require real assets or approved generated images recorded in `image-assets.json`.

## Source layout conventions (repo, reference only)

The source repo's single-page layouts follow a consistent markup convention worth mirroring conceptually in generated Reveal.js slides (Source: repo `references/layouts.md`):

- Each slide is a `<section class="slide" data-title="...">`.
- Header eyebrow/kicker: `.kicker` / `.eyebrow`; titles `.h1` / `.h2`; intro `.lede`.
- Cards: `.card` with variants `.card-soft`, `.card-outline`, `.card-accent`.
- Grids: `.grid.g2`, `.grid.g3`, `.grid.g4`.
- Per-slide speaker notes: `.notes`.

PD implements equivalent semantics with its own class names and the safe-area contract below; these are not imported.

## Safe Area Contract

All regular content sits in `.slide-safe`; full-bleed backgrounds and decorative image textures may sit in `.bleed`.

```css
.reveal .slides section {
  position: relative;
  width: 1280px;
  height: 720px;
  overflow: hidden;
}
.slide-safe {
  position: absolute;
  left: 54px;
  top: 70px;
  width: 1172px;
  height: 590px;
}
.bleed {
  position: absolute;
  inset: 0;
}
```

Do not rely on `overflow:hidden` to crop essential screenshots, code, charts, labels, or body text.
