# PresentationDirectorPlanV1

Status: **freeze candidate — not freeze-ready**  
Schema: `presentation-director-plan@1.0.0`  
Capability vocabulary: `presentation-artifact-capabilities@1.0.0`

## Purpose and scope

`PresentationDirectorPlanV1` is the persisted machine contract produced after Content Lock, Form Lock, Composition Lock, and human confirmation for a **BPS-governed PPTX** task. It freezes presentation intent before any Provider is selected.

V1 deliberately covers only governed `pptx`. Existing `html-revealjs` and `both` workflows continue to use the current interactive path. Provider-neutral therefore means neutral across PPTX implementations, not a generic multi-medium IR.

The Plan must not contain Provider identity, routing preference, executable/cache path, Provider self-reported eligibility, generation status, artifact digest, QA evidence, or implementation-specific helper/API names. Working-state fields such as advisory PASS, unresolved planning questions, proposed new governed inputs, and fallback instructions also stay outside the persisted Plan. Those conditions must stop Plan production before persistence.

## Lock compilation

- **Content Lock** supplies audience, goal, thesis, narrative arc, governed content coverage, slide claims, proof objects, omissions, language, and length intent.
- **Form Lock** supplies the selected Director-owned form direction and forbidden patterns.
- **Composition Lock** supplies semantic slide sequence, per-slide layout family, visual treatment, assets/data, task-source usage, font/token selections, reference-only influence, speaker notes, omissions, and required artifact capabilities.

Human-readable locks remain editing sources. Plan V1 is the cross-repository persisted IR for the governed PPTX path.

### Current interactive brief is not a governed compiler source

The existing `brief-confirmed.json` must **not** be treated as the direct source for Plan V1. In the current workflow `/api/confirm` copies intake/visual-selection state into that file and marks it confirmed, while later image-style work can mutate the same file without a new human confirmation. It also does not contain the complete machine-readable Content/Form/Composition Locks or the BPS governance binding.

Therefore a governed Plan producer must eventually consume an explicit complete lock packet plus the BPS governance binding and fail closed on missing fields. It must never infer or invent missing Plan fields from the legacy interactive brief.

## Authority binding

A governed Plan binds `resolved_job_id`, `resolved_job_sha256`, `constraint_view_sha256`, and the selected treatment identity/version/digest. These fields do not grant authority by themselves: BPS must independently reconstruct the upstream chain and evaluate Plan conformance.

The Plan also does **not** self-authenticate its human confirmation. A file claiming to be confirmed is not trusted merely because it exists or carries actor text. Governed execution must later require an external trusted confirmation event bound to the exact canonical Plan SHA-256. The event and its verification live outside Plan V1, analogous to the planned trusted authorization boundary for BrandPackage/TaskBrief.

Director-authored title, purpose, thesis, narrative, and other connective wording are exact human-confirmed presentation expression. They may organize or paraphrase approved content but may not introduce new enterprise facts. BPS remains factual authority; Presentation Director remains expression authority. Provider execution may not rewrite these fields to manufacture compatibility.

## Governance-visible presentation choices

Formal Plan V1 must preserve the presentation choices that BPS must independently validate, rather than reducing them to prose. Before freeze the schema must carry, at minimum:

- governed fact/claim/disclaimer bindings and explicit governed-content omissions with reasons;
- per-slide approved asset usage and digests;
- per-slide task-source IDs;
- per-slide selected font families;
- per-slide brand-token IDs;
- closed `reference_only_inspiration` provenance and per-slide reference IDs;
- selected treatment identity/digest and layout family;
- required artifact capabilities.

These fields preserve the fail-closed semantics already proven by the BPS presentation conformance proof for unknown content, sources, assets, fonts, brand tokens, references, treatment choices, and missing content coverage.

Cover/structural slides may legitimately have no governed primary claim. Content-bearing claims remain exact governed content bindings; a Provider may not invent a claim to satisfy a schema requirement.

## Semantic order and canonical sets

Array order is semantic for `narrative_arc`, `slides`, `speaker_notes`, and `appendix_notes`. **Slides are never sorted by `slide_id`.** Reordering slides changes Plan meaning and digest.

Set-like collections must already be sorted and unique. Examples are source IDs, dataset IDs, asset roles, font families, brand-token IDs, reference IDs, supporting governed-content bindings, slide assets, capabilities, omissions, and forbidden patterns. Validation rejects non-canonical input rather than silently rewriting it.

## Length

Exactly one primary control is required: `target_slide_count` or `slide_count_range`. `target_duration_minutes` is optional. An exact count must equal the persisted slide count; a range must contain it.

## Capability vocabulary

V1 capabilities describe artifact semantics:

- `editable_text`
- `native_table`
- `native_chart`
- `editable_chart_data`
- `native_shapes`
- `attached_connectors`
- `speaker_notes`
- `embedded_images`

Per-slide requirements are explicit. Top-level `required_capabilities` must equal their union. Capability dependencies fail closed: for example, editable chart data requires a native chart, attached connectors require native shapes, and non-empty speaker notes require speaker-note support. A proof object declared as a native table/chart/diagram/image must not silently degrade to rasterized or flattened output merely because a Provider lacks the corresponding capability.

### Clean-room rule

Vocabulary evolution is driven only by Presentation Director business semantics, public file-format/product documentation, and independently defined BPS acceptance requirements. Do not inspect, derive, translate, or mirror helper names, function architecture, or internal capability vocabulary from restricted `skills/pptx` materials when designing this contract or a portable Provider.

## Canonical bytes

A fully validated Plan uses RFC 8785 JSON Canonicalization Scheme; the Plan digest is SHA-256 over those exact UTF-8 bytes. The checked-in six-slide golden fixture covers a cover, executive summary, native table, native chart, native shapes/connectors, and bilingual density/image/speaker-note stress slide.

Any schema or serialization change that changes golden bytes requires an explicit compatibility decision. Silent digest drift is forbidden.

## Ownership

Presentation Director owns the Plan schema/version, capability vocabulary, compilation rules, exact Director-authored expression, and golden fixture. BPS owns supported Plan versions, trusted Plan-confirmation verification, constraint reconstruction, Plan conformance, Provider policy/eligibility, GenerationRequest, independent artifact validation, human release authorization, and ReleaseManifest. A Provider owns no governance authority.

BPS's current proof-level `PresentationDirectorPlan` schema `0.1` is not the formal V1 contract and must not be renamed or treated as byte-compatible. BPS support for formal Plan V1 is a separate compatibility implementation after this freeze review.

## Freeze blockers

The current branch is deliberately still a candidate. It must not be marked frozen until all of the following are closed:

1. the formal schema restores the governance-visible fields listed above and the golden fixture/tests are regenerated;
2. pinned/locked CI exists with a committed dependency lock and full existing Presentation Director tests;
3. schema-export parity and golden digest are verified using the real RFC 8785 implementation in CI;
4. the Plan production boundary is documented such that legacy mutable `brief-confirmed.json` cannot be mistaken for a trusted governed Plan source.

## Freeze gate

V1 is ready to freeze only when strict unknown-field rejection, semantic ordering, sorted-set validation, slide-count invariants, governance-visible expression closure, capability vocabulary closure, capability dependencies/union validation, schema export parity, golden digest stability, pinned/locked CI, and the existing Presentation Director test suite are all green.

## Explicit non-goals

No Capability Router, EligibilityDecision, portable Provider, Codex cache promotion, GenerationRequest, PPTX generation, native PPTX validation, or generic Director framework is implemented in this milestone.