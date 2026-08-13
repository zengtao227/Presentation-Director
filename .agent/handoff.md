# Handoff: PresentationDirectorPlanV1 Freeze Candidate

## Completed
- Closed the governed-expression, deterministic producer, and locked-CI implementation blockers on Draft PR #12.
- Added strict production input and Plan schemas, regenerated the six-slide RFC 8785 golden Plan, and recorded negative tests for legacy/malformed input.
- Removed the ungoverned dataset namespace, closed image/screenshot inputs to approved assets, and defined object-level font-family assignment semantics.
- Kept Playwright out of the contract wheel's default runtime and added exact Python 3.10/3.11 contract compatibility jobs beside the primary 3.12 verification.

## Current State
- Branch: `codex/presentation-plan-v1-freeze`.
- The candidate remains Draft pending GitHub CI and independent cross-repository freeze review.
- Eligibility, Provider routing, GenerationRequest, and PPTX generation remain out of scope and unimplemented.

## Next Steps
- Review the pushed diff and GitHub CI evidence.
- If the candidate receives GO, freeze the exact Plan/capability versions and begin BPS compatibility work before Eligibility.

## Key Decisions
- `brief-confirmed.json` remains a mutable standalone workflow input and cannot be a governed producer source.
- Capability vocabulary comes from business/file-format semantics, not restricted `skills/pptx` implementation details.
- Ruff/format gates cover the new contract surface; legacy UI/state lint debt remains separate while full tests and compileall cover the repository.
