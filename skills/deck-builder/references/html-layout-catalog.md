# HTML Layout Catalog

Reusable layout families for native Reveal.js decks. These are internal Presentation Director patterns, informed by public HTML deck libraries but implemented locally in generated HTML/CSS.

## Layout Families

| Key | Use When | Required Slots |
|-----|----------|----------------|
| `cover-hero` | opening with strong topic signal | title, subtitle, source/date, optional full-bleed abstract background |
| `toc-roadmap` | previewing sections | section labels, short descriptions, progress indicator |
| `section-divider` | act breaks | section title, one-line takeaway, optional abstract background |
| `claim-bullets` | simple explanatory slide | conclusion title, 3-5 bullets, source note |
| `two-column-proof` | compare claim and evidence | claim column, proof object column, note/footer |
| `three-column-compare` | options, personas, tradeoffs | three equal cards, direct labels, short evidence |
| `big-quote` | user/customer/research quote | quote, attribution, context, source |
| `stat-highlight` | one dominant metric | large number, label, denominator, interpretation |
| `kpi-grid` | operational snapshot | 4-8 KPI cells, trend markers, source line |
| `evidence-table` | dense but scan-friendly evidence | row labels, compact columns, highlights |
| `code-terminal` | command, log, or API example | short code block, annotations, outcome label |
| `diff-before-after` | changes, migration, refactor | before panel, after panel, delta labels |
| `flow-diagram` | process or data flow | nodes, semantic connectors, direction labels |
| `timeline` | chronology or phased rollout | dates/phases, milestones, risk markers |
| `roadmap` | future plan | now/next/later, dependencies, owner or confidence |
| `mindmap` | concept map | center node, grouped branches, limited depth |
| `pros-cons` | decision tradeoff | pros, cons, recommendation callout |
| `image-hero` | approved visual drives the point | image/background, title, short caption, overlay |
| `image-grid` | gallery or examples | 3-6 real/approved assets, captions, source labels |
| `chart-bar-line` | quantitative evidence | chart area, direct labels, takeaway subtitle |
| `architecture-map` | systems and platforms | components, boundaries, data/control flow |
| `process-steps` | how-it-works | numbered steps, input/output labels |
| `cta-close` | final ask or takeaway | final statement, next action, contact/source note |

## Rhythm Rules

- Do not repeat the same layout family three times in a row.
- Every slide needs one primary proof object: chart, diagram, table, quote, screenshot, or image.
- If no proof object exists, use `claim-bullets` only as a temporary fallback and mark the missing evidence in notes.
- Use `section-divider` to create pacing, not to hide weak content.
- `image-hero` and `image-grid` require real assets or approved generated images recorded in `image-assets.json`.

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
