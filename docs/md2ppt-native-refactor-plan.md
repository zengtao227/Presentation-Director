> **STATUS: RESEARCH NOTE — NOT APPROVED FOR IMPLEMENTATION**
> Reviewed by Opus + Codex (2026-05-20). Core analysis is useful; proposed implementation (DeckReview/DeckDraft/DeckSpec/Design Languages rename) was rejected as premature and over-engineered for a personal tool. The only approved action is Phase 6 (quality gates unification), tracked in `docs/quality-gates.md`. All other phases are deferred until real usage evidence warrants them.

---

# MD2PPT Native Refactor Plan

> Purpose: turn MD2PPT from a workflow that integrates several deck-generation ideas into a coherent product with its own core model, user-facing flow, design language, and quality gates.

## First-Principles Analysis

### 1. Problem Essence

MD2PPT currently has strong ingredients:

- slide planning from source material
- `ui-ux-pro-max` design intelligence
- Open Design-inspired visual profiles
- Codex Presentations as the primary editable PPTX renderer
- HTML deck routes for online sharing
- render QA and contact sheet expectations

The issue is not lack of capability. The root problem is that these capabilities still read like a set of integrated external workflows. Users and agents can see the seams:

- `deck.md` is treated as both a human review artifact and a machine source file.
- PPTX and HTML output paths share intent, but not a clearly defined internal intermediate model.
- Design locks still feel like imported style contracts rather than MD2PPT-native design languages.
- Quality checks are mentioned in several places, but not unified as one MD2PPT quality model.
- External projects are visible too high in the user-facing workflow.

The result is a useful workflow, but not yet a distinctive product.

### 2. Existing Mechanisms Review

Existing pieces should be reused, not discarded:

| Existing Mechanism | Keep? | Reason |
|--------------------|-------|--------|
| `deck-builder` skill | Yes | It already encodes the end-to-end orchestration model. |
| `ui-ux-pro-max` | Yes | It provides strong design intelligence and can remain an internal advisor. |
| `design-locks/` | Partially | The content is useful, but should be reframed as MD2PPT-native design languages. |
| `deck.md` | Downgrade | Useful for Git/export/debug, but not ideal as the primary human approval surface. |
| Codex Presentations | Yes | Best current primary renderer for editable PPTX. |
| HTML skills/projects | Yes, as adapters | Useful output engines, but should not define MD2PPT's product identity. |
| render QA / contact sheet | Yes | Should become part of a unified quality gate model. |

### 3. Constraints

Hard constraints:

- Editable `.pptx` remains the primary output.
- HTML deck remains a secondary output for online sharing and presenter mode.
- The user-facing workflow must not require people to manually maintain both HTML and Markdown versions of the same deck plan.
- The planner must remain claim-first: every slide needs a claim, proof object, source, and missing-info policy.
- External projects may inspire implementation, but MD2PPT must own the product vocabulary and user-facing model.
- Provenance and license boundaries must be kept explicit where copied assets, templates, or data remain.

Soft constraints:

- `deck.md` can remain as a sidecar export for Git diff and agent compatibility.
- `DeckSpec` can start as JSON embedded in `deck-review.html`, then later become a standalone schema.
- Design languages can be introduced gradually without immediately deleting existing `design-locks/`.
- Renderer adapters can remain prompt-based before becoming fully automated scripts.

### 4.方案评估

#### Option A: Keep the Current Workflow and Improve Documentation

Pros:

- Lowest cost.
- No risk of breaking existing skill usage.
- Enough for personal workflow.

Cons:

- Does not solve the product identity issue.
- Keeps `deck.md` as a visible human approval artifact.
- External project seams remain visible.
- PPTX and HTML paths remain loosely coordinated.

#### Option B: Refactor Around MD2PPT-Native Product Core

Pros:

- Creates a distinct product model.
- Reduces duplication between human review and machine generation.
- Makes PPTX and HTML outputs share one approved planning source.
- Allows external ideas to be absorbed as adapters and references instead of exposed as product identity.

Cons:

- Requires careful migration.
- Requires new docs and eventually schema/tooling.
- Needs QA to ensure current workflows still work.

Recommendation: choose Option B, but implement it in documentation-first phases before changing renderer behavior.

### 5. Minimality Check

The smallest useful refactor is not code. It is a terminology and artifact refactor:

1. Define `deck-review.html` as the human approval artifact.
2. Define embedded `DeckDraft` JSON inside `deck-review.html` as the machine-readable approval data.
3. Define `DeckSpec` as the compiled, approved intermediate format.
4. Reframe existing design locks as future MD2PPT design languages.
5. Move external project names out of the normal user-facing workflow and into adapter/reference docs.

Code should come after the model is accepted.

### 6. Side Effects

Affected modules and documents:

- `CONTEXT.md`
- `docs/pptx-master-workflow.md`
- `skills/deck-builder/SKILL.md`
- `skills/deck-builder/references/*`
- `design-locks/`
- future `design-languages/`
- future schema files for `DeckDraft` / `DeckSpec`
- prompt templates for Codex Presentations and HTML renderers

Risk:

- If introduced too aggressively, agents may confuse `deck-review.html` with final HTML deck output.
- If `DeckSpec` is overdesigned too early, the project may become heavier than needed.
- If existing `deck.md` support is removed too early, compatibility with current workflows may suffer.

Mitigation:

- Keep `deck.md` as optional sidecar export during transition.
- Use explicit naming: `deck-review.html` is for approval; `PPTX/<task-slug>/final/*.html` is final presentation output.
- Start with docs and examples before writing a compiler.

## Target Product Positioning

MD2PPT should not be positioned as "Markdown to PPT".

Recommended positioning:

> MD2PPT is a claim-first presentation compiler. It turns source materials such as articles, books, knowledge drafts, and engineering projects into approved, design-constrained, QA-verified presentation outputs.

The distinctive product idea:

```text
Source Material
  -> Slide Planner
  -> DeckReview
  -> DeckSpec
  -> MD2PPT Design Language
  -> Renderer Adapter
  -> Quality Gates
  -> PPTX / HTML
```

External projects become inputs to the product's internal thinking, not the product surface.

## Proposed Product Core

### 1. DeckReview

`DeckReview` is the human approval layer.

Primary artifact:

```text
deck-review.html
```

It is not the final HTML deck. It is a readable storyboard for approval.

It should show:

- audience
- goal
- thesis
- narrative arc
- slide count
- slide-by-slide storyboard
- claim per slide
- proof object per slide
- layout intent
- source status
- missing information
- appendix candidates
- approval checklist

It should also contain a hidden machine-readable JSON block:

```html
<script type="application/json" id="md2ppt-deckdraft">
{
  "version": "0.1",
  "audience": "...",
  "goal": "...",
  "thesis": "...",
  "slides": []
}
</script>
```

The visible HTML is for humans. The embedded JSON is for agents and compilers.

### 2. DeckDraft

`DeckDraft` is the structured JSON embedded in `deck-review.html`.

It represents the planned deck before final approval.

It should include:

- `version`
- `title`
- `audience`
- `goal`
- `thesis`
- `arc`
- `slides[]`
- `appendix[]`
- `sources[]`
- `missing_info[]`
- `approval_status`

Each slide should include:

- `id`
- `role`
- `claim`
- `proof_object`
- `layout_intent`
- `evidence`
- `source`
- `missing`
- `notes`

### 3. DeckSpec

`DeckSpec` is the approved machine intermediate format.

It should be compiled from approved `DeckDraft`, not handwritten by users.

It adds renderer-facing precision:

- normalized slide roles
- canonical layout intent
- proof object type
- evidence binding
- visual priority
- data requirements
- renderer hints
- QA expectations

`DeckSpec` can start as generated JSON/YAML, but the user does not need to edit it directly.

### 4. MD2PPT Design Languages

Current `design-locks/` should evolve into MD2PPT-owned design languages.

Goal:

- keep useful design ideas
- rewrite product-facing vocabulary
- avoid looking like a direct wrapper around another project
- make every language map cleanly to PPTX and HTML renderers

Possible first-party language names:

| Language | Best For | Character |
|----------|----------|-----------|
| Signal | engineering reports, system reviews, metrics decks | precise, operational, data-forward |
| Atlas | research, knowledge synthesis, book/article decks | structured, editorial, explanatory |
| Terminal | developer tools, infra, architecture, code-heavy projects | technical, compact, high-contrast |
| Studio | product launches, demos, startup pitch | polished, energetic, visual-led |
| Monograph | essays, strategy memos, thought leadership | restrained, typographic, publication-like |

The exact names can change. The key is that they become MD2PPT's own product language.

### 5. Renderer Adapters

Renderer adapters should consume `DeckSpec` and a selected design language.

Primary adapters:

| Adapter | Output | Role |
|---------|--------|------|
| PPTX Renderer | `.pptx` | Primary editable PowerPoint output via Codex Presentations or future local renderer. |
| HTML Renderer | `.html` | Secondary online sharing / presenter mode output. |
| Markdown Export | `.md` | Optional sidecar for Git diff, audit, or agent compatibility. |

External tools should be described as implementation references or backend options, not as the main user-facing workflow.

### 6. Quality Gates

Quality should become one MD2PPT-native layer, not scattered checks.

Recommended gates:

#### Content Gate

- Every slide has one clear claim.
- Every slide has one primary proof object.
- Every number, quote, screenshot, and logo has a source or is marked missing.
- No invented metrics.
- Appendix material does not pollute the main narrative.

#### Design Gate

- Selected design language is followed.
- Palette, typography, spacing, and chart grammar are consistent.
- Layout intent matches proof object type.
- Forbidden effects or generic templates are not used.

#### Render Gate

- PPTX render preview exists.
- Contact sheet exists.
- Text overflow checked.
- Layout JSON or equivalent inspection completed.
- At least one issue-fix-rerender cycle happened.

#### Output Gate

- Final output exists in `PPTX/<task-slug>/final/`.
- PPTX is editable where expected.
- HTML output is browser-tested when selected.
- Sidecar artifacts are saved for traceability.

## Target User Workflow

The future user-facing workflow should be:

```text
1. User provides source material
   article / book / knowledge draft / engineering project / topic

2. Slide Planner analyzes the source
   audience, goal, thesis, narrative arc, slide candidates, proof objects

3. MD2PPT generates deck-review.html
   human-readable storyboard + embedded DeckDraft JSON

4. Human reviews and revises deck-review.html
   approve, reject, reorder, merge, split, or request changes

5. MD2PPT compiles approved DeckDraft into DeckSpec
   machine-readable intermediate format

6. MD2PPT selects or asks for a Design Language
   Signal / Atlas / Terminal / Studio / Monograph, etc.

7. Renderer Adapter generates output
   PPTX primary, HTML secondary, Markdown optional sidecar

8. Quality Gates run
   content gate, design gate, render gate, output gate

9. Final files are delivered
   PPTX/<task-slug>/final/<task-slug>.pptx or PPTX/<task-slug>/final/<task-slug>.html
```

Important distinction:

- `deck-review.html` = review and approval artifact.
- `PPTX/<task-slug>/final/*.html` = final HTML presentation.
- `deck.md` = optional sidecar export, not a required user-facing step.
- `DeckSpec` = machine intermediate format, not a user editing surface.

## Proposed Repository Refactor

### Phase 1: Terminology and Documentation

Goal: align the project around the new product model without breaking anything.

Work:

- Update `CONTEXT.md` with new terms:
  - `DeckReview`
  - `DeckDraft`
  - `DeckSpec`
  - `Design Language`
  - `Renderer Adapter`
  - `Quality Gates`
- Update `docs/pptx-master-workflow.md` so `deck-review.html` becomes the human approval artifact.
- Update `skills/deck-builder/SKILL.md` so Step 3 becomes "Generate DeckReview", not "Write deck.md" as the primary user-facing artifact.
- Keep `deck.md` as optional sidecar export.
- Add a short glossary to reduce confusion between approval HTML and final HTML deck.

Done when:

- User-facing docs describe one coherent workflow.
- No doc implies humans must manually maintain both `deck-review.html` and `deck.md`.

### Phase 2: DeckReview Specification

Goal: define the review artifact before building tooling.

Work:

- Add `docs/deck-review-spec.md`.
- Define required visible sections.
- Define embedded `DeckDraft` JSON shape.
- Define approval states.
- Define editing rules:
  - visible content and embedded JSON must stay synchronized
  - agent should update JSON first, then regenerate visible HTML
  - human manual edits should be treated as review comments unless JSON is updated
- Add one example `examples/deck-review.example.html`.

Done when:

- Agents can produce a consistent review HTML file.
- Opus/Codex/Claude can inspect the embedded JSON without guessing from page text.

### Phase 3: DeckSpec Schema

Goal: create the internal machine format shared by PPTX and HTML renderers.

Work:

- Add `schemas/deckspec.schema.json`.
- Add `examples/deckspec.example.json`.
- Define slide roles, proof object types, layout intents, source binding, and QA expectations.
- Add a conversion rule:

```text
approved DeckDraft -> DeckSpec
```

Do not build a full compiler yet unless the schema is reviewed.

Done when:

- PPTX and HTML prompts can both consume the same `DeckSpec`.
- There is a clear difference between draft/review data and renderer-ready data.

### Phase 4: Design Language Refactor

Goal: transform design locks into MD2PPT-native product assets.

Work:

- Create `design-languages/`.
- Draft 3 initial MD2PPT-native languages:
  - `signal`
  - `atlas`
  - `terminal`
- Each language should define:
  - audience fit
  - narrative fit
  - palette tokens
  - typography tokens
  - layout grammar
  - chart grammar
  - forbidden patterns
  - PPTX notes
  - HTML notes
- Keep old `design-locks/` during migration.
- Add provenance notes where material is directly adapted from external sources.

Done when:

- New docs can choose MD2PPT design languages without exposing external project names.
- Existing design locks still work as fallback.

### Phase 5: Renderer Adapter Prompts

Goal: make output routes consume MD2PPT-native artifacts.

Work:

- Update Codex Presentations prompt template:

```text
Input: DeckSpec + Design Language
Output: editable PPTX + contact sheet + QA notes
```

- Update HTML prompt template:

```text
Input: DeckSpec + Design Language
Output: final HTML deck + browser QA notes
```

- Define Markdown export as optional:

```text
Input: DeckSpec
Output: deck.md sidecar
```

Done when:

- PPTX and HTML outputs share the same planning model.
- `deck.md` is no longer a mandatory middle step.

### Phase 6: Quality Gate Unification

Goal: turn QA from scattered instructions into one MD2PPT-native checklist.

Work:

- Add `docs/quality-gates.md`.
- Define content/design/render/output gates.
- Add minimum evidence requirements for each output type.
- Add examples of unacceptable outputs:
  - claim-less slide
  - text dump slide
  - source-less metric
  - generic card grid
  - screenshot-only editable PPTX where shapes should be editable
  - final HTML confused with review HTML

Done when:

- Every generation path must pass the same quality model.

### Phase 7: Optional Tooling

Goal: automate only after the model is stable.

Potential tools:

- `scripts/extract_deckdraft.py`
  - reads `deck-review.html`
  - extracts `#md2ppt-deckdraft`
  - validates JSON
- `scripts/compile_deckspec.py`
  - converts approved DeckDraft to DeckSpec
- `scripts/validate_deckspec.py`
  - validates against JSON Schema
- `scripts/export_deck_md.py`
  - optional Markdown sidecar export
- `scripts/check_quality_gates.py`
  - early static checks for claim/proof/source completeness

Done when:

- The workflow can run semi-automatically.
- Tooling follows accepted docs instead of inventing hidden behavior.

## What Should Not Be Done Yet

- Do not delete `deck.md` support immediately.
- Do not rename all folders before the new model is accepted.
- Do not expose external engine names as primary user-facing choices.
- Do not build a complex compiler before `DeckDraft` and `DeckSpec` are reviewed.
- Do not turn `deck-review.html` into the final presentation deck.
- Do not parse visual HTML text heuristically when embedded JSON can provide structure.

## Review Questions for Opus

1. Is `deck-review.html` as the human approval artifact a better primary surface than `deck.md`?
2. Is embedded `DeckDraft` JSON inside review HTML robust enough, or should the JSON always be a sidecar file?
3. Is the distinction between `DeckDraft` and `DeckSpec` necessary, or can they be merged in the first version?
4. Are `Design Languages` the right abstraction over current `design-locks/`?
5. Should `deck.md` remain optional forever, or only during migration?
6. Are the proposed quality gates sufficient for both PPTX and HTML outputs?
7. Which phase should be implemented first if only one sprint is available?

## Recommended Next Step

Ask Opus to review this plan before implementation.

If approved, start with Phase 1 and Phase 2 only:

```text
Phase 1: terminology and docs
Phase 2: DeckReview spec and one example
```

Do not implement schema compilers or renderer changes until the review artifact model is accepted.
