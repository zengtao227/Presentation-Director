# PresentationDirectorPlanV1

Status: **frozen** (independent cross-repository Freeze Review verdict GO, 2026-08-13)  
Schema: `presentation-director-plan@1.0.0`  
Capability vocabulary: `presentation-artifact-capabilities@1.0.0`  
Freeze provenance: reviewed head `3f838b6d79cb69a40e22e86770cbcd2c7fd1a812`, merged as `6c1333735718e38034f0053da7c03433c4d7a4f0` (PR #12, tree-identical squash merge), tag `presentation-director-plan-v1.0.0`

## Purpose and scope

`PresentationDirectorPlanV1` is the persisted machine contract produced after Content Lock, Form Lock, Composition Lock, and human confirmation for a **BPS-governed PPTX** task. It freezes presentation intent before any Provider is selected.

V1 deliberately covers only governed `pptx`. Existing `html-revealjs` and `both` workflows continue to use the current interactive path. Provider-neutral therefore means neutral across PPTX implementations, not a generic multi-medium IR.

The Plan must not contain Provider identity, routing preference, executable/cache path, Provider self-reported eligibility, generation status, artifact digest, QA evidence, or implementation-specific helper/API names. Working-state fields such as advisory PASS, unresolved planning questions, proposed new governed inputs, and fallback instructions also stay outside the persisted Plan. Those conditions must stop Plan production before persistence.

## Lock compilation

- **Content Lock** supplies audience, goal, thesis, narrative arc, governed content coverage, slide claims, proof objects, omissions, language, and length intent.
- **Form Lock** supplies the selected Director-owned form direction and forbidden patterns.
- **Composition Lock** supplies semantic slide sequence, per-slide layout family, visual treatment, approved assets, governed fact/source bindings for charts and tables, task-source usage, font/token selections, reference-only influence, speaker notes, omissions, and required artifact capabilities.

Human-readable locks remain editing sources. Plan V1 is the cross-repository persisted IR for the governed PPTX path.

### Current interactive brief is not a governed compiler source

The existing `brief-confirmed.json` must **not** be treated as the direct source for Plan V1. In the current workflow `/api/confirm` copies intake/visual-selection state into that file and marks it confirmed, while later image-style work can mutate the same file without a new human confirmation. It also does not contain the complete machine-readable Content/Form/Composition Locks or the BPS governance binding.

The candidate now implements this boundary as `GovernedPlanProductionInputV1`: an explicit complete `ConfirmedDirectorLockPacketV1` plus the BPS governance binding. `compile_presentation_director_plan_v1()` revalidates that strict input, derives only the canonical top-level capability union, and never infers or invents missing Plan fields. The legacy interactive brief shape cannot validate as production input.

The lock packet's `confirmation_state = confirmed` records workflow state only. It is not actor authentication. Trusted Plan confirmation remains an external event bound to the compiled canonical Plan digest.

## Authority binding

A governed Plan binds `resolved_job_id`, `resolved_job_sha256`, `constraint_view_sha256`, and the selected treatment identity/version/digest. These fields do not grant authority by themselves: BPS must independently reconstruct the upstream chain and evaluate Plan conformance.

The Plan also does **not** self-authenticate its human confirmation. A file claiming to be confirmed is not trusted merely because it exists or carries actor text. Governed execution must later require an external trusted confirmation event bound to the exact canonical Plan SHA-256. The event and its verification live outside Plan V1, analogous to the planned trusted authorization boundary for BrandPackage/TaskBrief.

Director-authored title, purpose, thesis, narrative, and other connective wording are exact human-confirmed presentation expression. They may organize or paraphrase approved content but may not introduce new enterprise facts. BPS remains factual authority; Presentation Director remains expression authority. Provider execution may not rewrite these fields to manufacture compatibility.

## Governance-visible presentation choices

Formal Plan V1 preserves the presentation choices that BPS must independently validate, rather than reducing them to prose. The candidate schema now carries:

- governed fact/claim/disclaimer bindings and explicit governed-content omissions with reasons;
- explicit slide kind so content slides require a governed primary claim while cover/structural slides may omit one;
- per-slide approved asset usage and digests;
- per-slide task-source IDs;
- per-slide selected font families;
- per-slide brand-token IDs;
- closed `reference_only_inspiration` provenance and per-slide reference IDs;
- selected treatment identity/digest and layout family;
- required artifact capabilities.

These fields preserve the fail-closed semantics already proven by the BPS presentation conformance proof for unknown content, sources, assets, fonts, brand tokens, references, treatment choices, and missing content coverage.

Cover/section-divider/closing slides may legitimately have no governed primary claim. Slides declared as `content` must carry one. Content-bearing claims remain exact governed content bindings; a Provider may not invent a claim to satisfy a schema requirement.

### Data and image input closure

V1 has no independent governed-dataset namespace, so it deliberately carries no free-form `dataset_ids`. A chart or table must bind at least one exact governed fact through `supporting_content`, and its proof-object `source_ids` must equal the union of those fact sources. This prevents a Provider from selecting or inventing post-resolution chart data. A future independently normalized dataset requires its own BPS-verifiable binding and a versioned contract change.

An `image` or `screenshot` proof must bind at least one approved `AssetBinding`. V1 does not yet support source-derived screenshots. A future use case such as a deterministic capture of an approved PDF page requires an explicit governed derivation contract; source prose alone is not permission for a Provider to choose or generate an image.

## Semantic order and canonical sets

Array order is semantic for `narrative_arc`, `slides`, `speaker_notes`, and `appendix_notes`. **Slides are never sorted by `slide_id`.** Reordering slides changes Plan meaning and digest.

Set-like collections must already be sorted and unique. Examples are source IDs, asset roles, font families, brand-token IDs, reference IDs, supporting governed-content bindings, slide assets, capabilities, omissions, and forbidden patterns. Validation rejects non-canonical input rather than silently rewriting it.

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
- `font_family_assignment`

Per-slide requirements are explicit. Top-level `required_capabilities` must equal their union. Capability dependencies fail closed: for example, editable chart data requires a native chart, attached connectors require native shapes, and non-empty speaker notes require speaker-note support. A proof object declared as a native table/chart/diagram/image must not silently degrade to rasterized or flattened output merely because a Provider lacks the corresponding capability.

`font_family_assignment` means the Provider can apply every Plan-selected family to the corresponding editable text objects and preserve that assignment in the PPTX. It does **not** imply PowerPoint theme font-scheme authoring, font-file embedding, font licensing, or runtime font availability; those are separate policies/capabilities if later required. Every V1 slide has governed `font_families`, so every eligible V1 Provider must support exact object-level family assignment.

### Clean-room rule

Vocabulary evolution is driven only by Presentation Director business semantics, public file-format/product documentation, and independently defined BPS acceptance requirements. Do not inspect, derive, translate, or mirror helper names, function architecture, or internal capability vocabulary from restricted `skills/pptx` materials when designing this contract or a portable Provider.

## Canonical bytes

A fully validated Plan uses RFC 8785 JSON Canonicalization Scheme; the Plan digest is SHA-256 over those exact UTF-8 bytes. The checked-in six-slide golden fixture covers a cover, executive summary, native table, native chart, native shapes/connectors, and bilingual density/image/speaker-note stress slide.

Any schema or serialization change that changes golden bytes requires an explicit compatibility decision. Silent digest drift is forbidden. The current six-slide fixture is 6,866 canonical bytes with SHA-256 `5768c81519b3d18ada5c62bb14afb8565cc35b5b6b9706388c1a2be53c3eb1bc`.

## Ownership

Presentation Director owns the Plan schema/version, capability vocabulary, compilation rules, exact Director-authored expression, and golden fixture. BPS owns supported Plan versions, trusted Plan-confirmation verification, constraint reconstruction, Plan conformance, Provider policy/eligibility, GenerationRequest, independent artifact validation, human release authorization, and ReleaseManifest. A Provider owns no governance authority.

BPS's current proof-level `PresentationDirectorPlan` schema `0.1` is not the formal V1 contract and must not be renamed or treated as byte-compatible. BPS support for formal Plan V1 is a separate compatibility implementation after this freeze review.

## Freeze implementation status

The frozen head closed the three implementation groups identified by the adversarial review:

1. governance-visible expression fields are present in the model, schema, production input, golden fixture, and positive/negative tests;
2. pinned Python/uv CI installs from committed `uv.lock` and runs the complete existing and Plan-specific test suite, full Python compileall, and contract-surface Ruff, format, strict mypy, schema/golden parity, installer syntax, and package build;
3. the strict governed producer boundary rejects incomplete, draft, unknown, and legacy brief-shaped input.

This closed the freeze candidacy: the reviewed head passed CI and an independent cross-repository Freeze Review with verdict GO (see Status above). Implementation completeness did not by itself approve the schema — the independent review did.

The Ruff/format gate is intentionally scoped to the independent contract package, artifact exporters, and Plan tests. The legacy 346 KB UI/state module, duplicated standalone scripts, HTML-heavy sources, and vendored skills predate this candidate and are not silently reformatted in a schema-freeze PR; they remain covered by the complete test suite and compileall. Expanding lint coverage is separate technical-debt work.

The contract wheel depends only on Pydantic and RFC 8785. Playwright remains an optional standalone workflow dependency. Exact Python 3.10.18 and 3.11.13 compatibility jobs complement the primary pinned Python 3.12.9 locked verification, exercising the declared Python 3.10 floor and every minor version through the primary runtime.

## Freeze gate — closed

V1 froze once strict unknown-field rejection, semantic ordering, sorted-set validation, slide-count invariants, governance-visible expression closure, capability vocabulary closure, capability dependencies/union validation, schema export parity, golden digest stability, pinned/locked CI, and the existing Presentation Director test suite were all green, and an independent cross-repository Freeze Review gave verdict GO on the exact reviewed head (see Status above). Any change to schema/version identity, capability vocabulary identity, or golden bytes/digest requires an explicit new compatibility decision and a new freeze tag; this frozen head and tag are not to be moved.

## Explicit non-goals

No Capability Router, EligibilityDecision, portable Provider, Codex cache promotion, GenerationRequest, PPTX generation, native PPTX validation, or generic Director framework is implemented in this milestone.
