# Prompt Templates

Ready-to-use generation prompts for the supported output paths. Fill in `<...>` placeholders before sending.

Before using any template, resolve file paths from the active project. Do not include a file in the prompt unless it exists. Outside MD2PPT, omit `docs/pptx-master-workflow.md` and rely on this skill's references instead.

All user-facing artifacts for a deck must be collected under `PPTX/<task-slug>/`: confirmed brief, review pages, versioned PPTX files, per-slide preview images, contact sheets, QA summaries, revision requests, comparison files, and final deliverables. Codex Presentations may keep its internal scratch workspace under `outputs/<thread-id>/presentations/...`, but copy user-facing outputs back into `PPTX/<task-slug>/`.

---

## Template A0 — Codex Presentation Director (Required Before Net-New PPTX)

Use this before Template A when working inside Codex and creating a new PPTX from source material.

Do not call Codex Presentations directly until the user has confirmed the brief.

```bash
# 1. Initialize director workspace
python3 scripts/presentation_director.py init \
  --task "<short task slug>" \
  --topic "<deck topic>" \
  --source "<resolved source path or URL>" \
  --conversation-text "<recent user prompt or conversation excerpt>"

# 2. Start click-based UI, open intake automatically, and wait for confirmation
python3 scripts/presentation_director.py serve-wait \
  --task "<short task slug>" \
  --for confirmed

# 3. Complete Image Style Gate when the confirmed brief lacks image_generation_mode
python3 scripts/presentation_director.py serve-wait \
  --task "<short task slug>" \
  --open-page image-style \
  --for images-style

# 4. Print the generation handoff prompt
python3 scripts/presentation_director.py prompt --task "<short task slug>" --kind initial
```

Keep `--ui-language auto` unless the user explicitly asks for a specific Director UI language. The confirmation HTML should communicate in the user's current conversation language; the separate `content_language` field controls the slide copy language.

Do not ask the user to copy/paste a local URL. If the page did not open, run:

```bash
python3 scripts/presentation_director.py open-page --task "<short task slug>" --page intake
```

For batch or background runs, add `--no-open` and log the printed URL.

For `post-v1-slot-review` or `hybrid`, after v1 preview artifacts exist, use the Image Placement Gate before style review:

```bash
python3 scripts/presentation_director.py serve-wait \
  --task "<short task slug>" \
  --open-page image-placement \
  --for images-placement
```

Pre-v1 and post-v1 generated images must be recorded through `image-asset`; `final_status: success` is valid only when the output file exists and is non-empty. Failed image generation uses retry-2-then-stop and must not silently become CSS gradients or SVG placeholders.

After the latest required version is generated, use the same director workspace for visual revision:

```bash
python3 scripts/presentation_director.py render --task "<short task slug>" --open-page style-review
python3 scripts/presentation_director.py wait --task "<short task slug>" --for revision
python3 scripts/presentation_director.py prompt --task "<short task slug>" --kind revision
```

After the final version is selected, use output-format-aware final paths:

```bash
PPTX/<task-slug>/final/<task-slug>.pptx
PPTX/<task-slug>/final/<task-slug>.html          # Reveal.js deck for html-revealjs or both
PPTX/<task-slug>/final/<task-slug>-companion.html # PPTX-only view-only companion
```

Skip Template A0 only when the user explicitly says to skip intake/director, when a valid user-confirmed `brief-confirmed.json` already exists, or when the task is a targeted edit / QA pass on an existing deck. In an interactive Codex session, do not create `brief-confirmed.json` or `confirmed.ready` on the user's behalf; open the confirmation page and wait for the user to click confirm.

---

## Template A — Codex Presentations (Primary PPTX Renderer)

Use this after Template A0 has produced a confirmed brief, or when the task is a targeted edit / already-confirmed brief.

```
I want to generate a high-quality, editable PowerPoint deck.

Use the Codex Presentations skill / plugin as the primary workflow. If the plugin is not visible in Codex UI, resolve the bundled runtime at `$HOME/.codex/plugins/cache/openai-primary-runtime/presentations/*/skills/presentations`.
Generation engine: artifact-tool presentation JSX. Before PPTX work, run `scripts/check_presentation_runtime.mjs`; for net-new PPTX export, call `scripts/build_artifact_deck.mjs`.
Do NOT use pptxgenjs, Marp, or Google Slides as the primary generation path.

[Input Files]
- Confirmed brief: <resolved path to brief-confirmed.json, or pasted summary from presentation_director.py prompt --kind initial>
- Content source: <resolved path to deck.md or source material if deck.md does not exist>
- Optional design lock: <resolved design-lock path only if the user explicitly selected one>
- Workflow reference: <optional resolved docs/pptx-master-workflow.md when working inside MD2PPT>

[Output Target]
- Final PPTX: `PPTX/<task-slug>/v1/final.pptx` for first draft, then `PPTX/<task-slug>/final/<task-slug>.pptx` after final selection
- Per-slide preview PNGs: copy to `PPTX/<task-slug>/v1/slides/` for the final share HTML companion
- Contact sheet and concise QA summary: copy to `PPTX/<task-slug>/v1/`
- Final PPTX-only share HTML companion: `PPTX/<task-slug>/final/<task-slug>-companion.html`, generated from the selected version's per-slide previews
- Scratch / preview / layout files required by the Presentations plugin/runtime may stay inside its internal workspace
- User-facing deliverables and review artifacts must be collected in `PPTX/<task-slug>/`

[Narrative Requirements]
- First, write a claim spine from the confirmed brief and source material: thesis, audience, one-line arc, per-slide claim, proof object, source
- Every slide title must be a conclusion sentence — not a topic label
- Do not fabricate numbers, clients, sources, logos, or brand assets
- Missing data must be noted in source notes or omission notes

[Design Requirements]
- If the user selected a design lock, apply it as a hard constraint. Otherwise, let Presentations own the design system.
- Audience, goal, source boundary, content language, logo policy, image policy, and output constraints are locked by the confirmed brief.
- Composition, layout rhythm, chart treatment, typography hierarchy, and visual expression are delegated to Presentations.
- Build a design system: background, fonts, palette, chart grammar, page numbers, footnotes, kicker, layout families
- Do not use the same major layout on 3 or more consecutive slides
- Avoid generic SaaS card grids; give each slide a distinct proof object

[Build Requirements]
- Use editable text, shapes, lines, tables, and charts throughout
- Charts must use direct annotation — minimize or eliminate legends
- Architecture and flow diagrams must use semantic connectors, not decorative arrows
- Every node and every labeled connector must be editable

[QA Requirements]
- Render per-slide preview images
- Copy final per-slide preview images into `PPTX/<task-slug>/<version>/slides/`
- Generate a contact sheet (thumbnail grid)
- Generate layout JSON; review for overflow, font issues, spacing
- Use the Presentations comeback rubric for self-assessment
- Complete at least one "find issue → fix → re-render" cycle
- Final reply must include: PPTX absolute path, QA evidence, remaining risks for human review
- Final reply must include: PPTX absolute path, HTML companion absolute path, QA evidence, remaining risks for human review
```

---

## Template B — Claude Code / pptxgenjs (Fallback Path)

Use this when Codex Presentations is not available — e.g., in Claude Code or offline.

```
Use this repository's skills/pptx/SKILL.md pptxgenjs workflow to generate an editable PPTX.

[Input Files]
- Content source: <resolved path to deck.md>
- Design lock: <resolved design lock path, or inline visual contract if no lock file exists>

[Output Target]
- Final PPTX: `PPTX/<task-slug>/final/<task-slug>.pptx`
- Final PPTX-only share HTML companion: `PPTX/<task-slug>/final/<task-slug>-companion.html`

[Narrative Requirements]
- Before writing any pptxgenjs code, produce a claim spine:
  thesis / audience / one-line arc / per-slide claim / proof object / source
- Every slide title must be a conclusion sentence — not a topic label
- Do not fabricate numbers, clients, logos, or missing data

[Design Requirements]
- Read the design lock; apply hex values, font names, and layout rules as hard constraints
- Do not introduce colors, fonts, or gradients not present in the design lock
- Vary layout families across slides — do not repeat the same layout 3 times in a row

[Build Requirements]
- Use editable pptxgenjs text boxes, shapes, lines, and tables throughout
- No embedded screenshots as proof objects unless user explicitly provides image files
- Keep chart code compact; use direct data labels instead of chart legends where possible

[QA Requirements]
- After generating the PPTX, run the local thumbnail script only if it exists: `python3 skills/pptx/scripts/thumbnail.py PPTX/<task-slug>/final/<task-slug>.pptx`
- Generate or copy per-slide rendered images, then create a view-only HTML companion at `PPTX/<task-slug>/final/<task-slug>-companion.html`
- Review thumbnails for: text overflow, font substitution, layout collision, color violations
- Fix at least one identified issue and regenerate before declaring done
- Final reply must include: PPTX absolute path, HTML companion path, thumbnail path, remaining risks for human review
```

---

## Template C — Native Reveal.js HTML Deck

Use this when the target output is an HTML presentation for online sharing — not when an editable PPTX is required.

```
Generate a native Reveal.js 5.1.0 HTML presentation deck. Do not call external html-ppt-skill or guizang-ppt-skill as a runtime dependency; use the internalized catalogs in:
- skills/deck-builder/references/html-theme-catalog.md
- skills/deck-builder/references/html-layout-catalog.md
- skills/deck-builder/references/html-animation-catalog.md

[Input Files]
- Content source: <resolved path to deck.md>
- Design lock: <resolved design lock path, or inline visual contract if no lock file exists>

[Output Target]
- Versioned HTML: `PPTX/<task-slug>/vN/final.html`; after final selection copy to `PPTX/<task-slug>/final/<task-slug>.html`

[Narrative Requirements]
- Before writing any HTML, produce a claim spine:
  thesis / audience / one-line arc / per-slide claim / proof object / source
- Every slide title must be a conclusion sentence — not a topic label
- Do not fabricate numbers, clients, logos, or missing data

[Design Requirements]
- Select a theme key, layout family, and animation profile from the internal catalogs.
- Use `html_motion_level` and `html_motion_profile` when present; cinematic currently means CSS-only enhanced motion, not Canvas/WebGL.
- Vary layout families — do not repeat the same layout 3 times in a row
- Do not introduce colors not in the design lock

[Build Requirements]
- All slides must be self-contained in the output HTML file
- Include speaker notes in the slide notes area where applicable
- Enable Reveal.js notes/presenter support when the deck will be presented to a live audience

[QA Requirements]
- Open the HTML file in a browser and verify all slides render at 16:9 aspect ratio
- Check for text overflow and layout collisions in full-screen mode
- Verify consistent visual rhythm across slides — no abrupt style break
- Final reply must include: HTML absolute path, catalog keys used, any layout risks for human review
```

---

## Iteration Feedback Templates

Use these when the generated deck needs revision. Specify page number and expected outcome — do not use vague requests like "make it better."

| Problem | Feedback Template |
|---------|------------------|
| Title is a topic label | `Slide <N> title: change to a conclusion sentence that states why <topic> matters.` |
| Repeated layout | `Slides <N> and <M> both use three-card layout. Keep slide <N>, change slide <M> to <timeline / comparison / big-number / diagram>.` |
| Weak data slide | `Slide <N>: make the primary metric the proof object — <N>pt number, two lines of context on the right. Remove the four small cards.` |
| Too much text | `Slide <N>: compress body to 3 sentences, max 16 Chinese characters per line.` |
| Unclear chart | `Slide <N>: remove the chart legend, apply direct annotation. Reduce x-axis labels to 4 values.` |
| Design lock violation | `Slide <N> introduced a gradient not in the design lock. Return to <lock name>'s flat color system.` |
| Invented data | `Slide <N> contains a metric with no cited source. Replace with "pending measurement" or remove.` |

---

## Render QA Checklist

After generation, verify all of the following:

**Contact Sheet**
- [ ] All slides visible as thumbnails
- [ ] Consistent visual rhythm — no abrupt style break between slides
- [ ] Section openers visually distinct from content slides

**Full-Size Preview**
- [ ] No title text wraps awkwardly onto a third line
- [ ] No body text overflows its container
- [ ] Charts and diagrams are legible at slide scale
- [ ] Footer and page number do not collide with content

**PowerPoint File**
- [ ] All text boxes are editable
- [ ] All shapes and connectors are native objects (not images)
- [ ] Chinese fonts render correctly or have a documented fallback

**Content**
- [ ] No fabricated numbers, company names, or logos
- [ ] All "missing" items are explicitly flagged
- [ ] Thesis claim appears on slide 01 or 02

---

## Generation Engine Quick Reference

| Environment | Primary Engine | Fallback | Quick Draft / PDF |
|-------------|----------------|----------|-------------------|
| Codex | Presentations + artifact-tool presentation-jsx | — | Marp (not editable PPTX) |
| Claude Code | skills/pptx + pptxgenjs | — | Marp |
| Offline / local | skills/pptx + pptxgenjs | — | Marp |
| HTML online sharing | installed HTML deck skill | browser print / PDF export | static HTML handoff |
| Need Google Slides | Generate PPTX first → import via Google Drive | — | — |

PPTX routes still produce a view-only HTML companion for simple sharing. That companion is generated from rendered slide previews and is not the editable source.
