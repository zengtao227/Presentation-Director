# Task Eval: Presentation Plan V1 Freeze Candidate

## Goal
- Close the three Draft PR #12 freeze blockers without implementing Eligibility, Provider routing, or PPTX generation.

## Acceptance Criteria
- [x] Plan V1 represents per-slide task sources, fonts, brand tokens, references, governed omissions with reasons, and closed reference-only provenance.
- [x] Cover and structural slides can omit `primary_claim`; governed content bindings remain digest-bound and closed.
- [x] Unknown, incomplete, conflicting, non-canonical, or undeclared governed expression fails closed.
- [x] A strict complete lock packet plus BPS governance binding deterministically produces Plan V1.
- [x] Legacy mutable `brief-confirmed.json` cannot validate as producer input.
- [x] Capability vocabulary remains route-neutral and is not derived from restricted `skills/pptx` implementation details.
- [x] Checked-in JSON Schema and RFC 8785 golden digest match the implementation.
- [x] A committed `uv.lock` and pinned CI run the full existing and Plan-specific verification suite.
- [x] Existing standalone Presentation Director behavior remains green.
- [x] Chart/table proof contains no free-floating dataset namespace and binds governed facts plus governed sources.
- [x] Image/screenshot proof fails closed unless at least one approved asset is bound.
- [x] Font capability means exact editable-object font-family assignment, not PowerPoint theme-scheme authoring.
- [x] The contract-only wheel does not require Playwright at runtime.
- [x] Pinned CI exercises the declared Python 3.10 floor and every minor version through the primary Python 3.12 job.

## Verification
- Command: `uv run --locked pytest -ra`
- Expected: all tests pass; skips, if any, have explicit environment reasons.
- Command: `uv run --locked ruff check src/presentation_director_contracts scripts/export_plan_v1_schema.py scripts/export_plan_v1_golden.py tests/test_plan_v1_*.py`
- Expected: lint passes on every new frozen-contract file; legacy UI/state and vendored skills remain outside this bounded refactor.
- Command: `uv run --locked ruff format --check src/presentation_director_contracts scripts/export_plan_v1_schema.py scripts/export_plan_v1_golden.py tests/test_plan_v1_*.py`
- Expected: formatting passes on every new frozen-contract file.
- Command: `uv run --locked mypy src/presentation_director_contracts`
- Expected: strict type checking passes.
- Command: `uv run --locked python -m compileall -q src scripts tests skills/deck-builder/scripts`
- Expected: compilation succeeds.
- Command: `uv run --locked python scripts/export_plan_v1_schema.py --check`
- Expected: checked-in schema parity passes without writing.
- Command: `uv build --no-build-isolation`
- Expected: sdist and wheel build successfully.

## Manual Checks
- [x] Inspect the golden Plan and confirm semantic slide order is preserved.
- [x] Inspect CI and confirm exact Python/uv pins, action SHAs, and `uv sync --locked --all-extras`.
- [x] Search for direct `brief-confirmed.json` producer use and restricted implementation-derived capability terms.

## Result
- Status: PASS
- Evidence:
  - `uv run --locked pytest -ra`: 85 passed, 0 skipped.
  - Python 3.10.18 and 3.11.13 isolated locked Plan suites: 43 passed on each version; pinned matrix jobs are committed alongside the primary exact Python 3.12.9 job.
  - Schema and golden `--check`: PASS; Plan is 6,866 RFC 8785 bytes, SHA-256 `5768c81519b3d18ada5c62bb14afb8565cc35b5b6b9706388c1a2be53c3eb1bc`.
  - Contract-surface Ruff/format: PASS; strict mypy: PASS.
  - Full compileall and installer syntax checks: PASS.
  - `uv build --no-build-isolation`: sdist and wheel built; clean temporary wheel import smoke passed.
  - Built archives contain only the contract package and packaging metadata; no `skills/` subtree is distributed and Playwright is not a default runtime requirement.
- Remaining risks:
  - Formal cross-repository BPS compatibility review remains required before the candidate is declared frozen.
