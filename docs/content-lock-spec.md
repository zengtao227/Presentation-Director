# Content Lock Spec

Content Lock freezes what a deck is allowed to say before form, composition, or generation begins. It is the Presentation Director layer that turns source material, audience, goal, and research boundaries into a slide-level claim plan.

Content Lock does not decide visual style. It also does not generate HTML or PPTX. It decides the content contract that later locks must preserve.

## File Location

```text
Decks/<task-slug>/brief/content-lock.md
```

For legacy tasks, `PPTX/<task-slug>/brief/content-lock.md` may be read for compatibility, but new tasks should use `Decks/<task-slug>/`.

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
- `form-lock.md` answers how the deck should feel and which visual choices are allowed.
- `composition-lock.md` binds slide content to selected layout and visual treatment.
- `visual-contract.md` and `brief-confirmed.json` carry the confirmed execution contract.

After Content Lock is compiled, later stages may refine wording for fit and clarity, but they must not add unsupported claims, invent metrics, change the source boundary, or change the deck's audience and goal without reopening confirmation.

## Versioning

Do not add ad hoc `version` fields to Content Lock files. Add a schema version only after the protocol defines the field name, allowed values, compatibility behavior, and migration rule.

## Required Sections

### 1. Scope

Define the task and output constraints:

- `task_slug`
- `output_format`: `pptx`, `html-revealjs`, or `both`
- Topic.
- Audience.
- Goal.
- Source boundary.
- Research strategy.
- Content language.
- Length or duration target.
- Known constraints: logo policy, image policy, confidentiality, required sources, or forbidden sources.

### 2. Source Boundary

Record what may and may not be used.

Include:

- Primary sources: files, folders, links, user text, existing deck, research packet, or project docs.
- Allowed external research behavior: online research, hybrid, or provided-only.
- Required verification behavior for numbers, quotes, logos, screenshots, and citations.
- Prohibited content: claims, metrics, logos, images, or competitive statements that must not be invented.

For provided-only work, missing facts must be marked as missing instead of filled in from memory or web search.

### 3. Audience And Goal

Define the communication target:

- Audience role and familiarity level.
- Decision, understanding, or action the deck should support.
- Tone requirements that affect content, such as executive concise, technical review, teaching, research defense, or narrative storytelling.
- Success condition for the deck.

### 4. Thesis

Write one sentence that the entire deck supports.

A good thesis is:

- Specific.
- Arguable or decision-relevant.
- Supported by the available source boundary.
- Short enough to guide slide selection.

### 5. Narrative Arc

List the deck's logical progression in 4 to 7 steps.

The arc should explain why the slide order exists. It should not be a list of visual layouts.

### 6. Slide Claims

Each planned slide should include:

- `slide_id`: stable id such as `s01`.
- `title`: working claim title.
- `claim`: the single point the slide advances.
- `proof_object`: the evidence type, such as chart, table, quote, screenshot, architecture map, comparison, timeline, checklist, or case.
- `source`: source file, user instruction, cited document, or explicit `missing`.
- `missing`: unsupported facts, unavailable data, or material that must be flagged before generation.

Every slide should have exactly one primary claim. If a slide needs two independent claims, split it.

### 7. Appendix Or Notes Plan

Record what should not enter the main deck:

- Detail that belongs in speaker notes.
- Appendix material.
- Optional examples.
- Caveats or limitations.
- Source traceability that would clutter a slide.

### 8. Omission Notes

Explicitly list what the deck must not invent or imply.

Common omission notes:

- Do not invent metrics.
- Do not invent customer logos.
- Do not cite inaccessible documents.
- Do not imply real Figma, MCP, API, or product integration unless it has actually been tested.
- Do not claim PPTX parity when only HTML was tested.

## Suggested Markdown Shape

```markdown
# Content Lock: <task slug>

## Scope
- output_format:
- topic:
- audience:
- goal:
- source_boundary:
- research_strategy:
- content_language:
- length_target:
- constraints:

## Source Boundary
- primary_sources:
- allowed_research:
- verification_rules:
- prohibited_content:

## Audience And Goal
- audience_context:
- desired_outcome:
- tone:
- success_condition:

## Thesis
<one sentence>

## Narrative Arc
1. 
2. 
3. 

## Slide Claims

### s01 - <claim title>
- claim:
- proof_object:
- source:
- missing:

## Appendix Or Notes Plan
- 

## Omission Notes
- 
```

## Validation Checklist

- Scope includes output format, audience, goal, source boundary, research strategy, language, and length or duration target.
- Thesis is specific and supported by allowed sources.
- Narrative arc explains the order of the deck.
- Every slide has exactly one primary claim.
- Every proof object has a source or an explicit missing note.
- Provided-only tasks do not use outside facts.
- Missing data is marked instead of invented.
- Later Form Lock decisions do not change the content boundary.
- Later Composition Lock decisions preserve slide claims and proof objects.
- `brief-confirmed.json` contains the compiled execution fields needed by guard and generation.
- No undefined schema or version fields are introduced.
