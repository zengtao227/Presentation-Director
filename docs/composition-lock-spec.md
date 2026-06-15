# Composition Lock Spec

Composition Lock freezes how confirmed content should be expressed through the selected form before generation starts. It is the bridge between `content-lock.md` and `form-lock.md`; it is not a generator prompt and should not contain raw implementation code.

## File Location

```text
Decks/<task-slug>/brief/composition-lock.md
```

For legacy tasks, `PPTX/<task-slug>/brief/composition-lock.md` may be read for compatibility, but new tasks should use `Decks/<task-slug>/`.

## Role In The Workflow

```text
content-lock.md
    ↓
form-lock.md
    ↓
composition-lock.md
    ↓
visual-contract.md + brief-confirmed.json
    ↓
generation
```

- `content-lock.md` answers what the deck says.
- `form-lock.md` answers how the deck should feel and what visual options are allowed.
- `composition-lock.md` answers which form each slide uses to express its content.
- `brief-confirmed.json` is the machine-readable compiled artifact used by guard and generation.

After `brief-confirmed.json` is confirmed, generation must not go back to Figma, design intelligence tools, or theme galleries to make new design decisions. Those sources should already be digested into the lock files and visual contract. If a compatibility path runs an Image Style Gate after confirmation, treat it as a late lock supplement: update the relevant lock files and `brief-confirmed.json` before generation starts.

## Required Sections

### 1. Deck Binding

- `task_slug`
- `output_format`: `pptx`, `html-revealjs`, or `both`
- `visual_policy`: `pptx_parity`, `html_enhanced`, or `pptx_only`
- `content_lock_ref`
- `form_lock_ref`
- `visual_contract_ref`

### 2. Global Composition Rules

- Slide count or duration target.
- Reading density target.
- Default safe area.
- Source-note and footer policy.
- Treatment for missing or unverifiable information.
- HTML-only affordances, if any: motion, gradient, presenter notes, browser-only layout behavior.
- PPTX compatibility limits, if any: editability, native shapes, conservative motion, image-only exceptions.

### 3. Slide Bindings

Each slide entry should include:

- `slide_id`: stable id such as `s01`.
- `title`: working title or claim title.
- `claim`: the single point the slide should advance.
- `proof_object`: type and source, such as chart, quote, screenshot, architecture map, comparison, timeline, table, or list.
- `layout_family`: selected from the project layout catalog or documented as a new candidate.
- `visual_treatment`: the specific form element from `form-lock.md`, such as editorial hero, dense comparison, blueprint diagram, warm quote, or data-first card grid.
- `assets`: required images, logos, charts, screenshots, icons, or generated-image targets.
- `notes`: presenter notes or supporting detail.
- `omissions`: facts, numbers, visuals, or claims that must not be invented.
- `medium_overrides`: optional `html` or `pptx` adjustments when `output_format` is `both`.

## Suggested Markdown Shape

```markdown
# Composition Lock: <task slug>

## Deck Binding
- output_format:
- visual_policy:
- content_lock_ref: brief/content-lock.md
- form_lock_ref: brief/form-lock.md
- visual_contract_ref: brief/visual-contract.md

## Global Composition Rules
- density:
- safe_area:
- source_notes:
- missing_info:
- html_affordances:
- pptx_limits:

## Slide Bindings

### s01 - <claim title>
- claim:
- proof_object:
  - type:
  - source:
- layout_family:
- visual_treatment:
- assets:
- notes:
- omissions:
- medium_overrides:
```

## Validation Checklist

- Every slide has exactly one primary claim.
- Every proof object has a source or an explicit omission note.
- Every layout family is available to the selected output path or has a documented fallback.
- HTML-only visual treatment is not forced onto PPTX unless `visual_policy` allows divergence.
- No Figma or external template reference remains as an execution dependency; references are provenance only.
- `brief-confirmed.json` contains the compiled execution fields needed by guard and generation.
