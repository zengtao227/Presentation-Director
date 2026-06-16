# Form Lock Spec

Form Lock freezes how a deck should look and feel before composition and generation. It is the Presentation Director layer that can use Figma, internal design locks, theme galleries, or design intelligence as inputs, but it must digest those sources into Director-owned form decisions.

Form Lock does not decide slide claims. It also does not generate HTML or PPTX. It decides which visual options are allowed and how they compile to runtime vocabulary.

## File Location

```text
Decks/<task-slug>/brief/form-lock.md
```

For legacy tasks, `PPTX/<task-slug>/brief/form-lock.md` may be read for compatibility, but new tasks should use `Decks/<task-slug>/`.

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

After Form Lock is compiled, generation must not fetch new visual decisions directly from Figma, design intelligence tools, or theme galleries.

## Versioning

Do not add ad hoc `version` fields to Form Lock or compiled config files. Add a schema version only after the protocol defines the field name, allowed values, compatibility behavior, and migration rule.

## Required Sections

### 1. Scope

- `task_slug`
- `output_format`: `pptx`, `html-revealjs`, or `both`
- Design source status: internal default, user-provided Figma URL, local export, screenshot/reference image, or another manually supplied source packet.
- Execution rule: clarify that sources are inputs only; generation reads compiled locks and config.

### 2. Content Context

Summarize only the content facts needed for form decisions:

- Deck type.
- Audience.
- Goal.
- Density.
- Room or reading context.
- Content boundary.

Do not duplicate the full Content Lock.

### 3. Design Strategy Filter

Define what internal design directions should be considered and which optional user-provided references should influence them.

Include:

- Desired tone.
- Density fit.
- Layout needs.
- Chart or diagram needs.
- Motion tolerance.
- Medium constraints: HTML-only, PPTX-only, or both.
- Rejection rules for options that cannot be safely realized.

### 4. Visual Source Packet

Record optional visual references in a table or short list. Do not invent Figma/community-template candidates when the user has not supplied a real file, URL, export, or screenshot.

Each candidate should include:

- Candidate or reference name.
- Source type: user-provided Figma file, local export, screenshot/reference image, existing deck, internal design lock, HTML deck theme, or manual source packet.
- Useful form elements: palette, typography, grid, layout family, component, chart grammar, image treatment, motion rhythm.
- Risk.
- License or provenance note when relevant.

External source names, URLs, frame ids, and screenshots are provenance. They are not execution dependencies unless explicitly converted into local assets or runtime tokens.

### 5. Selected Form Direction

Describe the selected direction in Director-owned terms:

- Name.
- Tone.
- Background strategy.
- Palette role intent.
- Typography intent.
- Component intent.
- Chart and diagram grammar.
- Image strategy.
- Motion policy.
- Forbidden patterns.

### 6. Runtime Mapping

For HTML output, map the selected form to the existing HTML runtime vocabulary:

```json
{
  "html_config": {
    "theme_key": "",
    "motion_level": "subtle",
    "motion_profile": "",
    "layout_families": [],
    "transition": "slide",
    "effects_runtime": "css-only"
  }
}
```

`theme_key` must correspond to an existing theme file unless a task explicitly adds a custom theme. `layout_families` should use existing layout template names or document a fallback before generation starts.

For PPTX output, Form Lock should stay softer unless the user asks for a strict template. PPTX constraints should prioritize editability, native text/shapes, readable charts, and render QA.

For `both`, declare one of:

- `pptx_parity`: HTML and PPTX stay visually close; avoid HTML-only effects that cannot survive PPTX.
- `html_enhanced`: HTML may use richer CSS/motion while PPTX keeps editable, conservative equivalents.

### 7. Layout Family Intent

Explain why each selected layout family fits the expected proof objects.

Each row should include:

- Layout family.
- Intended use.
- Content or proof object fit.
- Medium-specific fallback if needed.

### 8. Compile Notes

Record why the mapping is safe:

- Which runtime theme or token set is used.
- Which layout templates already exist.
- Whether token overrides are required.
- Which external source details were discarded.
- Which decisions must be carried into `composition-lock.md`.

### 9. Open Questions

Keep unresolved design questions visible. Open questions should not block generation unless they affect source rights, runtime availability, output format, or user-confirmed visual direction.

## Suggested Markdown Shape

````markdown
# Form Lock: <task slug>

## Scope
- output_format:
- external_source_status:
- execution_rule:

## Content Context
- deck_type:
- audience:
- goal:
- density:
- content_boundary:

## Design Strategy Filter
- retrieve:
- reject:

## Visual Source Packet
| Candidate | Source Type | Useful Form Elements | Risk | Provenance |
|---|---|---|---|---|

## Selected Form Direction
- name:
- tone:
- background_strategy:
- palette_role_intent:
- typography_intent:
- component_intent:
- chart_diagram_grammar:
- image_strategy:
- motion_policy:
- forbidden_patterns:

## Runtime Mapping
```json
{
  "html_config": {
    "theme_key": "",
    "motion_level": "subtle",
    "motion_profile": "",
    "layout_families": [],
    "transition": "slide",
    "effects_runtime": "css-only"
  }
}
```

## Layout Family Intent
| Layout Family | Use | Proof Object Fit | Fallback |
|---|---|---|---|

## Compile Notes
- 

## Open Questions
- 
````

## Validation Checklist

- The Form Lock does not redefine the deck's claims or source boundary.
- Every external visual source is either provenance-only or converted into Director-owned tokens, local assets, layout choices, or motion policy.
- HTML `theme_key` exists or the task explicitly includes a custom theme.
- HTML `layout_families` exist or have documented fallbacks.
- Motion policy is compatible with the selected output format.
- No generator step needs to read Figma, design intelligence output, or theme galleries directly after confirmation.
- No undefined schema or version fields are introduced.
