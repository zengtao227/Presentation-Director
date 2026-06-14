---
name: deck-builder
description: Orchestrates professional presentation creation from source materials. In Codex net-new presentation requests, this skill MUST run Presentation Director intake, output format selection, research strategy, visual inspiration, and brief confirmation before routing to pakco-compatible HTML deck output, Codex Presentations, or both. For Claude/offline paths it coordinates deck.md planning, design intelligence, visual contracts, and verified output. Do NOT trigger for small edits to existing slides, quick Marp/reveal.js previews, or requests that do not require a new deck workflow.
---

# Deck Builder

A workflow orchestration skill for building professional presentations.

In Codex, this skill is the front door for net-new presentation requests: run `Presentation Director` first, confirm output format, research strategy and visual inspiration, open the confirmation page, automatically wait for the click confirmation signal, then route the confirmed brief by `output_format`. Use pakco-compatible HTML direct writing for `html-revealjs`, Codex Presentations for `pptx`, and both paths for `both`. If `pptx` is selected in Codex, do not decide Presentations is missing only because it is absent from plugin UI or tool search; first resolve the bundled runtime under `$HOME/.codex/plugins/cache/openai-primary-runtime/presentations/*/skills/presentations`, run its runtime check, then use its artifact-tool build script for PPTX export. If neither the plugin nor bundled runtime is available, stop and report that the required Codex Presentations runtime is missing; do not silently fall back to `python-pptx`, pptxgenjs, Google Slides, Keynote, or PowerPoint automation. The user must only click in the HTML UI; do not ask them to copy/paste, report choices in chat, or reply "confirmed". Do not let generation start from an unconfirmed prompt unless the user explicitly asks to skip the director.

Outside Codex, this skill coordinates the fuller deck.md-centered workflow: source material through slide planning, design intelligence, visual contract, and verified PPTX or HTML output.

This skill does NOT generate slides directly. It routes to the correct generation engine based on the active environment and target output format.

---

## Request Boundary Check

> **DEFAULT RULE — when in doubt, use Presentation Director.** Any request involving a presentation, slide deck, PPT/PPTX, or "把这些内容做成演示文稿/HTML" goes through the Director pipeline (intake → research strategy → visual inspiration → brief confirmation → image gate → generation → preview-review → style-review). This explicitly includes **beautifying an existing PPTX, converting a PPTX to an HTML deck, restyling, or porting slides to a new format.** Do NOT hand-write an HTML deck or call a generator directly just because a source PPTX already exists — an existing PPTX is *source material*, and the user still needs the confirmation gates and the preview/revision loop. The only requests that skip the pipeline are the narrow "Handle directly" rows below.

Before starting this pipeline, verify the request actually needs a new deck:

| Request Type | Action |
|-------------|--------|
| New PPTX/HTML from source material in Codex | **Run Presentation Director before Presentations** |
| New deck from source material outside Codex | **Run Presentation Director, then deck.md-centered pipeline** |
| **Beautify / restyle / reformat an existing PPTX** | **Run Presentation Director — PPTX is source material** |
| **Convert an existing PPTX to an HTML deck** | **Run Presentation Director — PPTX is source material** |
| New deck from an existing deck as a template/base | **Run Presentation Director (source_boundary = existing-doc)** |
| Slide plan review or deck.md revision | **Proceed with this pipeline** |
| Single-slide text fix in existing deck | Handle directly — skip this pipeline |
| QA pass on an existing generated deck | Handle directly — skip this pipeline |
| Quick Marp / reveal.js preview | Handle directly — skip this pipeline |
| Format-only change (color, font size) on an already-Director-generated deck | Handle directly — skip this pipeline |

If in doubt: does this produce or transform a presentation the user will show to an audience? If yes, use Presentation Director. A pre-existing PPTX does not exempt the request — it is source material, not a reason to skip the gates. In Codex, start with Presentation Director. Outside Codex, also start with Presentation Director, then continue with the deck.md-centered path.

---

## Trigger Scope

**Use this skill when:**
- Generating a new deck from an article, book, knowledge document, or engineering project materials
- The user asks Codex to create a new PPTX / PowerPoint / presentation from source material
- **The user gives an existing PPTX and asks to beautify it, restyle it, or convert it to an HTML deck** — the PPTX is source material; run the full pipeline
- The request implies slide planning, deck.md authoring, or design system selection
- The user asks for a professional, editable, or high-quality presentation
- The user mentions "Presentation Director", "slide planner", "deck.md", "design lock", or "visual contract"

**Do NOT trigger when:**
- Fixing a typo or rewriting a single slide in an existing deck
- Creating a quick Marp or reveal.js preview file
- The user only asks to change one formatting value (e.g. a single color/font size) in a deck this pipeline already generated
- No new deck planning is required

A pre-existing PPTX is NOT a reason to skip this skill. "Make this PPTX prettier" and "turn this PPTX into HTML" are full pipeline requests: the user still needs format/language confirmation, visual direction, and the preview → revision loop.

---

## Installation Paths

Canonical copy lives in Presentation Director; sync to global locations as needed:

```
Presentation Director/skills/deck-builder/         ← canonical source
~/.claude/skills/deck-builder/       ← Claude Code (global)
~/.codex/skills/deck-builder/        ← Codex (sync only if ~/.codex/skills/ exists)
```

VS Code agent support depends on the specific agent extension — check its skill loading config separately.

Sync command after edits to canonical:
```bash
# Run from the Presentation Director repository root.
mkdir -p "$HOME/.claude/skills" "$HOME/.codex/skills"
rm -rf "$HOME/.claude/skills/deck-builder" "$HOME/.codex/skills/deck-builder"
cp -R "$(pwd)/skills/deck-builder" "$HOME/.claude/skills/"
cp -R "$(pwd)/skills/deck-builder" "$HOME/.codex/skills/"
```

---

## Dependency Resolution

This skill is global, so do not assume Presentation Director local paths exist in every project.

Resolve dependencies in this order:

| Dependency | Resolution |
|------------|------------|
| Presentation Director | Use `scripts/presentation_director.py` in the current repo if present; otherwise use `scripts/presentation_director.py` beside this SKILL.md. In Codex net-new PPTX requests, this is the first step before Presentations unless the user explicitly skips it or a user-confirmed brief already exists. |
| Codex Presentations runtime | First use the active Presentations skill / plugin if exposed. If it is not exposed, resolve `$HOME/.codex/plugins/cache/openai-primary-runtime/presentations/*/skills/presentations`, set `SKILL_DIR` to that directory, run `node "$SKILL_DIR/scripts/check_presentation_runtime.mjs" --workspace "$WORKSPACE"`, then export net-new PPTX with `node "$SKILL_DIR/scripts/build_artifact_deck.mjs"`. Plugin UI absence is not a missing-runtime signal. |
| `design-consultant` | Use the current repo's `skills/ui-ux-pro-max/scripts/search.py` if present; otherwise try `$HOME/.claude/skills/ui-ux-pro-max/scripts/search.py`, then `$HOME/.codex/skills/ui-ux-pro-max/scripts/search.py`. If none exists, synthesize a short design intelligence brief from the source and mark the tool as unavailable. |
| `design-locks/` | Use the current repo's `design-locks/` if present. Otherwise look for `design-locks/` inside the directory containing this SKILL.md (bundled by install.sh). If neither exists, use a lightweight visual contract written directly in `deck.md` and do not cite a missing lock file. |
| PPTX fallback | Use `skills/pptx/SKILL.md` only outside Codex, or when the user explicitly asks to bypass Codex Presentations. In Codex `pptx` / `both` mode, missing Presentations means active plugin and bundled runtime are both unavailable or the runtime check failed; it is a blocker, not a reason to run fallback tooling. |
| HTML deck runtime | Native HTML output path. When `output_format` is `html-revealjs` or `both`, write a pakco-compatible HTML deck using the bundled `skills/html-deck/pakco-html/` assets plus `references/html-theme-catalog.md`, `references/html-layout-catalog.md`, and `references/html-animation-catalog.md`. `html-revealjs` remains the legacy output-format name. |
| Presentation Director docs | Treat `docs/pptx-master-workflow.md` and `docs/quality-gates.md` as optional project-level context. Outside Presentation Director, rely on this skill's reference files and the minimum QA checklist below instead. |

Never include file paths in a generation prompt unless those files actually exist.

---

## Deck Workspace Rule

For any project, keep all user-facing deck artifacts in one project-local folder. New tasks use `Decks/<task-slug>/`; existing legacy `PPTX/<task-slug>/` folders remain readable for compatibility:

```text
Decks/<task-slug>/
```

Do not scatter generated brief files, intake pages, contact sheets, QA summaries, revision requests, comparison files, or final PPTX/HTML outputs across the project root, `assets/`, or unrelated folders.

Recommended structure:

```text
Decks/<task-slug>/
  sources/                # optional copied user assets
  brief/                  # optional notes and source summaries
    visual-contract.md    # task-level visual contract after direction confirmation
  intake.html
  image-style.html
  image-placement.html
  brief-confirm.html
  brief-confirmed.json
  image-plan.json
  image-assets.json
  image-placement-request.json
  preview-review.html
  style-review.html
  revision-request.json
  compare.html
  final-selection.json
  v1/
    final.pptx
    final.html             # if output_format is html-revealjs or both
    slides/
      slide-001.png
      slide-002.png
    contact-sheet.png
    qa-summary.md
  v2/
    final.pptx
    final.html
    slides/
    contact-sheet.png
    qa-summary.md
  final/
    <task-slug>.pptx
    <task-slug>.html       # Reveal.js deck when output_format is html-revealjs or both
    <task-slug>-companion.html  # PPTX-only view-only companion
    final-report.md
```

Codex Presentations may still use its required internal scratch workspace under `outputs/<thread-id>/presentations/...`. That scratch space is not the user-facing project folder. Copy final deliverables, per-slide preview images, and key review artifacts back into `Decks/<task-slug>/`.

Every final PPTX-only deliverable must also have a view-only HTML companion at `Decks/<task-slug>/final/<task-slug>-companion.html`, generated from rendered slide previews. This companion is for simple sharing only; edit the PPTX and regenerate the companion after changes. In `both` mode, `final/<task-slug>.html` is the Reveal.js deck and no separate companion is generated.

Final PPTX files are the editable source of record. For small changes, use manual PowerPoint editing or Codex Presentations targeted-edit instead of regenerating the full deck. Save targeted edits as a new version folder and regenerate the HTML companion from the updated render previews.

---

## Slide Safe-Area Contract

Every deck must define a safe area before generation and verify it after rendering. This applies to PPTX, HTML decks, and PPTX-derived HTML companions.

Default 16:9 authoring coordinates use a `1280x720` slide. Unless a template or design lock defines stricter margins, use:

```text
content safe area: x=54, y=70, width=1172, height=590
slide frame:       x=0,  y=0,  width=1280, height=720
```

Hard rules:

- Essential content must stay inside the content safe area: titles, subtitles, body text, screenshots, diagrams, charts, tables, icons that carry meaning, callouts, controls, and code blocks.
- Backgrounds, grids, full-bleed decorative fills, and intentional hero imagery may extend to the slide frame, but they must not crop or hide essential content.
- Slide chrome such as page numbers, footers, source labels, and tiny kicker rows may use a reserved chrome band, but they must still stay inside the slide frame and must not collide with the content safe area.
- Any screenshot, product image, code image, or rendered preview placed on a slide must use a real bounding box inside the safe area. Do not let it rely on `overflow:hidden` to hide the part that ran outside the page.
- If a proof object cannot fit inside the safe area at readable size, split the slide or simplify the proof object. Do not shrink text below the deck's minimum readable size to force it in.

PPTX QA must run both the generator's layout checker and a safe-area check when layout JSON exists:

```bash
python3 <deck-builder-skill-dir>/scripts/check_presentation_safe_area.py \
  --layout "Decks/<task-slug>/v1/layout-or-presentations-layout-dir"
```

Inside the Presentation Director repo, `scripts/check_presentation_safe_area.py` is the same checker. If an engine cannot emit layout JSON, the agent must verify safe-area compliance from full-size rendered previews and record that manual check in `qa-summary.md`.

HTML decks must implement the same contract in CSS:

```css
.reveal .slides section {
  /* width + height required so section is a real 1280×720 box.
     overflow:hidden clips any true overflow.
     DO NOT set position — Reveal.js controls position:absolute on sections.
     Adding position:relative causes the staircase bug (all slides stack in flow).
     Omitting height causes section to collapse to 0px → .bleed/.slide-safe
     clipped to nothing → blank page. Both bugs confirmed by live testing. */
  width: 1280px;
  height: 720px;
  overflow: hidden;
}
.slide-safe {
  position: absolute;   /* positioned within the Reveal.js section */
  left: 54px;
  top: 70px;
  width: 1172px;
  height: 590px;
  overflow: hidden;     /* hard boundary — content beyond 590px is clipped */
}
.slide-safe img,
.slide-safe video,
.slide-safe canvas,
.slide-safe pre {
  max-width: 100%;
  max-height: 100%;
}
.bleed {
  position: absolute;
  inset: 0;
}
```

## HTML Deck CSS & Layout Rules (live-tested, confirmed)

> **Core principle:** Generate with px and hard layout rules to minimize risk; verify with browser-measured scrollHeight after render; auto-scale is only a safety net for small errors (≤14%); severe overflow must trigger a redesign, not more shrinking.

### Rule 1 — Font units: px for decorative elements, em/rem only for body text

```css
/* ❌ WRONG — 1.3em × 42px base = 54px; three stacked cards = instant overflow */
font-size: 1.3em;

/* ❌ STILL WRONG — 0.9em is still theme-dependent (0.9 × 42 = 38px but another
   theme may use a different base) */
font-size: 0.9em;

/* ✅ CORRECT — always predictable */
font-size: 28px;
line-height: 1;
```

**Decorative elements** (emoji, icons, FontAwesome, decorative numbers): always `px`, never `em`.  
Recommended sizes: `20px`–`34px` for icons, `16px`–`22px` for body copy.  
`line-height` may use unitless values (e.g. `1.15`, `1.25`, `1.35`).

### Rule 2 — Stagger is opt-in only

`stagger` applies staggered `translateY(18px)` delays. During animation, items render at different Y positions — vertical lists appear diagonal/staircase to viewers.

```html
<!-- ❌ WRONG — steps, timelines, flow cards -->
<div class="steps stagger">

<!-- ✅ CORRECT — single container animation -->
<div class="steps fade-up">
```

`.stagger` is forbidden by default. It is allowed for any horizontal row of uniform parallel items. If such usage is intentional, mark the container with both `.stagger` and `.stagger-ok`; without `.stagger-ok`, the guard fails.

The guard blocks `.stagger.stagger-ok` on:
- **Vertical stacks**: `ul`, `ol`, `flex-direction:column` containers
- **Explicitly forbidden names**: `.cols`, `.cmp`, `.compare`, `.comparison`, `.flow`, `.flow-list`, `.pipeline`, `.steps`, `.tc`, `.timeline`

No specific class name is required — any container not in the forbidden list and not a vertical stack passes with `.stagger.stagger-ok`.

```html
<!-- ❌ WRONG — no stagger-ok marker -->
<div class="cmp stagger">

<!-- ❌ WRONG — .cols is in the forbidden-names list -->
<div class="cols stagger stagger-ok">

<!-- ✅ CORRECT — animate the whole container as one unit -->
<div class="cmp fade-up">

<!-- ✅ CORRECT — stagger-ok on a non-forbidden horizontal row -->
<div class="feature-cards stagger stagger-ok">
<div class="icon-row stagger stagger-ok">
```

**Rule summary:** default to `fade-up` on the container or `rise-in` on individual elements. Use `.stagger.stagger-ok` for a horizontal row of uniform parallel items (any class name, as long as it is not in the forbidden list).

### Rule 3 — Height budget (pre-flight estimate only, not final arbiter)

Available content height = 590px − slide-h (~75px) = **~515px**.

| Element | Estimated height |
|---------|-----------------|
| List item (`.il li`) | 28px |
| Step row (`.step`) | 60px |
| Small card (single-line body) | 55px |
| Large card (3–4 line body) | 90px |
| Icon/emoji at 28px | 28px + padding |

Budget rules:
- Max 4 steps per slide (split if 5+)
- Max 5 bullet points per list
- Max 6 table rows
- **This 515px estimate is a pre-flight check, not the final verdict. Browser scrollHeight is the final arbiter.**

#### Split-layout specific constraints (confirmed by live testing)

Split layouts (`grid-template-columns: 1.05fr .95fr`) give each column ~573px wide and consume the full slide height. The column's content must fit within the remaining height after the slide header (kicker + h2 + margins ≈ 99px), leaving **~491px per column**.

| Screenshot class | Height | Safe to add below in split column |
|-----------------|--------|----------------------------------|
| `shot-wide` (420px) | 420px | kicker + h2 + 1-line caption only — nothing else |
| `shot-mid` (370px) | 370px | max 1-line caption (≤20px); 2+ lines = overflow risk |
| `shot-small` (310px) | 310px | caption + 1 short paragraph, safe |

| Lower-padding class | Value | Risk in split column |
|--------------------|-------|---------------------|
| `lower-16` | 16px | safe |
| `lower-28` | 28px | safe |
| `lower-40` | 40px | risky with 3+ cards |
| `lower-52` | 52px | **high risk** — avoid in split columns with cards |

Split-column hard rules:
- `shot-mid` + `lower-16` + caption (2-line wrapping text) = **overflow confirmed** (+19px in testing). Shorten to 1 line or use `shot-small`.
- Three step cards with borders + `section-heading` + equation inside a split left column = **overflow confirmed** (+9px). Use full-width `flow3` layout instead.
- When in doubt: prefer full-width layouts (`flow3`, `grid g3`) over split when the left column contains both a screenshot and a caption.

### Rule 4 — Two-column balance: right column must stretch

When a right column has fewer items than the left, items stack at the top — visually unbalanced.

```html
<!-- ✅ Right column stretches full height and distributes content -->
<div class="tcr" style="display:flex;flex-direction:column;justify-content:space-between;">
  <div class="card">...top content...</div>
  <div class="card">...bottom content pinned to bottom...</div>
</div>

<!-- ✅ Alternative: push last element to bottom -->
<div class="tcr" style="display:flex;flex-direction:column;">
  <div class="card">...top...</div>
  <div class="card" style="margin-top:auto;">...bottom...</div>
</div>
```

### Rule 5 — slide-safe must be flex when using margin-top:auto

`margin-top:auto` only works inside a flex container. If distributing content vertically inside `.slide-safe`, set it explicitly:

```html
<div class="slide-safe" style="display:flex;flex-direction:column;">
```

### Rule 6 — Browser overflow QA (required in every generated HTML deck)

Static estimates are not enough — font loading, line wrapping, and language-specific lengths can all push actual `scrollHeight` past 590px. Every generated HTML deck **must** include this QA script:

```html
<script>
// Overflow QA — checks both scrollHeight (≤590) and scrollWidth (≤1172).
// Auto-scales slides that overflow by ≤14% (scale ≥ 0.86).
// Marks slides that overflow by >14% as QA_FAIL (red outline).
// Runs after DOM + fonts load; window.load fallback catches late assets.
function runOverflowQA() {
  const SAFE_H = 590, SAFE_W = 1172, MIN_SCALE = 0.86;
  document.querySelectorAll('.slide-safe').forEach((safe, idx) => {
    const prev = safe.style.overflow;
    safe.style.overflow = 'visible';
    const sh = safe.scrollHeight;
    const sw = safe.scrollWidth;
    safe.style.overflow = prev || 'hidden';
    if (sh <= SAFE_H && sw <= SAFE_W) return;
    const scale = Math.min(SAFE_H / sh, SAFE_W / sw, 1);
    if (scale < MIN_SCALE) {
      console.error(`[QA_FAIL] Slide ${idx+1}: scroll=${sw}x${sh}px, scale=${scale.toFixed(2)} < 0.86 — must split or reduce content`);
      safe.style.outline = '3px solid rgba(255,50,50,0.8)';
    } else {
      const wrap = document.createElement('div');
      wrap.style.cssText = `transform:scale(${scale});transform-origin:top left;width:${(100/scale).toFixed(2)}%;`;
      while (safe.firstChild) wrap.appendChild(safe.firstChild);
      safe.appendChild(wrap);
      console.info(`[QA_FIT] Slide ${idx+1}: scroll=${sw}x${sh}px → scaled to ${(scale*100).toFixed(1)}%`);
    }
  });
}
document.addEventListener('DOMContentLoaded', () => {
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(runOverflowQA);
  } else {
    requestAnimationFrame(runOverflowQA);
  }
});
window.addEventListener('load', () => {
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(runOverflowQA);
  } else {
    runOverflowQA();
  }
});
</script>
```

This script must appear **after** the pakco runtime script. It will:
- Log `[QA_FIT]` for auto-corrected slides (scale 0.86–1.0)
- Log `[QA_FAIL]` + red outline for slides that are too dense (scale < 0.86)
- Do nothing for slides that fit correctly

Auto-scale is a safety net only — the goal is zero `[QA_FIT]` logs, not "let the script handle it".

### Why the earlier `.slide-safe` test produced layout failures

Overriding pakco `.slide` positioning or turning slide sections into normal document flow breaks keyboard navigation and can create staircase layouts. Keep `section.slide` under pakco `base.css`; put normal content inside `.slide-safe` and decorative backgrounds inside `.bleed`.

All regular slide content goes inside `.slide-safe`; only backgrounds and explicitly intentional bleed elements may sit outside it.

**Required structure for every slide — NO EXCEPTIONS including cover and section-divider slides:**

```html
<section class="slide" data-title="...">
  <div class="bleed ..."><!-- background gradient / image ONLY --></div>
  <div class="slide-safe">
    <!-- ALL content: title, body, columns, charts, code, images -->
  </div>
</section>
```

Inside `.slide-safe` use normal flow or flex/grid layout. Do NOT use `position:absolute` on content elements inside `.slide-safe` unless stacking layers within those 1172×590 bounds.

**Forbidden patterns — these silently push content outside the visible area:**

| Pattern | Why it breaks |
|---------|---------------|
| **`position` on `.reveal .slides section`** | Reveal.js sets `position:absolute` on sections internally — any override switches all slides to document flow and produces the staircase bug (Slide 2 below Slide 1, etc.). **The guard now auto-fails on this pattern.** |
| `position:absolute` on direct children of `<section>` (other than `.bleed` / `.slide-safe`) | Bypasses safe-area coordinates entirely |
| `top:50%; transform:translateY(-50%)` on elements outside `.slide-safe` | Centres against the 720px section, not the 590px safe zone |
| `display:flex` or `display:grid` on the `<section>` element to position content | Replaces the absolute-position model; content escapes the safe zone |
| Arbitrary `left` / `top` / `right` / `bottom` on section children that bypass `.slide-safe` | Same as first row |
| **Unapproved `.stagger`** | `.stagger` is forbidden on content-bearing containers by default. It is allowed only for decorative, single-row, uniform horizontal card grids explicitly marked `.stagger-ok`. Forbidden on: vertical stacks (ul/ol/steps/timeline, flex-direction:column), comparison/content columns (`.cols`, `.cmp`, `.tc`), multi-row grids, and generic flex/grid containers. Use `.fade-up` on the container or `.rise-in` on each child instead. **The guard auto-fails on this pattern.** |
| Treating the cover slide as exempt ("it's decorative") | The cover is **not** exempt; title, subtitle, kicker, and badge all go inside `.slide-safe` |

For a two-column cover layout, put both columns inside `.slide-safe` and use `display:flex; flex-direction:row` there:</p>

```html
<section>
  <div class="bleed" style="background: linear-gradient(...)"></div>
  <div class="slide-safe" style="display:flex; align-items:center; gap:32px;">
    <div style="flex:1.6"><!-- left: title, kicker, subtitle --></div>
    <div style="flex:1"><!-- right: badge / stats --></div>
  </div>
</section>
```

---

## Pipeline Overview

The confirmed `output_format` is authoritative. If the user later asks in chat to switch between HTML, PPTX, or both, do not generate from the stale confirmed brief. Reopen the confirmation gate to update the brief, or require an explicit "skip confirmation / directly change to <format>" instruction and record that override in the final report.

### Codex Net-New Presentation Path

Use this path when the user asks for a new presentation in Codex. `output_format` decides whether the final generation route is HTML deck, PPTX, or both.

```
[1] Source Material
    topic / links / files / folder / existing notes
        ↓
[2] Presentation Director intake
    click-based audience, goal, source paths/URLs, research strategy, source boundary, content language, logo policy, image policy, output constraints
    UI communication language auto-detected from the current conversation; content_language remains the deck body language
        ↓
[3] Research Strategy Gate
    Codex deep web research / external Deep Research packet / hybrid / provided-only
        ↓
[4] Visual Inspiration Gate
    3 dynamic visual candidates from topic, deck type, audience, design-locks, ui-ux-pro-max, and deck UI references
        ↓
[5] Brief Confirmation Gate  ← HARD STOP
    open the confirmation page; user reviews the summarized plan and clicks "confirm"
        ↓
[5.5] Image Style Gate
    user confirms image_generation_mode and prompt drafts; write image-plan.json
    pre-v1 images are generated only from approved targets and recorded in image-assets.json
        ↓
[6] Generation — route by output_format in brief-confirmed.json
    ├─ output_format = "html-revealjs"
    │    → Claude/Codex writes pakco-compatible HTML directly (NOT via Presentations plugin)
    │    → Save version to Decks/<task-slug>/v1/final.html
    │
    ├─ output_format = "pptx"
    │    → Codex Presentations capability (active plugin or bundled runtime scripts)
    │    → Runtime check before PPTX work; build_artifact_deck.mjs for net-new PPTX export
    │    → If no runtime is available, STOP instead of using fallback tooling
    │    → Save version to Decks/<task-slug>/v1/final.pptx
    │
    └─ output_format = "both"
         → First: Codex Presentations capability → PPTX
         → Then: Claude/Codex writes pakco-compatible HTML directly → HTML
         → Save versions to Decks/<task-slug>/v1/
         → Note: HTML uses gradients/animation; PPTX uses solid-color equivalent
        ↓
[6.5] Image Placement Gate (post-v1-slot-review / hybrid only)
    user reviews v1 preview artifact and approves placements; write v2 outputs
        ↓
[7] Render QA
    PPTX route: previews + layout JSON + contact sheet + fix-and-rerender
    HTML route: open in browser + screenshot each slide + text-overflow check
        ↓
[8] Style Review
    user chooses keep/current or visual revision directions
        ↓
[9] Optional Revised Versions + Compare
        ↓
Decks/<task-slug>/final/<task-slug>.pptx
Decks/<task-slug>/final/<task-slug>.html
Decks/<task-slug>/final/<task-slug>-companion.html  # PPTX-only
```

For this Codex path, do not pre-lock `design-locks/`, palette, or per-slide layout before v1 unless the user explicitly asks. The visual inspiration gate should select a direction, not a rigid template. The goal is to lock intent, source boundaries, research strategy, and visual target, then give Presentations room to produce a stronger first draft.

In interactive Codex sessions, the confirmation gate is a real user-action gate: the agent must not POST `/api/confirm`, write `brief-confirmed.json`, or touch `confirmed.ready` on the user's behalf. Use the local Director server, open the confirm page, wait for the user's click, then let `serve-wait --then-guard` run the generation guard. Start generation only after `status/guard-passed.ready` exists or `GUARD_PASSED` is visible in flushed output. The only exception is an explicit user instruction to skip confirmation or generate directly.

### Claude / Offline / HTML Path

```
[1] Source Material
    Article / book / knowledge doc / engineering project / topic
        ↓
[1.5] Presentation Director / Equivalent Intake Gate
    content_language → output_constraints → research boundary → visual target
    user confirmation required before generation
        ↓
[2] Slide Planner  ← NEVER skip this step
    audience → thesis → arc → slide claims → proof objects → omissions
    Output: slide-plan.md
        ↓
[3] deck.md
    Thesis, audience, per-slide: claim + proof object + source
        ↓
[4] 颜色层 (Color Layer)
    design-consultant → 2-3 套配色方案（可视色块）→ 迭代调整 → 用户确认
        ↓
[5] 结构层 (Structure Layer)
    展示全部 5 个 design-locks → 用户选择 → 记录颜色覆盖 → 两层都确认后才 lock
        ↓
[6] Generation — route by output_format in brief-confirmed.json or chat confirmation
    ├─ output_format = "html-revealjs"
    │    → Claude writes pakco-compatible HTML directly (see HTML Spec in this skill)
    │    → Single .html file, CDN-loaded
    │    → Save versions to Decks/<task-slug>/vN/final.html, then copy the selected version to final/<task-slug>.html
    │
    ├─ output_format = "pptx"
    │    → skills/pptx + pptxgenjs (existing path, no change)
    │
    └─ output_format = "both"
         → Generate HTML first, then PPTX
         → HTML uses gradients/animation; PPTX uses solid-color equivalent
        ↓
[7] Render QA
    Contact sheet + layout JSON + at least one fix-and-reverify cycle
        ↓
PPTX route:
  Decks/<task-slug>/final/<task-slug>.pptx   ← editable primary output
  Decks/<task-slug>/final/<task-slug>-companion.html   ← view-only share companion

HTML-deck-only route:
  Decks/<task-slug>/final/<task-slug>.html   ← full HTML deck output
```

Skipping Step 2 produces information dumps, not presentations.

Claude Code and offline agents follow the same confirmation principle as Codex. If the Presentation Director helper is available, run its intake/confirmation flow and `guard` before generating with pptxgenjs or HTML tooling. If it is not available, present an equivalent chat/static confirmation covering `content_language`, `output_constraints`, audience, goal, slide plan, source boundary, and visual direction; stop until the user explicitly confirms.

---

## Tool Routing

| Environment | Generation Path | Notes |
|-------------|-----------------|-------|
| Codex net-new PPTX | Presentation Director → Presentations capability **(primary PPTX)** | Intake + research strategy + visual inspiration + brief confirmation must happen before `artifact-tool presentation-jsx`; plugin UI absence requires bundled runtime resolution |
| Codex targeted edit / confirmed brief | Presentations capability | Direct only when not creating a new deck or when `brief-confirmed.json` already exists |
| Claude Code / offline | Presentation Director or equivalent confirmation → `skills/pptx` + pptxgenjs **(fallback PPTX)** | Same `content_language` / `output_constraints` split and user-confirmation gate apply before pptxgenjs |
| Codex / Claude Code (HTML) | Claude/Codex writes pakco-compatible HTML deck directly | Native path. Use bundled `skills/html-deck/pakco-html/` assets; do not install or invoke global pakco-html as a separate skill. |
| Either | Marp | Quick draft / PDF only — not editable PPTX |

**Hard constraints — never misattribute these roles:**
- Presentation Director = Codex intake / confirmation / revision-choice layer, NOT a PPTX generator
- `ui-ux-pro-max` = design intelligence tool, NOT a PPTX generator
- `design-locks/` = visual contracts, NOT slide templates or generation engines
- pptxgenjs = Claude Code fallback only, NOT the Codex primary path
- In Codex `pptx` or `both` mode, missing Presentations means both active plugin and bundled runtime are unavailable or the runtime check fails. Plugin UI absence alone is not enough. Do not use `python-pptx`, pptxgenjs, Google Slides, Keynote, or PowerPoint automation as a substitute unless the user explicitly asks to bypass Presentations.
- HTML deck = first-class browser presentation output when selected, NOT a PPTX replacement
- Marp output = NOT a professional editable PPTX

**Claude Design / designer-skills boundary:**
- If Claude Code has `designer-skills` installed, treat those skills as optional design support, not as the PPT workflow owner.
- Do not let any frontend or design-system skill replace Presentation Director intake, slide planning, `deck.md`, brief confirmation, visual contract selection, generation routing, or render QA.
- Use optional design support only to refine Director HTML gates, HTML companions, or the task-level `Decks/<task-slug>/brief/visual-contract.md`.
- When a task-level `visual-contract.md` exists, it overrides the global `design-locks/` choice for that deck.

---

## Execution Steps

## HTML Deck Generation Spec

When `output_format` is `"html-revealjs"` or `"both"`, generate a pakco-compatible HTML presentation. `html-revealjs` is a legacy enum value; the implementation uses the bundled pakco runtime and theme assets.

This applies to both Codex and Claude Code. In Codex, write the HTML as a file artifact or local file; do NOT call Presentations plugin for HTML. Write candidate versions to `Decks/<task-slug>/vN/final.html`; after final selection copy the chosen version to `Decks/<task-slug>/final/<task-slug>.html`.

### Bundled Asset Contract

- Resolve the bundled pakco root from the current project at `skills/html-deck/pakco-html/`.
- Include or inline `assets/fonts.css`, `assets/base.css`, `assets/themes/{theme_key}.css`, `assets/animations/animations.css`, and `assets/runtime.js`.
- Use pakco theme tokens: `--bg`, `--bg-soft`, `--surface`, `--surface-2`, `--border`, `--text-1`, `--text-2`, `--accent`, `--accent-2`, `--accent-3`, and `--grad`.
- Do not install pakco-html globally or treat it as a separate generation route.

### HTML Structure

```html
<!DOCTYPE html>
<html lang="{content_language}" data-theme="{theme_key}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{deck_title}</title>
  <link rel="stylesheet" href="./assets/fonts.css">
  <link rel="stylesheet" href="./assets/base.css">
  <link rel="stylesheet" id="theme-link" href="./assets/themes/{theme_key}.css">
  <link rel="stylesheet" href="./assets/animations/animations.css">
</head>
<body data-themes="{theme_list}" data-theme-base="./assets/themes/">
  <div class="deck">
    <section class="slide" data-title="{slide_title}">
      <p class="kicker">{kicker}</p>
      <h1 class="h1 anim-fade-up">{deck_title}</h1>
      <p class="lede">{subtitle}</p>
      <aside class="notes">{speaker_notes}</aside>
    </section>
  </div>
  <script src="./assets/runtime.js"></script>
</body>
</html>
```

### Content Density Rules — MUST follow to prevent overflow

These rules are hard constraints for every content slide. A slide that looks complete in source material may overflow a 1280×720 viewport. When in doubt, split into two slides.

| Element | Limit |
|---------|-------|
| Bullet points per column / list | ≤ 5 items |
| Words per bullet | ≤ 15 words |
| Content sections per slide | ≤ 2 (e.g., two columns = 2 sections) |
| Table rows (including header) | ≤ 8 rows |
| Nested columns inside a two-col layout | No — each cell has at most one list or one diagram |
| Font size floor | Never set `font-size` below `0.55em` to compensate for density |

When source content exceeds these limits, **split the slide**, do not compress. Use a consistent title with a " (cont.)" suffix for the second slide.

### CSS Overflow Safeguards — include in every generated HTML

Add these rules to the `<style>` block of every HTML deck. They prevent content from escaping the slide boundary invisibly.

```css
/* Overflow safeguard */
.reveal .slides section { box-sizing: border-box; height: 100%; overflow: hidden; }
.slide-body {
  overflow: hidden;
  height: calc(100% - 62px);   /* 62px = slide-header rendered height */
  box-sizing: border-box;
  padding: 0.45em 1.1em 0.3em;
  display: flex;
  flex-direction: column;       /* enables .src margin-top:auto */
}
/* Source line always pinned to bottom */
.src { font-size:.42em; margin-top:auto; flex-shrink:0; }
```

If the deck does not use a `.slide-body` wrapper, apply instead:

```css
.reveal .slides section { overflow: hidden; box-sizing: border-box; }
```

**Also enforce these structural rules:**
- Each slide has exactly **one** `h2.slide-title` at the top (≈ 0.95em). Inside two-col columns, replace with `.col-title` (0.62em) — the size difference saves ~35px per column heading and is the most common cause of content overflow.
- `.src` always sits as the last child of `.slide-body` and gets `margin-top:auto` — this pins all source lines to the same visual baseline across all slides.
- Place every normal content element inside `.slide-safe`; images, screenshots, code blocks, tables, and diagrams must be contained by the safe area and may not extend outside the slide, even if the section itself hides overflow.

---

### Design Language System — Gradient Text, 3D Depth, and Glow

These are reusable design rules for the Biotech Pipeline dark theme and similar dark-background decks. Apply consistently across all slides of a deck.

#### Gradient Text Classes

| Class | Color | Use |
|-------|-------|-----|
| `.grad-cyan` | Cyan (#4cc9f0 → #74d8f5) | Key terms, accent data, drug names |
| `.grad-gold` | Gold (#ffb703 → #ffd460) | Warnings, secondary metrics, contrast points |
| `.grad-two` | Cyan → violet → gold | Cover title line 1 only |
| `.grad-light` | Near-white (#ddeeff → #f2f9ff) | Cover title line 2 only |

**Gradient base classes carry zero glow.** Glow is a separate utility — see below.

#### Cover Title 3D System

The cover title uses **`text-shadow` for 3D depth**, not `filter: drop-shadow`. `text-shadow` casts from letter glyph shapes and works on gradient text (where `-webkit-text-fill-color: transparent` would make `filter: drop-shadow` invisible on dark backgrounds).

**Template rule: title lines must be uniform in technique.** Every line — whether the title is 1, 2, or 3 lines — must have: gradient color + 3D depth + glow animation. Never mix "some lines have glow, some don't" or "some lines are gradient, some are plain."

```css
/* Shared 3D — applied to .cov-h1 container; inherited by ALL child lines */
.text-3d {
  text-shadow:
    0  1px  0 rgba(76,201,240,.30),   /* cyan top shimmer  */
    0  4px  0 rgba(0,0,0,.88),         /* hard extrusion edge (no blur = crisp) */
    0  7px 14px rgba(76,201,240,.22),  /* cyan mid-depth glow */
    0 12px 28px rgba(0,0,0,.50);       /* far volume shadow */
}

/* Gradient classes — pure color only; depth comes from inherited text-shadow */
.grad-two   { background: linear-gradient(135deg, #4cc9f0 0%, #a78bfa 50%, #ffb703 100%); ... }
.grad-light { background: linear-gradient(90deg,  #ddeeff 0%, #f2f9ff 100%); ... }
```

**Cover title HTML template** (1–3 lines, all uniform):

```html
<div class="cov-h1 text-3d">
  <span class="grad-two  glow-c">Line 1 / full title if single line</span><br>
  <span class="grad-light glow-w">Line 2 (if needed)</span><br>
  <span class="grad-cyan  glow-hero">Line 3 — final/tagline line</span>
</div>
```

- 1-line title: use a single span with `.grad-two.glow-c` (or `.glow-hero` for maximum impact)
- 2-line title: lines 1 + 3 (skip `.grad-light` line)
- 3-line title: all three, as above

Glow intensity creates a natural progression (moderate → moderate → strong), but all lines use the SAME technique. 3D depth is **cover title only** — never apply `.text-3d` to content slide headings.

#### Glow Utility Classes — Emphasis Only

Glow is an **attention tool, not decoration**. The rule: only elements that are deliberately enlarged or explicitly highlighted may receive glow.

**Apply glow to:**
- Stat card numbers (`.stat-card .num`) — these are already 1.4em+
- Pillar / callout large numbers (`.pnum`, large inline metrics)
- The cover subtitle (`.glow-hero`)
- At most 1–2 emphasized numbers per content slide

**Never apply glow to:**
- Inline drug names or keywords in body text
- Bullet list items or table cells
- Slide headings (`h2.slide-title`, `.col-title`, `glass h4`)
- Any element where the text has not been explicitly enlarged for emphasis

| Class | Color | Keyframe range | Use |
|-------|-------|---------------|-----|
| `.glow-hero` | Cyan | 6 → 20px (+ depth) | Cover subtitle, 1 per deck |
| `.glow-c` | Cyan | 4 → 12px | Primary stat numbers, key metrics |
| `.glow-g` | Gold | 3 → 8px (softer — gold is visually loud) | Secondary gold callouts |
| `.glow-w` | White | 3 → 10px | White/near-white emphasized numbers |

```css
.glow-hero { animation: glowHero 2.8s ease infinite; display:inline-block; }
.glow-c    { animation: glow     2.8s ease infinite; display:inline-block; }
.glow-g    { animation: goldGlow 3.0s ease infinite; display:inline-block; }
.glow-w    { animation: whiteGlow 3.0s ease infinite; display:inline-block; }
```

These classes work on any color text, not just cyan/gold — the class name refers to the glow color, which should match the text color for visual coherence.

---

### Light Background — Image / Art Blending Rule

When placing any image, SVG illustration, or decorative artwork on a **light background** slide, the artwork must never have hard edges that abruptly border the background. Apply a `mask-image` radial gradient to the artwork's container so its edges fade smoothly into the slide background.

```css
/* Standard light-bg vignette — apply to the container wrapping the image/art */
.cov-r, .art-panel {
  -webkit-mask-image: radial-gradient(ellipse 78% 80% at center, black 38%, transparent 92%);
          mask-image: radial-gradient(ellipse 78% 80% at center, black 38%, transparent 92%);
}
```

**When to apply:**
- Cover right-panel artwork on light themes (Aurora Light and similar)
- Full-bleed decorative dividers between text and illustration columns
- Any photo or graphic where the background color is lighter than `#d0d0d0`

**Do NOT apply on dark backgrounds** — vignette is unnecessary when the artwork naturally blends into a near-black slide background.

**Bar-label wrapping rule:** The `.bar-label` column must always use `white-space: nowrap` and a width of at least `10em` to prevent longer labels (e.g., "Phase III (36 drugs)") from wrapping to a second line when shorter sibling labels ("Phase I …") stay on one line. Consistent label row height is a visual consistency requirement.

```css
.bar-row .bar-label { width:10em; text-align:right; color:var(--muted); flex-shrink:0; white-space:nowrap; }
```

---

### Animation Density Rules

| `html_animation` | Implementation |
|------------------|----------------|
| `minimal` | Do not use `data-auto-animate`; use `transition: 'fade'`; no gradient background. Visually equivalent to a clean PPTX — intentionally restrained. |
| `moderate` | Add `data-auto-animate` to selected sections; use the chosen transition; add gradients to key slides only (cover + section dividers). |
| `rich` | Add `data-auto-animate` to all sections; use the chosen transition; use gradients throughout including title slide; add entrance animations via CSS `@keyframes` on key data elements. |

### PDF Export

Append `?print-pdf` to the URL, open in Chrome/Edge, press Cmd+P, choose Save as PDF, disable headers/footers, and use landscape A4.

### Speaker Notes

Use `<aside class="notes">` inside each `<section>`. Press `S` to open presenter view.

### HTML QA Checklist

- [ ] Open in Chrome/Safari; deck loads without console errors.
- [ ] All slides advance correctly with arrow keys and spacebar.
- [ ] **No text overflows slide boundaries** — scroll through every slide and confirm no content is cut off at the bottom or sides. If any slide overflows: split the slide or remove content, do not reduce font size below 0.55em.
- [ ] **Safe area respected** — every non-background text block, screenshot, chart, table, code block, and diagram is fully inside `.slide-safe`; anything using `.bleed` is background-only.
- [ ] Gradients render as expected (if `html_animation` is `moderate` or `rich`).
- [ ] Speaker notes are visible in presenter view (`S` key).
- [ ] `?print-pdf` renders all slides without clipping.
- [ ] File is self-contained except pinned Reveal.js CDN links; no broken local paths.
- [ ] CSS overflow safeguards are present in `<style>` (`.slide-body { overflow: hidden; … }`).
- [ ] **Section CSS has NO `position` property** — the section rule must be `width:1280px; height:720px; overflow:hidden; box-sizing:border-box` only. The generation guard (`validate_generation_guard`) auto-fails if `section { position:... }` is detected.
- [ ] **`.stagger` is opt-in only** — `.stagger` is forbidden unless the container also has `.stagger-ok` and is a decorative, single-row, uniform horizontal card/tile/metric grid. Forbidden on vertical stacks, comparison/content columns, multi-row grids, and generic flex/grid containers. The generation guard auto-fails on these patterns.
- [ ] **Title position is a design decision, not a layout fix** — title alignment (left / center) and vertical position are chosen during brief confirmation and must stay consistent across all slides. When fixing a head-heavy layout, do NOT change the title's position or the section's `padding-top` as the solution; that moves every title and breaks visual consistency.
- [ ] **No head-heavy layout** — content fills at least 60% of the vertical space below the title. The correct fix is to increase internal spacing of content elements (card `padding`, grid `gap`, `line-height`, element `margin`). Never "fix" empty bottom space by shifting the title down, using `center: true`, or floating content to the middle of the slide.
- [ ] **Word-break rules present** — `word-break: break-word; hyphens: none; overflow-wrap: break-word;` on `.reveal` to prevent mid-word splits in mixed Chinese/English text.
- [ ] **Tool references are regional** — never hard-code a single AI product name. Always provide both: 🇨🇳 China options (Kimi / DeepSeek / 通义千问 / 文心一言) and 🌐 international options (Claude / GPT-4o / Gemini), or use the neutral term "AI 助手".

### Codex Mode — Presentation Director First

If the environment is Codex and the user asks for a net-new PPTX, use `scripts/presentation_director.py` before running Presentations.

1. Resolve the script path:

```bash
# Prefer repo-local helper.
python3 scripts/presentation_director.py --help

# If outside MD2PPT but this skill is installed globally, use the bundled helper.
python3 <deck-builder-skill-dir>/scripts/presentation_director.py --help
```

2. Initialize the director workspace:

```bash
python3 scripts/presentation_director.py init \
  --task "<short task slug>" \
  --topic "<inferred or user-provided topic>" \
  --source "<resolved source path or URL>" \
  --conversation-text "<recent user prompt or conversation excerpt>"
```

Use `--ui-language auto` by default. The Director HTML gates (`intake`, `visual-inspiration`, `confirm`, `image-style`, `image-placement`, `style-review`, and `compare`) should follow the user's current conversation language, while `content_language` controls the language of the generated slide content.

3. Start the local UI server and wait in the same command. In Claude Code, use `run_in_background=True` on the Bash tool. Across Claude Code, Codex, Antigravity, and other agents, treat `status/guard-passed.ready` as the authoritative "start generation" signal; process exit is only a convenience notification:

```bash
python3 scripts/presentation_director.py serve-wait \
  --task "<short task slug>" \
  --for confirmed --then-guard
# Run this with run_in_background=True in Claude Code.
# The process exits after guard passes and writes status/guard-passed.ready.
# Do NOT use process exit as a proxy for "confirmed"; use guard-passed.ready.
```

**Fixed protocol — "简报确认后自动开始生成" (Bug fix: confirmed -> auto-generate deadlock):**

The old behavior of `--then-guard` kept the server alive waiting for v1 output, which deadlocked
Claude Code (process waited for Claude Code to write v1; Claude Code waited for process exit).

**New behavior:** `--then-guard` exits immediately after:
1. Writing `status/guard-passed.ready` (the authoritative "start generation" signal)
2. Flushing `GUARD_PASSED` + generation prompt to stdout

After generation, open preview-review as a **separate step** (see step 8 below).

**Bug-prevention notes (Bug 1 & Bug 3):**
- `serve-wait` opens the intake page in the browser automatically. Do NOT run an extra `open` command or `open-page` after starting `serve-wait` — this causes a duplicate tab.
- Do NOT start `serve-wait` with a shell `&` suffix. Use the Bash tool's `run_in_background` parameter instead; that way Claude Code receives a completion notification and can continue automatically without polling.

4. Do not ask the user to copy a URL, paste JSON, or come back to chat to say "confirmed". The intake page opens automatically. The user submits intake choices, reviews visual inspiration, reviews the confirmation page, and clicks confirm. `serve-wait` runs the guard and exits — Claude Code is notified. If the page does not open, use:

```bash
python3 scripts/presentation_director.py open-page --task "<short task slug>" --page intake
```

For batch or background runs, use `--no-open`, but still pair it with `serve-wait` or `wait` so generation resumes from a file signal, not a chat reply.

5. Generate the handoff prompt:

```bash
python3 scripts/presentation_director.py prompt --task "<short task slug>" --kind initial
```

6. Before generation, complete the Image Style Gate if the confirmed brief lacks `image_generation_mode`:

```bash
python3 scripts/presentation_director.py serve-wait \
  --task "<short task slug>" \
  --open-page image-style \
  --for images-style
```

For pre-v1 modes, generate only the targets in `image-plan.json`. In interactive Codex sessions, run `skills/deck-builder/scripts/generate_images.py --task-dir "Decks/<task-slug>" show`, display the prompts to the user, then register user-provided images with `place --source <path> --target-id <id>` or `place --sources '{...}'`. Record every attempt with `image-asset`; `final_status: success` is only valid when the registered file exists and is non-empty. Failed or missing images must not be replaced by CSS gradients or SVG placeholders. Automatic backends such as `--api stub`, `--api dall-e-3`, `--api flux`, and `--api hf` remain available only when explicitly chosen or for testing.

7. Route generation by `output_format` in the confirmed brief:
   - `html-revealjs`: write pakco-compatible HTML directly to `Decks/<task-slug>/v1/final.html`; do NOT call Presentations plugin.
   - `pptx`: verify Codex Presentations / `artifact-tool presentation-jsx` through active plugin or bundled runtime, run the runtime check, then export the net-new PPTX with `build_artifact_deck.mjs` to `Decks/<task-slug>/v1/final.pptx`. If unavailable, stop and report the missing runtime.
   - `both`: verify Codex Presentations / `artifact-tool presentation-jsx` through active plugin or bundled runtime, export PPTX with `build_artifact_deck.mjs`, then write pakco-compatible HTML directly to `v1/final.html`. If Presentations runtime is unavailable, stop before generating either output unless the user explicitly changes output format.

If `image_generation_mode` is `post-v1-slot-review` or `hybrid`, after v1 exists run:

```bash
python3 scripts/presentation_director.py serve-wait \
  --task "<short task slug>" \
  --open-page image-placement \
  --for images-placement
```

Then generate v2 from `image-placement-request.json`: PPTX uses targeted edit and re-rendered `v2/contact-sheet.png`; HTML-only regenerates `v2/final.html`; `both` uses PPTX as the primary placement review and regenerates matching HTML.

After the latest required version is generated, render Director pages and open the preview review page. Use the local Director server for click-to-submit behavior; opening `preview-review.html` directly is only a static preview. If the user keeps the current version, final selection is written by the preview gate. If the user chooses style changes, wait for `revision.ready` from the style review gate, then use:

```bash
python3 scripts/presentation_director.py render --task "<short task slug>"
python3 scripts/presentation_director.py guard --task "<short task slug>"
python3 scripts/presentation_director.py serve-wait \
  --task "<short task slug>" \
  --open-page preview-review \
  --for preview-review
```

If guard exits 2, do not open preview-review. Fix the HTML and re-run guard first.
After preview-review is submitted, read `preview-review.json`. If `preview_action` is `style-review`, open the style review gate and then request the revision prompt:

```bash
python3 scripts/presentation_director.py serve-wait \
  --task "<short task slug>" \
  --open-page style-review \
  --for revision
python3 scripts/presentation_director.py prompt --task "<short task slug>" --kind revision
```

After revised versions are generated, render and open the comparison page:

```bash
python3 scripts/presentation_director.py render --task "<short task slug>" --open-page compare
python3 scripts/presentation_director.py wait --task "<short task slug>" --for final-selection
```

Do not bypass this flow in an interactive Codex session unless the user explicitly says to skip it. A casual "continue" after providing source material is not enough to replace the brief confirmation click.

## Claude / Offline / HTML Execution Steps

The steps below are for non-Codex environments without Codex Presentations, for Claude/offline PPTX fallback, or for HTML deck output. For Codex `pptx` mode, do not run the full deck.md/design-lock workflow before v1 unless the user explicitly asks for it.

### Claude Step 1 — Classify the Input

| Input Type | Key Questions | Reference |
|------------|---------------|-----------|
| Article / book / knowledge doc | What is the central thesis? Who is the audience? | `references/source-to-deck.md` |
| Engineering project | What problem does it solve? Who are the stakeholders? | `references/engineering-project-deck.md` |
| Topic only | What outcome does the user need — pitch, brief, report? | Proceed to slide planner directly |

### Claude Step 2 — Run the Slide Planner

Read `references/slide-planner.md` for the full planner protocol.

Produce `slide-plan.md` containing:
- `audience`, `goal`, `content_language`, `output_constraints`, `thesis`, `arc`, `slide-count`
- Per-slide: `claim`, `proof-object`, `layout-family`, `source`, `missing`
- `appendix-plan`: what moves to notes or appendix, not the main deck

**Confirmation behavior — HARD STOP in interactive sessions:**

In an interactive session (human is present):
1. Present the slide plan as a readable list: slide number, title, one-line claim, layout intent
2. Ask explicitly: "这个大纲符合你的想法吗？有需要调整的幻灯片顺序、数量或重点吗？确认后我继续下一步。"
3. **STOP. Do not write deck.md, do not run ui-ux-pro-max, do not call any tool until the user replies.**
4. Only proceed to Step 3 after the user sends an explicit confirmation (e.g., "好的"、"继续"、"looks good", or change instructions).

Rationale: skipping this confirmation forces an expensive full-rerun if the structure is wrong. The cost of pausing here is near zero.

In a batch / automated / non-interactive context: write `slide-plan.md`, log "slide-plan.md written — proceeding to deck.md", then continue without waiting.

For net-new PPTX work, this slide-plan confirmation does not replace the Director confirmation gate when the Director helper is available. Run the helper and guard before generation, or use the equivalent chat/static confirmation only when the helper cannot be used.

### Claude Step 3 — Write deck.md

Read `references/source-to-deck.md` or `references/engineering-project-deck.md` for structure.

Rules:
- Every slide needs a `Claim` — a conclusion sentence, not a topic label
- Every slide needs one primary `Proof object` (chart, diagram, table, big number, case)
- Every number and logo needs a `Source`; write "missing" if unverifiable — never invent data

### Claude Step 4 — 颜色层 (Color Layer)

**Sub-step 4a — 行业情报查询（Industry Intelligence）**

Extract the deck topic and industry from `deck.md` thesis. Then call `search.py` with the topic:

```bash
# Path: skills/ui-ux-pro-max/scripts/search.py (or ~/.claude/skills/ui-ux-pro-max/scripts/search.py)
python3 skills/ui-ux-pro-max/scripts/search.py "[deck topic / product type]" --domain color --json --max-results 3
```

Map each result to palette format:
- `bg` ← result `Background`
- `text` ← result `Foreground`
- `accent` ← result `Primary`
- `muted` ← result `Muted Foreground`
- `mood` ← result `Notes` (trimmed to key phrase)
- `font_zh` ← assign based on mood: formal/academic→"思源宋体", tech/modern→"思源黑体"
- `font_en` ← assign based on mood: editorial→"IBM Plex Sans", modern→"Inter", elegant→"Plus Jakarta Sans"
- `lock` ← assign based on color vibe: dark bg→"linear-dark", warm/paper→"editorial", cool academic→"academic", neutral→"swiss-klein-blue" or "notion-warm"
- `id` ← generate a short slug like "industry-saas-indigo"

**Note:** Filter out search results with very dark backgrounds (`Background` starts with `#0` or `#1` and very low luminance) unless the user explicitly wants dark mode — PPT slides read best on light backgrounds in daylit rooms.

**Sub-step 4b — Write palettes.json**

Write `assets/palettes.json` using the **object format** (supports industry context display in preview):

```json
{
  "deck_industry": "[product type from search results, e.g. SaaS / Finance / Healthcare]",
  "palettes": [
    {
      "id": "industry-saas-blue",
      "name": "风格名称",
      "zh": "中文风格名",
      "category": "tech",
      "bg": "#hex",
      "text": "#hex",
      "accent": "#hex",
      "muted": "#hex",
      "font_zh": "思源黑体",
      "font_en": "Inter",
      "mood": "情绪描述",
      "lock": "recommended-lock-id"
    }
  ]
}
```

**Sub-step 4c — HTML Preview — HARD STOP:**

Run the preview script to generate the interactive palette selector:

```bash
python3 scripts/preview_palette.py
# Generates assets/palette-preview.html
# Shows: Claude's industry-matched recommendations + full 50-palette browsable library
```

Open `assets/palette-preview.html` automatically. The user should click a palette in the HTML UI; do not ask them to copy/paste the selection back into chat. If the legacy preview script cannot emit a status file, replace it with an equivalent Director-style local endpoint before using it as a primary flow.

If `scripts/preview_palette.py` is not available (outside MD2PPT repo), fall back to terminal text with `████` Unicode blocks — but always note the limitation.

**Consultation is iterative:**
- User can say "我想要更暖的色调" / "强调色换成橙色" / "更深的背景"
- Update `palettes.json` and re-run the script each iteration — the browser auto-refreshes on reload
- User can also ask for a mood board image (DALL-E 3) to preview the overall visual feel

**STOP. Do not proceed to Step 5 until the user explicitly confirms a palette through the HTML UI or an equivalent file-signal mechanism.**

The output of Step 4 is:
- Confirmed color palette (hex values, semantic roles)
- Confirmed typography direction (Chinese + Latin fonts)
- Confirmed mood and style
- Suggested design-lock for the structural layer

### Claude Step 5 — 结构层 (Structure Layer)

颜色层（Step 4）已确认。结构层提供设计的骨架：字体层级、网格比例、图表标注规则、禁用效果。

**必须先运行预览脚本，绝不跳过此步骤直接展示文字表格。**

脚本已打包在 skill 目录中。按以下顺序查找并运行：

```bash
# 优先在当前项目目录查找
python3 scripts/preview_locks.py

# 若当前目录没有，用 skill 内置版本（全局安装路径）
python3 ~/.claude/skills/deck-builder/scripts/preview_locks.py
```

运行后自动打开 `assets/locks-preview.html`。用户只应在 HTML UI 中点击确认结构层；不要要求用户把选择粘贴回聊天。如果旧预览脚本不能写入状态文件，应先补齐等价的本地端点/文件信号，再作为主流程使用。

同时给出文字推荐（作为辅助说明，不替代 HTML 预览）：

| Lock ID | 布局语法 | 适合 | 不适合 |
|---------|----------|------|--------|
| `swiss-klein-blue` | 边栏分割 · 严格栅格 · 精密层级 | 商业计划、投资人、路线图 | 文化类、叙事类 |
| `linear-dark` | 卡片边框 · 高密度 · 代码块结构 | SaaS、技术平台、工程演示 | 教学类、文化类 |
| `academic` | 双色块 · 数据表格 · 权威分割线 | 技术方案、数据报告、答辩 | 温暖叙事类 |
| `editorial` | 引言竖栏 · 长文段落 · 纵向叙事 | 路演、课程、观点类 | 纯工程类、数据密集 |
| `notion-warm` | 卡片列表 · 扁平层级 · 亲和结构 | 内部汇报、文化类、轻量演示 | 投资人演示、高强度外部 |

推荐最匹配 Step 4 配色情绪的选项，说明理由。

**STOP. 等用户从预览页面点击确认，并通过状态文件或等价机制恢复；不得要求聊天粘贴，也不得自行决定。**

两层都确认之后，才写入 `deck.md` 的 Design Contract：

```markdown
## Design Contract
- Structure lock: design-locks/<lock>.md
- Color layer (from Step 4):
  - background: #[hex]
  - primary text: #[hex]
  - accent: #[hex]
  - muted: #[hex]
  - _(只列与 lock 默认值不同的颜色)_
- Typography: [中文字体] + [西文字体]（来自 Step 4 确认）
- Must keep: lock 的字体层级、网格语法、图表标注规则
- May adapt: layout families to match proof objects
- Must avoid: gradients, generic card grids, invented logos, unsupported metrics
```

**这是真正的 lock 时刻。** 颜色层 + 结构层都由用户明确选定后，生成过程不得引入任何未在 Design Contract 中声明的颜色、字体或效果。

### Claude Step 5.5 — AI Background Image (Optional) — HARD STOP

**Trigger this step only after Step 5 structure lock is confirmed.**

**HARD STOP — present this choice in the HTML UI and wait for the click/file signal before proceeding to Step 6:**

> "需要为封面和章节分隔页生成 AI 背景图吗？现有的纯色方案够用就可以跳过。"

**Do NOT proceed to Step 6 until the user clicks a choice or an equivalent file signal is present.** This step is skippable, but you must ask.

**If user says skip / no / 跳过:** proceed directly to Step 6.

**If user says yes:** read `docs/ai-background-image.md` for the full protocol, then:
1. **Auto-construct the image prompt** — do NOT pass the user's raw instruction to the API. Build a rich DALL-E 3 prompt by combining:
   - Primary color family from the Design Contract (e.g. "deep indigo blue tones, #0a1f3d")
   - Mood/style from the confirmed structure lock (e.g. "scholarly, cold-tech aesthetic")
   - Deck theme/topic extracted from `deck.md` thesis (e.g. "AI infrastructure growth in enterprise")
   - Fixed technical constraints: "abstract texture, no people, no faces, no text, suitable for 16:9 presentation slide background, high contrast areas reserved for title placement, 1920×1080"
   - Overlay note: "semi-transparent overlay will be applied — background should be rich in texture but not distracting"
2. Call DALL-E 3 via OpenAI images API (or Flux/SD if user specifies) — only for cover and section-divider slides
3. Save generated images to `assets/` in the current project folder
4. Note image paths — they will be referenced in Step 6 generation prompts
5. Add a 遮罩 (semi-transparent overlay, 40–60% opacity, using the lock's background color) instruction to the generation prompt to ensure text readability

Hard constraints (from `docs/ai-background-image.md`):
- Abstract texture / geometry only — no scenes, people, faces, text
- Image must use the lock's primary color family
- Only cover + section-divider slides get background images; content slides do not
- Always build the full prompt internally — never pass a one-line user instruction directly to the image API

### Claude Step 6 — Generate

Read `references/prompt-templates.md` for ready-to-use prompts.

- In Codex: use Template A (Presentations capability; active plugin or bundled runtime)
- In Claude Code: use Template B (pptxgenjs fallback)
- HTML deck (either environment): write pakco-compatible HTML directly using the spec above

Before generating a net-new deck in a workspace that has Presentation Director, run:

```bash
python3 scripts/presentation_director.py --base-dir "." guard --task "<task-slug>"
```

If that guard fails, open the Director confirmation page through `serve-wait` and continue automatically after the user clicks in the HTML UI. Do not ask the user to reply in chat. Do not generate PPTX/HTML by treating a conversational "continue" as a substitute for the confirmation gate unless the user explicitly asks to skip the gate or generate directly.

For new confirmed briefs with `image_generation_mode`, the guard also enforces Image Style Gate completion and, once a v1 preview artifact exists, Image Placement Gate completion for `post-v1-slot-review` and `hybrid`. Older briefs without `image_generation_mode` skip image gates for compatibility.

The guard also runs **structural HTML QA** on `v1/final.html` and auto-fails on two patterns that recurrently cause the staircase layout bug:
1. `section { position:... }` in CSS — Reveal.js manages section positioning; any override breaks slide stacking.
2. Unapproved `.stagger` — `.stagger` is forbidden by default and allowed only as `.stagger stagger-ok` on decorative, single-row, uniform horizontal card/tile/metric grids.

If the guard fails due to structural QA, fix the HTML and re-run the guard before opening preview-review.

### macOS PowerPoint File Access Dialogs

Prefer render/export paths that do not use Microsoft PowerPoint UI automation, such as Codex Presentations artifact-tool rendering or LibreOffice/headless renderers. If a PowerPoint-based render is unavoidable on macOS, start the watcher before the render command:

```bash
scripts/macos/powerpoint-grant-access-watcher.sh 180 &
```

The watcher clicks common Microsoft PowerPoint `Grant File Access`, `Select`, and `Grant Access` dialogs. macOS may still require one-time Accessibility permission for the terminal/Codex host process; that OS-level permission cannot be silently bypassed by project code.

### Claude Step 7 — Render QA

Full gate definitions inside Presentation Director: `docs/quality-gates.md`. If that file is unavailable, apply this minimum checklist before declaring done:

- [ ] Per-slide preview images rendered (or browser screenshot for HTML)
- [ ] Contact sheet generated (PPTX) or browser full-screen test completed (HTML)
- [ ] Layout JSON reviewed (overflow, font issues, spacing)
- [ ] Safe-area check completed: essential content stays inside the declared safe area; backgrounds/chrome only may sit outside it
- [ ] No text overlaps after rendering: title/subtitle/body/footer/page number/labels/connectors are visually separated
- [ ] Long titles are safe after wrapping: wrapped titles do not cover subtitles, captions, or the body area
- [ ] At least one "find issue → fix → re-render" cycle completed
- [ ] Final output confirmed at `Decks/<task-slug>/final/<task-slug>.pptx` or `Decks/<task-slug>/final/<task-slug>.html`
- [ ] For PPTX-only output, view-only HTML companion exists at `Decks/<task-slug>/final/<task-slug>-companion.html`
- [ ] Completion report includes: output path, render evidence, remaining risks

---

## Out of Scope

- Marp `.md` writing → handle directly without this pipeline
- Google Slides native creation → generate PPTX first, import via Google Drive
- reveal.js from scratch (no source material) → handle directly
- Fixing individual slides in an existing deck → do it directly
