# Presentation Director Quality Gates

Every deck produced by the `deck-builder` pipeline must pass all four gates before being declared done. These gates apply regardless of output format (PPTX or HTML) and regardless of generation engine (Codex Presentations, pptxgenjs, guizang-ppt-skill, html-ppt-skill).

---

## Gate 1 — Content Gate

**Purpose:** Ensure the deck argues a thesis, not dumps information.

Checked after `deck.md` is written and before generation begins.

| Check | Pass Condition | Failure Action |
|-------|---------------|----------------|
| Thesis present | One-sentence thesis exists in `deck.md` | Write thesis before proceeding |
| Every slide has a claim | Slide title is a conclusion sentence, not a topic label | Rewrite title as a claim |
| Every slide has one proof object | Chart, diagram, table, big number, case, or quote — not multiple | Remove secondary proof objects to speaker notes |
| Every metric has a source | Source is cited or marked "missing" — not inferred | Mark as "missing" or add attribution |
| No fabricated data | No metric, company name, or logo that cannot be verified | Replace with "pending measurement" or omit |
| Missing info is explicit | Anything unavailable is listed in `deck.md` `## Omissions` | Add to Omissions section |
| Appendix material is separated | Background context the audience already knows is in appendix, not main deck | Move to appendix or speaker notes |

**Minimum evidence:** Reviewer (human or agent) can point to the thesis and the per-slide claim for every slide.

---

## Gate 2 — Design Gate

**Purpose:** Ensure the visual contract is respected throughout the deck.

Checked after generation, before render QA.

| Check | Pass Condition | Failure Action |
|-------|---------------|----------------|
| Design lock selected | One lock from `design-locks/` is declared in `## Design Contract` | Select lock and append Design Contract block |
| Hex values respected | No color outside the lock's palette is introduced | Return to lock-defined palette |
| Typography respected | Font families and weight hierarchy match the lock | Correct to lock fonts |
| No gradients or shadows not in lock | Flat color system maintained unless lock explicitly allows depth | Remove unapproved effects |
| Layout variety maintained | No same major layout on 3+ consecutive slides | Break pattern with different layout family |
| No generic 3-up card grid | Each slide has a layout that matches its proof object type | Replace with claim-focused layout from `layout-vocabulary.md` |
| Chart annotation style | Direct annotation used; legend minimized or removed | Add direct labels, remove or reduce legend |
| Architecture diagrams use editable shapes | No screenshot used where editable shapes are required | Rebuild as native shapes + connectors |

**Minimum evidence:** `## Design Contract` block is present in `deck.md` with lock, must-keep, and must-avoid fields.

---

## Gate 3 — Render Gate

**Purpose:** Confirm the generated output actually looks correct and is editable.

Checked after generation — mandatory before declaring done.

### PPTX Render Gate

| Check | Pass Condition | Failure Action |
|-------|---------------|----------------|
| Per-slide preview images exist | At least one render pass completed | Re-render before declaring done |
| Contact sheet generated | Thumbnail grid of all slides exists | Generate contact sheet |
| Safe area respected | Essential content is inside the declared safe area; only backgrounds and slide chrome use bleed/chrome bands | Move, resize, simplify, or split the slide; run `scripts/check_presentation_safe_area.py` when layout JSON exists |
| No text overlaps | Titles, subtitles, body text, labels, footers, page numbers, and connector lines do not collide | Move elements, widen text boxes, reduce font size, or reduce copy, then re-render |
| Long-title safe zone respected | Wrapped titles still leave visible clearance before subtitles or body content | Reserve a taller title band or move the subtitle/content down |
| Text overflow absent | No title wraps to a third line; no body text clips container | Fix text box size or reduce copy |
| Footer / page number clear | Footer does not collide with content area | Adjust layout margins |
| All text is editable | No text is rasterized or embedded as image | Rebuild as native text boxes |
| All shapes are native objects | No shape is an embedded screenshot where editability is expected | Rebuild as native shapes |
| At least one fix cycle completed | At minimum one issue was identified and fixed after first render | Do not skip the fix cycle |

### HTML Render Gate

| Check | Pass Condition | Failure Action |
|-------|---------------|----------------|
| Browser test completed | HTML opened in browser and verified | Open and inspect before declaring done |
| 16:9 aspect ratio correct | Slides render at correct ratio in full-screen mode | Fix CSS or slide dimensions |
| Safe area respected | All normal content sits inside `.slide-safe`; `.bleed` is used only for backgrounds or intentional full-bleed media | Move content into `.slide-safe`, constrain media/code blocks, or split the slide |
| Text overflow absent | No text clips or wraps unexpectedly | Fix font size or container width |
| Visual rhythm consistent | No abrupt style break between slides | Check section openers and content slides |
| Speaker notes hidden | `.notes` elements are not visible on slides; `display: none` is set in inline or linked local CSS | Add `.notes { display: none; }` to the HTML deck CSS |
| Slide count matches `data-total` | Count of `<section>` elements whose class list contains `slide` equals the `data-total` value on every footer | Fix `data-total` or add missing slides before delivery |
| `data-current` sequential | Slides are numbered 1 through N with no gaps or duplicates | Grep for `data-current` and compare against expected sequence |
| Preview form declared | HTML deck declares `data-preview-as="mobile"`, `"desktop"`, or `"both"` | Add the marker to `<html>` and `<body>` so Director preview matches delivery form |
| Footer language consistent | Footer text language matches the deck's declared `content_language` | Rewrite mixed-language footers to match deck language |
| Final HTML at correct path | `Decks/<task-slug>/vN/.draft/final.html` is promoted by `finalize --version vN` to `Decks/<task-slug>/vN/final.html`; final delivery lives under `Decks/<task-slug>/final/` | Run finalize; do not copy draft HTML by hand |

**Mandatory validator — run before declaring any HTML deck done:**

```bash
python3 skills/deck-builder/scripts/validate_html_deck.py <path-to-html>
```

This script catches failures that grep and visual inspection miss (smart/curly quotes in attributes, slide count mismatch, sequence gaps, visible notes). Exit code must be 0. Do not report complete if it fails.

**Minimum evidence:** Validator PASS output + browser screenshot included in completion report.

### Default Safe Area

For 16:9 decks authored on a `1280x720` canvas, use this default unless the template or design lock defines a stricter one:

```text
content safe area: x=54, y=70, width=1172, height=590
slide frame:       x=0,  y=0,  width=1280, height=720
```

Essential content means titles, subtitles, body text, screenshots, diagrams, charts, tables, icons that carry meaning, callouts, controls, and code blocks. Decorative backgrounds may bleed to the slide frame, but essential content may not rely on clipping or overflow hiding.

---

## Gate 4 — Output Gate

**Purpose:** Confirm final files are correctly located and deliverable.

Checked last, after render gate passes.

| Check | Pass Condition | Failure Action |
|-------|---------------|----------------|
| Final PPTX at correct path | `Decks/<task-slug>/v1/<task-slug>.pptx` exists for PPTX output | Move or rename file |
| Final HTML companion at correct path | `Decks/<task-slug>/v1/<task-slug>-companion.html` exists for PPTX-only output | Generate from selected version's per-slide preview images |
| Final HTML deck at correct path | Selected `Decks/<task-slug>/vN/final.html` exists after `finalize`, and `Decks/<task-slug>/final/<task-slug>.html` exists for delivery | Run finalize and final selection before handoff |
| Deck workspace matches project structure | For standalone delivery decks, path is `项目演示文稿/<project-name>/`; for task-bound decks, path is `Decks/<task-slug>/` | Confirm correct workspace before copying |
| `brief-confirmed.json` saved | Source execution contract is committed or saved | Save before closing |
| Sidecar artifacts saved | Lock files, contact sheet, QA notes retained for traceability | Save or copy into `Decks/<task-slug>/` |
| Remaining risks documented | Any known open issues stated in completion report | Write risk list before handing off |

**Minimum evidence:** Final completion report includes: PPTX absolute path when applicable, HTML path, render evidence, remaining risks for human review.

---

## Unacceptable Outputs — Examples

These patterns are automatic gate failures. Do not declare done if any are present.

| Pattern | Gate | Why It Fails |
|---------|------|-------------|
| Slide title is "Market Analysis" | Content Gate | Topic label, not a conclusion claim |
| Metric "grew 40% YoY" with no source | Content Gate | Unverified — must cite or mark missing |
| 4 consecutive slides with three-panel layout | Design Gate | Layout variety rule violated |
| New gradient introduced mid-deck | Design Gate | Design lock violation |
| Text box rasterized as image | Render Gate | Not editable in PowerPoint |
| Architecture diagram is a screenshot | Render Gate | Cannot be edited by user |
| `PPTX/<task-slug>/final/deck.html` is a temporary draft or preview artifact | Output Gate | Non-final artifact confused with final output |
| No contact sheet or browser screenshot | Render Gate | No render evidence |
| `.notes` content is visible on slides | Render Gate | Speaker notes must never render in main slide view; add `display: none` |
| `data-total` does not match actual slide count | Render Gate | Navigator and footer show wrong count; grep to verify before delivery |
| Footer text is in a different language from the deck | Render Gate | Language inconsistency destroys audience trust; fix before delivery |
| Slides described as added but not present in file | Render Gate | Declared work that was not done; count `data-current` attributes before reporting complete |

---

## Applying Gates Across Output Types

| Gate | PPTX Required | HTML Required | Notes |
|------|--------------|---------------|-------|
| Content Gate | Yes | Yes | Same `deck.md` is source for both |
| Design Gate | Yes | Yes | Design lock applies to both; CSS variables for HTML |
| Render Gate | Yes — contact sheet | Yes — browser screenshot | Evidence format differs |
| Output Gate | Yes | Yes | Output paths differ; same completion report |

---

## Source References

These gates consolidate checks previously scattered across:

- `skills/deck-builder/SKILL.md` — Step 7 Render QA checklist
- `skills/deck-builder/references/prompt-templates.md` — Render QA Checklist section
- `skills/deck-builder/references/slide-planner.md` — Common Planning Mistakes
- `skills/deck-builder/references/source-to-deck.md` — Quality Gates Before Handing to Generation
- `skills/deck-builder/references/engineering-project-deck.md` — Quality Gates Before Handing to Generation
- `skills/deck-builder/references/design-workflow.md` — Anti-Patterns to Enforce
