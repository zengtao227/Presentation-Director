# Agent Demand Gate: Figma Context For Presentation Director

## 1. Friction Point
- Current user friction: Presentation Director already has design intelligence, visual contracts, visual inspiration gates, and render QA, but design directions can still be hard to judge before generation and hard to keep visually consistent across repeated decks.
- Who experiences it: Solo maintainer creating or improving deck workflows and occasionally needing reusable visual language for PPTX, HTML gates, and pakco-compatible HTML decks.
- Why fixed rules or normal automation are insufficient: Fixed markdown rules can define palettes and typography, but they do not give an editable visual canvas for comparing slide families, spacing rhythm, component states, and brand assets before generation.
- Evidence source: Project `CONTEXT.md`, `DESIGN.md`, existing `design-locks/`, and Figma official documentation for libraries, variables, MCP context, Slides import/export, and pricing.

## 2. Quantified Gap
- Baseline metric: Unknown; current project does not appear to log time spent choosing visual direction, revising first-draft layouts, or fixing style inconsistency after render QA.
- Target metric: Reduce repeated visual-direction/revision work by at least 20% on high-value decks, or reduce avoidable style fixes after v1 by at least 30%.
- Failure or exit point: After 3 representative decks, Figma setup does not reduce style-review changes, does not improve reusable visual contracts, or adds more than 20 minutes of maintenance per deck.
- Acceptable error / misclassification rate: Figma-derived design specs may be advisory, but generated decks must still pass existing render QA and no-overlap checks; no false pass is acceptable for final delivery.
- Measurement window: 3 to 5 deck tasks or 2 weeks of normal use, whichever comes first.

## 3. Solution Choice
- Recommended path: non-agent-automation
- Why this path fits current data and change frequency: The clearest near-term value is deterministic transfer of Figma variables, components, frame references, and exported assets into `visual-contract.md`, pakco theme tokens, and Director UI references.
- Why the rejected paths are weaker: A fully autonomous design agent is premature because the project has no baseline metrics or labeled examples proving that autonomous visual decisions outperform the existing Director plus QA workflow. Fine-tuning is unnecessary. Prompt-chain use is acceptable for summarizing Figma frames, but should not own the workflow.
- Smallest useful prototype: Create one Figma file as a visual-contract sandbox, export or read its variables/components, translate them into one task-level `brief/visual-contract.md`, generate one deck, and compare v1/v2 QA effort against the current process.

## 4. Success Preview And Risk Plan
- Success standard: Figma improves visual preview and reuse without replacing Presentation Director intake, brief confirmation, Codex Presentations, pakco HTML runtime, or render QA.
- Pause / kill signal: The workflow becomes “design twice” in Figma and in code, paid features are required before value is proven, or generated PPTX editability/QA quality declines.
- Degraded fallback: Keep using existing `design-locks/`, `ui-ux-pro-max`, pakco themes, and task-level visual contracts without Figma.
- Owner and review cadence: Solo maintainer reviews after each experimental deck; decide after 3 decks whether to keep, narrow, or remove the Figma step.

---

# Agent Demand Gate: Figma Source Gate Automation

## 1. Friction Point
- Current user friction: A Figma-backed workflow should not require the user to leave the Director flow, manually hunt for URLs, collect screenshots, and paste them back before every deck.
- Who experiences it: The project owner and future users creating HTML decks through Presentation Director.
- Why fixed rules or normal automation are insufficient: A static “paste Figma URL” field interrupts the flow and makes Figma feel bolted on. The gate needs to offer topic-matched built-in source packets, optional URL/local-export paths, and a deterministic `figma-source-packet.json`.
- Evidence source: Current user feedback and the implemented Director gate flow.

## 2. Quantified Gap
- Baseline metric: Before this change, the real click flow had 0 Figma-specific page interactions and Visual Inspiration looked identical to the old flow.
- Target metric: Net-new HTML/both deck flows show one explicit Figma Source Gate before Visual Inspiration and write exactly one `figma-source-packet.json`.
- Failure or exit point: Visual Inspiration can appear without either a selected packet or an explicit skipped status.
- Acceptable error / misclassification rate: 0 false claims that a real Figma file was fetched; built-in packets must declare `source_status: built-in`.
- Measurement window: This implementation and the next teacher-facing HTML deck test.

## 3. Solution Choice
- Recommended path: workflow-orchestration.
- Why this path fits current data and change frequency: The behavior is deterministic page routing plus packet compilation; a full autonomous Figma agent is unnecessary until a real connector/API is available.
- Why the rejected paths are weaker: Pure prompt-chain would not guarantee click state or packet files. Fine-tuning is irrelevant. Requiring URL input by default preserves the interruption the user wants to remove.
- Smallest useful prototype: Insert `/figma-source` between `/intake` and `/visual-inspiration`, provide built-in Figma-assisted packets, and feed the selected packet into visual candidates.

## 4. Success Preview And Risk Plan
- Success standard: Intake redirects to Figma Source Gate, the user can choose built-in/search/URL/local/skip, the packet is written, and Visual Inspiration includes a Figma-assisted candidate when not skipped.
- Pause / kill signal: The page implies a real Figma file was read when only a built-in packet was used, or the flow can still bypass `figma-source-packet.json` silently.
- Degraded fallback: User selects “跳过 Figma”; the workflow continues with existing design-locks, ui-ux-pro-max, and pakco themes.
- Owner and review cadence: Review after the next teacher-facing deck run; decide whether to add real Figma API/MCP fetch after the click flow proves useful.

---

# Agent Demand Gate: Governed Presentation Plan V1 Freeze

## 1. Friction Point
- Current user friction: Presentation Director can collect and confirm deck intent, but it does not yet persist one complete, canonical, cross-repository Plan that BPS can validate without trusting mutable UI state or Provider behavior.
- Who experiences it: The maintainer integrating Presentation Director with Brand Production Studio and reviewers deciding whether a governed PPTX task is safe to route.
- Why fixed rules or normal automation are insufficient: Fixed rules are sufficient. This milestone needs a deterministic contract, compiler boundary, and CI; it does not need an autonomous Agent.
- Evidence source: BPS presentation conformance proof, Draft PR #12 adversarial review, and the current post-confirmation mutation of `brief-confirmed.json`.

## 2. Quantified Gap
- Baseline metric: 0 freeze-ready Plan schemas, 0 governed producer inputs, and 0 locked CI runs proving schema/golden parity in this repository.
- Target metric: 1 strict PPTX Plan V1 candidate whose six-slide golden fixture, exported JSON Schema, RFC 8785 digest, full test suite, Ruff, mypy, compileall, and package build all pass from a committed lock.
- Failure or exit point: Stop before Eligibility if any BPS-governed expression cannot be represented, mutable `brief-confirmed.json` is accepted as authority, canonical bytes drift silently, or CI is not reproducible from the lock.
- Acceptable error / misclassification rate: 0 unknown governed inputs accepted; 0 missing required content silently omitted; 0 Provider-specific implementation terms admitted into the capability vocabulary.
- Measurement window: Draft PR #12 freeze review and its next independent cross-repository review.

## 3. Solution Choice
- Recommended path: non-agent-automation.
- Why this path fits current data and change frequency: The required behavior is closed-schema validation, deterministic compilation, canonical serialization, and fail-closed policy checks.
- Why the rejected paths are weaker: Prompt chains or autonomous agents cannot establish authorization authenticity or byte-level reproducibility, and would add nondeterminism at the trust boundary.
- Smallest useful prototype: Complete the Plan expression closure, define a strict governed lock packet input, produce one canonical golden Plan, and enforce all parity checks in locked CI.

## 4. Success Preview And Risk Plan
- Success standard: The same complete lock packet and BPS governance binding always produce identical Plan bytes/digest, and malformed, incomplete, unknown, or legacy mutable input is rejected before persistence.
- Pause / kill signal: The implementation starts routing Providers, derives capability names from restricted `skills/pptx`, rewrites Plan requirements for compatibility, or requires changing BPS frozen v1 contracts.
- Degraded fallback: Keep the current Presentation Director standalone workflow and the BPS proof-level Plan separate; do not start Eligibility.
- Owner and review cadence: Presentation Director owns schema/compiler changes; BPS performs an independent compatibility and authority review before Eligibility begins.
