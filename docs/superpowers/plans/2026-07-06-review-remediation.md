# Presentation Director Review Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the concrete P1/P2 findings from `docs/architecture-review-2026-07-06.md` — two functional field-dropping bugs, a stale-fork drift between duplicated scripts, a gap in the `guard` command's QA coverage, one dead-code cleanup, and mechanical lint/naming cleanup.

**Architecture:** No structural changes. All fixes are localized edits inside the existing `skills/deck-builder/scripts/presentation_director.py` monolith (per the review, splitting it is P3/out of scope), plus a byte-identical resync of two forked top-level convenience scripts, plus mechanical lint fixes in `skills/ui-ux-pro-max`.

**Tech Stack:** Python 3.10+, `unittest` (existing `tests/test_presentation_director.py`), `ruff`.

## Global Constraints

- After every task, `python3 -m pytest tests/ -q` must report at least 35 passed with zero failures (current baseline: `35 passed in 11.25s`).
- One task = one commit. Only `git add` the exact files touched by that task (never `git add -A`).
- Commit messages follow the project convention: `git commit -m "fix: <简要描述>"` (Chinese description), no `git push` — pushing is a manual step the user does after reviewing all commits.
- Do not merge `skills/deck-builder/scripts/` into the top-level `scripts/` directory, and do not delete either tree: `bootstrap.sh` copies `skills/deck-builder/` wholesale to `~/.claude/skills` and `~/.codex/skills`, so it must remain self-contained.
- Do not convert `scripts/preview_locks.py` or `scripts/preview_palette.py` into `runpy` shims (unlike `scripts/presentation_director.py`). Both use `Path(__file__).parent.parent` to locate the *current* project's `assets/` folder; a shim would make `__file__` resolve inside `skills/deck-builder/scripts/` instead, silently redirecting reads/writes to `skills/deck-builder/assets/`. Keep them as byte-identical copies instead (see Task 3).

---

### Task 1: Fix dropped `gradient_preview` field in the Visual Inspiration candidate card

**Files:**
- Modify: `skills/deck-builder/scripts/presentation_director.py:4568-4630` (function `render_visual_candidate_card`)
- Test: `tests/test_presentation_director.py`

**Interfaces:**
- Consumes: `PD.VisualCandidate` (frozen dataclass, fields: `key, name, summary, best_for, avoid_for, palette, background, typography, layout, chart, image_strategy, inspiration, risk, html_transition="slide", html_animation="minimal", html_gradient="", suggested_html_theme=""`), `PD.render_visual_candidate_card(candidate, checked, ui_language="zh", show_html_fields=False) -> str`.
- Produces: no signature change; `render_visual_candidate_card` now includes the gradient swatch markup it already computes.

- [ ] **Step 1: Write the failing test**

Add this test class to `tests/test_presentation_director.py`, immediately before the final `if __name__ == "__main__":` block:

```python
        self.assertNotEqual(0, result.returncode)
        self.assertIn("No layout files found", result.stderr)


class VisualCandidateCardRenderTest(unittest.TestCase):
    def test_html_gradient_preview_is_rendered_when_present(self) -> None:
        candidate: PD.VisualCandidate = PD.VisualCandidate(
            key="aurora-test",
            name="Aurora Test",
            summary="summary",
            best_for="best",
            avoid_for="avoid",
            palette=("#0f172a", "#e2e8f0", "#38bdf8", "#a855f7"),
            background="dark gradient",
            typography="sans",
            layout="grid",
            chart="line",
            image_strategy="none",
            inspiration="test",
            risk="none",
            html_transition="fade",
            html_animation="subtle",
            html_gradient="linear-gradient(135deg, #0f172a, #38bdf8)",
            suggested_html_theme="aurora",
        )
        card_html: str = PD.render_visual_candidate_card(
            candidate, checked=True, ui_language="zh", show_html_fields=True
        )
        self.assertIn("linear-gradient(135deg, #0f172a, #38bdf8)", card_html)


if __name__ == "__main__":
```

(This replaces the old tail `...No layout files found", result.stderr)\n\n\nif __name__ == "__main__":` with the same text plus the new class inserted before `if __name__ == "__main__":`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_presentation_director.py -k test_html_gradient_preview_is_rendered_when_present -v`
Expected: FAIL — `AssertionError: 'linear-gradient(135deg, #0f172a, #38bdf8)' not found in ...` (the variable is computed but never inserted into the returned template).

- [ ] **Step 3: Insert the missing field into the template**

In `skills/deck-builder/scripts/presentation_director.py`, function `render_visual_candidate_card`, find:

```python
  <p><strong>{html.escape(t(ui_language, "chart"))}:</strong> {html.escape(localized_visual_field(candidate_json, "chart", ui_language))}</p>
  {theme_info}
  <p><strong>{html.escape(t(ui_language, "inspiration"))}:</strong> {html.escape(localized_visual_field(candidate_json, "inspiration", ui_language))}</p>
```

Replace with:

```python
  <p><strong>{html.escape(t(ui_language, "chart"))}:</strong> {html.escape(localized_visual_field(candidate_json, "chart", ui_language))}</p>
  {theme_info}
  {gradient_preview}
  <p><strong>{html.escape(t(ui_language, "inspiration"))}:</strong> {html.escape(localized_visual_field(candidate_json, "inspiration", ui_language))}</p>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_presentation_director.py -k test_html_gradient_preview_is_rendered_when_present -v`
Expected: PASS

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python3 -m pytest tests/ -q`
Expected: `36 passed` (35 existing + 1 new)

- [ ] **Step 6: Commit**

```bash
git add skills/deck-builder/scripts/presentation_director.py tests/test_presentation_director.py
git commit -m "fix: 补上 Visual Inspiration 卡片里丢失的 HTML 渐变预览"
```

---

### Task 2: Fix dropped `html_transition` field in the HTML deck generation prompt

**Files:**
- Modify: `skills/deck-builder/scripts/presentation_director.py` (function `initial_prompt`, around line 5572)
- Test: `tests/test_presentation_director.py`

**Interfaces:**
- Consumes: `PD.initial_prompt(task_dir: Path) -> str` (reads `task_dir / "brief-confirmed.json"`).
- Produces: no signature change; the returned prompt string now documents the locked `transition` value.

- [ ] **Step 1: Write the failing test**

Add this test class to `tests/test_presentation_director.py`, immediately before the final `if __name__ == "__main__":` block (which now follows `VisualCandidateCardRenderTest` from Task 1):

```python
        card_html: str = PD.render_visual_candidate_card(
            candidate, checked=True, ui_language="zh", show_html_fields=True
        )
        self.assertIn("linear-gradient(135deg, #0f172a, #38bdf8)", card_html)


class InitialPromptHtmlConfigTest(unittest.TestCase):
    def test_html_transition_is_included_in_generation_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = Path(tmp_dir) / "Decks" / "transition-task"
            task_dir.mkdir(parents=True)
            brief: dict[str, object] = {
                "confirmed": True,
                "output_format": "html-revealjs",
                "html_config": {"transition": "zoom-fade"},
            }
            (task_dir / "brief-confirmed.json").write_text(json.dumps(brief), encoding="utf-8")
            prompt: str = PD.initial_prompt(task_dir)
            self.assertIn('transition from html_config: "zoom-fade"', prompt)


if __name__ == "__main__":
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_presentation_director.py -k test_html_transition_is_included_in_generation_prompt -v`
Expected: FAIL — the assertion string is not present anywhere in the prompt (the raw `json.dumps(brief, ...)` dump in `common_rules` contains `"transition": "zoom-fade"` with different formatting/quoting, which does not match the exact assertion string, so this correctly fails before the fix).

- [ ] **Step 3: Insert the missing directive into `html_requirements`**

In `skills/deck-builder/scripts/presentation_director.py`, inside `initial_prompt`, find:

```python
- theme_key from html_config: "{theme_key}". Resolve it to `{html_deck_root / "assets" / "themes"}` / `<theme_key>.css`; if that file is missing, use `minimal-white`.
- Consume HTML deck theme tokens (`--bg`, `--surface`, `--surface-2`, `--border`, `--text-1`, `--text-2`, `--text-3`, `--accent`, `--accent-2`, `--accent-3`, `--grad`) instead of regenerating one-off per-slide colors. Background hint: "{html_gradient or 'use the selected HTML deck theme background'}".
```

Replace with:

```python
- theme_key from html_config: "{theme_key}". Resolve it to `{html_deck_root / "assets" / "themes"}` / `<theme_key>.css`; if that file is missing, use `minimal-white`.
- transition from html_config: "{html_transition}". Use it as the slide-change transition intent (wire it into `assets/runtime.js` transition config or the slide-change animation class); do not substitute a different default transition.
- Consume HTML deck theme tokens (`--bg`, `--surface`, `--surface-2`, `--border`, `--text-1`, `--text-2`, `--text-3`, `--accent`, `--accent-2`, `--accent-3`, `--grad`) instead of regenerating one-off per-slide colors. Background hint: "{html_gradient or 'use the selected HTML deck theme background'}".
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_presentation_director.py -k test_html_transition_is_included_in_generation_prompt -v`
Expected: PASS

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python3 -m pytest tests/ -q`
Expected: `37 passed`

- [ ] **Step 6: Commit**

```bash
git add skills/deck-builder/scripts/presentation_director.py tests/test_presentation_director.py
git commit -m "fix: 补上生成提示词里丢失的 html_transition 字段"
```

---

### Task 3: Close the `preview_locks.py` / `preview_palette.py` drift and lock it with a regression test

**Files:**
- Modify: `skills/deck-builder/scripts/preview_locks.py` (add maintenance-note comment)
- Modify: `skills/deck-builder/scripts/preview_palette.py` (add maintenance-note comment)
- Modify: `skills/deck-builder/scripts/check_presentation_safe_area.py` (add maintenance-note comment)
- Modify: `scripts/preview_locks.py`, `scripts/preview_palette.py`, `scripts/check_presentation_safe_area.py` (become byte-identical copies of the above)
- Test: `tests/test_presentation_director.py`

**Interfaces:**
- No Python function signatures change. This task only guarantees `scripts/<name>.py` and `skills/deck-builder/scripts/<name>.py` stay byte-identical for these three files, enforced by a new `TopLevelScriptSyncTest`.

- [ ] **Step 1: Add the `filecmp` import**

In `tests/test_presentation_director.py`, find:

```python
import importlib.util
import json
import subprocess
```

Replace with:

```python
import filecmp
import importlib.util
import json
import subprocess
```

- [ ] **Step 2: Write the failing test**

Add this test class to `tests/test_presentation_director.py`, immediately before the final `if __name__ == "__main__":` block (which now follows `InitialPromptHtmlConfigTest` from Task 2):

```python
            prompt: str = PD.initial_prompt(task_dir)
            self.assertIn('transition from html_config: "zoom-fade"', prompt)


class TopLevelScriptSyncTest(unittest.TestCase):
    """scripts/*.py must stay byte-identical to their skills/deck-builder/scripts/*.py
    canonical source. Do not "fix" this by converting the top-level copy into a
    runpy shim: preview_locks.py and preview_palette.py resolve `assets/` via
    Path(__file__).parent.parent, which is meant to mean the current project's
    root. A shim would make __file__ resolve inside skills/deck-builder/scripts/
    instead, silently redirecting reads/writes to skills/deck-builder/assets/.
    """

    def _assert_synced(self, name: str) -> None:
        top_level: Path = ROOT_DIR / "scripts" / name
        canonical: Path = ROOT_DIR / "skills" / "deck-builder" / "scripts" / name
        self.assertTrue(
            filecmp.cmp(top_level, canonical, shallow=False),
            f"{top_level} has drifted from {canonical}. Fix with: cp {canonical} {top_level}",
        )

    def test_preview_locks_is_synced(self) -> None:
        self._assert_synced("preview_locks.py")

    def test_preview_palette_is_synced(self) -> None:
        self._assert_synced("preview_palette.py")

    def test_check_presentation_safe_area_is_synced(self) -> None:
        self._assert_synced("check_presentation_safe_area.py")


if __name__ == "__main__":
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_presentation_director.py -k TopLevelScriptSyncTest -v`
Expected: `test_preview_locks_is_synced` FAIL, `test_preview_palette_is_synced` FAIL, `test_check_presentation_safe_area_is_synced` PASS (this one is already byte-identical today).

- [ ] **Step 4: Add a maintenance-note comment to the three canonical files**

In `skills/deck-builder/scripts/preview_locks.py`, find the end of the module docstring:

```python
Usage:
    python3 scripts/preview_locks.py
    # then open: assets/locks-preview.html
"""

import http.server
```

Replace with:

```python
Usage:
    python3 scripts/preview_locks.py
    # then open: assets/locks-preview.html
"""

# MAINTENANCE: scripts/preview_locks.py (repo top level) must stay byte-identical
# to this file — do not replace it with a runpy shim (see Global Constraints in
# docs/superpowers/plans/2026-07-06-review-remediation.md for why). After editing
# this file, run: cp skills/deck-builder/scripts/preview_locks.py scripts/preview_locks.py
# Enforced by tests/test_presentation_director.py::TopLevelScriptSyncTest.

import http.server
```

In `skills/deck-builder/scripts/preview_palette.py`, find the end of its module docstring (the line right before its first `import`, e.g. `import http.server` per the earlier ruff findings) and add the equivalent note, substituting `preview_palette.py` for `preview_locks.py` in both the prose and the `cp` command.

In `skills/deck-builder/scripts/check_presentation_safe_area.py`, add the equivalent note after its module docstring, substituting `check_presentation_safe_area.py` in both the prose and the `cp` command, and dropping the shim-specific sentence (this file doesn't use `Path(__file__)`, so a shim would technically be safe for it, but it stays a plain copy for consistency with the other two and so one test class covers all three uniformly).

- [ ] **Step 5: Propagate the canonical files to the top-level copies**

```bash
cp skills/deck-builder/scripts/preview_locks.py scripts/preview_locks.py
cp skills/deck-builder/scripts/preview_palette.py scripts/preview_palette.py
cp skills/deck-builder/scripts/check_presentation_safe_area.py scripts/check_presentation_safe_area.py
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python3 -m pytest tests/test_presentation_director.py -k TopLevelScriptSyncTest -v`
Expected: 3 passed

- [ ] **Step 7: Run the full suite to confirm no regressions**

Run: `python3 -m pytest tests/ -q`
Expected: `40 passed` (this task adds 3 tests: 37 + 3)

This specifically re-verifies `test_safe_area_checker_fails_on_empty_layout_directory`, which invokes `scripts/check_presentation_safe_area.py` via `subprocess` — confirming the propagated copy still behaves correctly as a standalone script.

- [ ] **Step 8: Commit**

```bash
git add skills/deck-builder/scripts/preview_locks.py skills/deck-builder/scripts/preview_palette.py skills/deck-builder/scripts/check_presentation_safe_area.py scripts/preview_locks.py scripts/preview_palette.py scripts/check_presentation_safe_area.py tests/test_presentation_director.py
git commit -m "fix: 同步顶层 preview_locks.py/preview_palette.py 到规范实现，消除过时分叉"
```

---

### Task 4: Make `guard` re-verify Playwright visual QA, not just static checks

**Files:**
- Modify: `skills/deck-builder/scripts/presentation_director.py` (function `preview_review_gate_errors`, line 2954)
- Test: `tests/test_presentation_director.py`

**Interfaces:**
- Consumes: `PD.playwright_visual_qa(html_path: Path) -> list[str]` (already exists; previously only called from `cmd_finalize`).
- Produces: `PD.preview_review_gate_errors(task_dir: Path, version_name: str = "v1") -> list[str]` now also includes Playwright-detected errors (prefixed `"HTML visual QA: "`). Both existing callers (`validate_generation_guard` and `ensure_preview_review_gate_passed`) pick this up automatically with no call-site changes.

- [ ] **Step 1: Write the failing test**

Add this test class to `tests/test_presentation_director.py`, immediately before the final `if __name__ == "__main__":` block (which now follows `TopLevelScriptSyncTest` from Task 3):

```python
    def test_check_presentation_safe_area_is_synced(self) -> None:
        self._assert_synced("check_presentation_safe_area.py")


class PreviewReviewGateRunsPlaywrightTest(unittest.TestCase):
    def test_generation_guard_surfaces_playwright_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir: Path = Path(tmp_dir)
            task_dir: Path = write_task(base_dir, GOOD_HTML)
            with patch.object(
                PD,
                "playwright_visual_qa",
                return_value=["Slide 2: content overflows .slide-safe by 40px"],
            ):
                errors: list[str] = PD.preview_review_gate_errors(task_dir)
            self.assertTrue(any("overflows" in error for error in errors))


if __name__ == "__main__":
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_presentation_director.py -k test_generation_guard_surfaces_playwright_errors -v`
Expected: FAIL — `errors` is empty because `preview_review_gate_errors` never calls `playwright_visual_qa`, so patching it has no observable effect and `GOOD_HTML` passes all existing static checks.

- [ ] **Step 3: Add the Playwright check to the gate**

In `skills/deck-builder/scripts/presentation_director.py`, find:

```python
    for path in preview_artifact_paths(task_dir, output_format, version_name):
        if path.name != "final.html":
            continue
        for iw in html_deck_integrity_warnings(path):
            errors.append(f"HTML integrity QA: {iw}")
        for fw in html_small_font_warnings(path):
            errors.append(f"HTML font-size QA: {fw}")
        for sw in html_structural_warnings(path):
            errors.append(f"HTML structural QA: {sw}")
    return errors
```

Replace with:

```python
    for path in preview_artifact_paths(task_dir, output_format, version_name):
        if path.name != "final.html":
            continue
        for iw in html_deck_integrity_warnings(path):
            errors.append(f"HTML integrity QA: {iw}")
        for fw in html_small_font_warnings(path):
            errors.append(f"HTML font-size QA: {fw}")
        for sw in html_structural_warnings(path):
            errors.append(f"HTML structural QA: {sw}")
        for ve in playwright_visual_qa(path):
            errors.append(f"HTML visual QA: {ve}")
    return errors
```

This is the exact same check `cmd_finalize` already runs on `.draft/final.html` before promotion — now `guard` (and the `preview-review` page gate) re-verifies it on the promoted `final.html` too, so it can no longer be bypassed by writing directly to `vN/final.html` and skipping `finalize`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_presentation_director.py -k test_generation_guard_surfaces_playwright_errors -v`
Expected: PASS

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `python3 -m pytest tests/ -q`
Expected: `41 passed`

Note: this makes `guard` and the `preview-review` page require Playwright/Chromium to be installed for any task with `output_format` in `{"html-revealjs", "both"}` — `cmd_finalize` already required this (see `playwright_visual_qa`'s `PLAYWRIGHT_MISSING` fallback, which returns a non-empty error list rather than skipping the check), so this task makes `guard` consistently as strict as `finalize` already was, not stricter than the project's existing behavior.

- [ ] **Step 6: Commit**

```bash
git add skills/deck-builder/scripts/presentation_director.py tests/test_presentation_director.py
git commit -m "fix: guard 命令补跑 Playwright 视觉 QA，堵住跳过 finalize 的漏洞"
```

---

### Task 5: Remove dead code and unify the duplicated `output_format` default in `validate_generation_guard`

**Files:**
- Modify: `skills/deck-builder/scripts/presentation_director.py` (function `render_visual_inspiration` around line 4523; function `validate_generation_guard` around lines 2009 and 2079)

**Interfaces:**
- No signature changes anywhere in this task.

- [ ] **Step 1: Remove the unused `current_candidate` local variable**

In `skills/deck-builder/scripts/presentation_director.py`, function `render_visual_inspiration`, find:

```python
    candidate_cards: list[str] = [
        render_visual_candidate_card(candidate, current_key == candidate.key, ui_language, show_html_fields)
        for candidate in candidates
    ]
    current_candidate: VisualCandidate = next((c for c in candidates if c.key == current_key), candidates[0])
    html_deck_picker_html: str = ""
```

Replace with:

```python
    candidate_cards: list[str] = [
        render_visual_candidate_card(candidate, current_key == candidate.key, ui_language, show_html_fields)
        for candidate in candidates
    ]
    html_deck_picker_html: str = ""
```

- [ ] **Step 2: Unify the two `output_format` computations in `validate_generation_guard`**

In `skills/deck-builder/scripts/presentation_director.py`, function `validate_generation_guard`, find:

```python
    output_format: str = output_format_from_brief(brief, "html-revealjs")
    for version_name in generated_preview_versions(task_dir, output_format):
```

Replace with:

```python
    output_format: str = output_format_from_brief(brief, "pptx")
    for version_name in generated_preview_versions(task_dir, output_format):
```

Then, further down in the same function, find:

```python
    output_format: str = output_format_from_brief(brief, "pptx")
    if image_mode in POST_V1_IMAGE_MODES and v1_preview_exists(task_dir, output_format):
```

Replace with:

```python
    if image_mode in POST_V1_IMAGE_MODES and v1_preview_exists(task_dir, output_format):
```

(This removes the second, now-redundant computation — both call sites already reuse the single `output_format` value computed earlier in the function.)

- [ ] **Step 3: Run the full suite to confirm no regressions**

Run: `python3 -m pytest tests/ -q`
Expected: `41 passed` (no new tests — this is a behavior-preserving cleanup; the default only differed for a `brief-confirmed.json` missing `output_format`, which cannot occur for a brief that already passed `confirmed is True` in production use)

- [ ] **Step 4: Verify with ruff that the dead-variable warning is gone**

Run: `ruff check skills/deck-builder/scripts/presentation_director.py --select F841`
Expected: no output (0 errors) — confirms the three `F841` hits found in the original review (`current_candidate`, `gradient_preview`, `html_transition`) are all resolved by Tasks 1, 2, and 5.

- [ ] **Step 5: Commit**

```bash
git add skills/deck-builder/scripts/presentation_director.py
git commit -m "refactor: 清理 render_visual_inspiration 死代码，统一 validate_generation_guard 的 output_format 默认值"
```

---

### Task 6: Clean up `ruff` lint findings in `skills/ui-ux-pro-max`

**Files:**
- Modify: `skills/ui-ux-pro-max/scripts/search.py`
- Modify: `skills/ui-ux-pro-max/scripts/design_system.py`
- Modify: `skills/ui-ux-pro-max/data/_sync_all.py`

**Interfaces:**
- No signature changes. Pure lint cleanup (unused import, unused local variables with no side effects, redundant `f""` string prefixes, one `E401` multiple-imports-on-one-line).

- [ ] **Step 1: Confirm current lint state**

Run: `ruff check skills/ui-ux-pro-max --output-format=concise`
Expected: 11 errors listed (1 `E401`, 1 `F401`, 5 `F541`, 4 `F841` across `search.py`, `design_system.py`, `_sync_all.py`).

- [ ] **Step 2: Apply safe fixes**

Run: `ruff check skills/ui-ux-pro-max --fix --unsafe-fixes`
Expected output ends with something like: `Fixed 11 errors.`

- [ ] **Step 3: Review the diff before committing**

Run: `git diff skills/ui-ux-pro-max`
Confirm every removed line is one of: an unused `import`, a redundant `f` string prefix, a merged multi-import line, or a `dict.get(...)`-only assignment whose result was never read (no side effects are being dropped — e.g. `style_name = style.get("Style Category", "")` with `style_name` never referenced again).

- [ ] **Step 4: Run the full suite to confirm no regressions**

Run: `python3 -m pytest tests/ -q`
Expected: `41 passed` (this skill has no dedicated pytest coverage in `tests/`; the check here is that the existing suite, which imports other modules from the repo, still collects and passes cleanly)

Run: `ruff check skills/ui-ux-pro-max`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add skills/ui-ux-pro-max/scripts/search.py skills/ui-ux-pro-max/scripts/design_system.py skills/ui-ux-pro-max/data/_sync_all.py
git commit -m "refactor: 清理 ui-ux-pro-max 的 ruff lint 问题（未用变量/导入/多余 f-string）"
```

---

### Task 7: Rename the stale `md2ppt` package name

**Files:**
- Modify: `package.json`

**Interfaces:** none.

- [ ] **Step 1: Rename the package**

In `package.json`, find:

```json
{
  "name": "md2ppt",
  "version": "1.0.0",
```

Replace with:

```json
{
  "name": "presentation-director",
  "version": "1.0.0",
```

- [ ] **Step 2: Verify the file is still valid JSON**

Run: `python3 -c "import json; json.load(open('package.json')); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Verify npm scripts still resolve (no functional dependency on the "name" field)**

Run: `npm run --silent 2>&1 | head -10`
Expected: lists `export:html`, `export:pdf`, `export:pptx`, `export:all` as before (npm scripts are keyed by name, not by the package `name` field, so this is unaffected — this step is a sanity check, not a real risk).

- [ ] **Step 4: Commit**

```bash
git add package.json
git commit -m "docs: package.json 名称从 md2ppt 改为 presentation-director"
```

---

## Final Check

After Task 7, run the full suite one more time and confirm the final count:

Run: `python3 -m pytest tests/ -q`
Expected: `41 passed`

Run: `ruff check .`
Expected: `All checks passed!`

At this point all P1 and P2 items from `docs/architecture-review-2026-07-06.md` are resolved. P3 (splitting `presentation_director.py` into modules) remains intentionally out of scope — revisit only if heavy new feature work on that script is planned.
