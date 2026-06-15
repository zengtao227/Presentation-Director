# Presentation Director Design Rules

This document is the project-level design constitution for Presentation Director. It is a soft constraint layer: it defines priorities, boundaries, and QA expectations, but it does not replace a user-confirmed task brief or a task-level visual contract.

## 1. Priority Order

When design guidance conflicts, agents must resolve it in this order:

```text
User's explicit instruction
> Decks/<task-slug>/brief-confirmed.json
> Decks/<task-slug>/brief/composition-lock.md
> Decks/<task-slug>/brief/visual-contract.md
> Decks/<task-slug>/brief/form-lock.md
> Decks/<task-slug>/brief/content-lock.md
> this root DESIGN.md
> design-locks / ui-ux-pro-max / Claude Design or designer-skills advice
> agent aesthetic preference
```

Task-level decisions always beat global style advice. `brief-confirmed.json` is the machine execution contract; lock files are the human-readable source for content, form, and composition decisions. This root document should guide default behavior, not freeze every deck into one visual template.

## 2. Constraint Levels

- MUST: Non-negotiable execution rules.
- SHOULD: Strong defaults unless the task brief says otherwise.
- MAY: Optional inspiration or implementation latitude.
- AVOID: Patterns that commonly reduce deck quality.

## 3. Product Principles

- MUST preserve editable PPTX as the primary deliverable unless the user explicitly asks for HTML-only output.
- MUST treat source boundaries, research strategy, audience, goal, content language, and output constraints as design inputs.
- MUST separate UI language for Presentation Director pages from deck body language.
- SHOULD optimize for decision clarity and slide-level claims before visual flourish.
- SHOULD use visual design to clarify proof objects, not to decorate weak content.
- MAY use distinctive editorial, Swiss, academic, dark SaaS, or warm minimal styles when they fit the audience and room context.

## 4. Codex Presentations Boundary

Codex Presentations has its own design-system generation capability. Do not over-constrain it before the first draft.

- MUST provide confirmed intent, source boundary, research strategy, visual target, and QA requirements before generation.
- SHOULD give Codex Presentations room to choose the first-draft design system, contact-sheet rhythm, and slide composition.
- MAY pass a selected design-lock or visual-contract when the user explicitly chose a direction.
- AVOID locking exact per-slide layout, all colors, or all font sizes before v1 unless the user requests a strict template.

## 5. Claude Design Boundary

Claude Design / designer-skills are design support tools, not the PPT workflow owner.

- MUST keep new PPT work routed through deck-builder / Presentation Director.
- MUST NOT let design-flow, frontend-design, or design-tokens replace slide planning, brief confirmation, visual contract selection, PPTX generation, or render QA.
- SHOULD use design-brief, design-tokens, and design-review as inputs for Director HTML gates, HTML companions, or optional visual-contract refinement.
- MAY translate useful Claude Design output into `Decks/<task-slug>/brief/visual-contract.md`.

## 6. Visual Contract Rules

Every high-value deck should have a task-level visual contract after visual direction is confirmed.

- MUST save task-level contracts at `Decks/<task-slug>/brief/visual-contract.md`.
- SHOULD save task-level lock sources at `Decks/<task-slug>/brief/content-lock.md`, `Decks/<task-slug>/brief/form-lock.md`, and `Decks/<task-slug>/brief/composition-lock.md` when a deck needs explicit review or reusable provenance.
- MUST treat task-level `visual-contract.md` as higher priority than global `design-locks/*.md`.
- SHOULD include palette roles, typography, slide families, chart grammar, image policy, source-note treatment, and forbidden patterns.
- SHOULD compile outside visual sources into the task-level locks and visual contract before generation; generators should not pull fresh design decisions directly from Figma, design intelligence tools, or theme galleries after confirmation.
- SHOULD use softer constraints for Codex Presentations and stricter constraints for Claude / pptxgenjs fallback.
- AVOID mixing multiple design-locks unless the contract explicitly defines which parts are inherited from each.

## 7. PPT-Specific Design Defaults

- MUST use slide titles as claim statements whenever possible, not generic topic labels.
- MUST keep key text, charts, source notes, page numbers, and connectors free from overlap or clipping.
- MUST avoid invented data, fake logos, unsourced claims, and unverifiable metrics.
- SHOULD use one primary proof object per slide.
- SHOULD split overloaded content across multiple slides instead of shrinking text below readable size.
- SHOULD keep charts directly labeled when possible, reducing legend scanning.
- MAY create appendix or notes for detail that would damage the main slide's clarity.
- AVOID full-slide screenshots as the editable PPTX source of record unless the task explicitly requires an image-only reproduction.

## 8. Director UI And Artifact Boundaries

- MUST keep user-facing deck artifacts under `Decks/<task-slug>/`.
- MUST keep `.design/` for product/interface design artifacts only; do not mix it into PPTX deliverables.
- SHOULD use `.design/` for Presentation Director's own HTML gates, interface redesigns, and designer-skills outputs.
- SHOULD keep task files such as lock files, `brief-confirmed.json`, `visual-contract.md`, QA summaries, renders, and final outputs in the deck workspace.

## 9. QA Requirements

- MUST render slide previews and a contact sheet before declaring a PPTX complete.
- MUST run a no-overlap check at visual review time.
- MUST document QA evidence in the task workspace.
- SHOULD rerender affected slides after layout fixes.
- SHOULD verify that the final PPTX remains editable, especially text, charts, tables, and connectors.
- AVOID declaring success based only on package validity, XML inspection, or code generation logs.
