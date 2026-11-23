# Handoff

## 首轮产品化（2026-11-23 起，当前主线）

### Completed
- 方案审查与 Codex 复审完成，结论见 `docs/distribution/2026-11-23-engine-plan-review-brief.md` 第 7 节。
- 已删除专有的 `skills/pptx/`；自有代码改为保留所有权利（`LICENSE`）；官网去掉「开源」字样。
- 工作计划：`docs/distribution/2026-11-23-work-plan.md`；试用环境已远程核实（Win11 x64、WorkBuddy 5.11.3、WPS、无 PowerPoint）。

### Current State
- 计划待 owner 确认第 5 节的决定项；尚未开始实现。

### Next Steps
- 顺序 1：W1 逐页输入格式 + W2 生成器，出样例后先上试用机用 WPS 验证图表数据可编辑。

### Key Decisions
- 首轮只做 Windows x64 + WorkBuddy stdio + PPTX + A/D 检查；HTTP、豆包、Necto、第二个系统推迟。

### Review 时间
- 无

### 验收标准
- 见工作计划 W8。

---

## 历史：PresentationDirectorPlanV1 Freeze Candidate

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
