# Codex Presentation Director Workflow

> Status: implemented prototype for Codex + Presentations plugin, with Claude/offline parity rules for intake and confirmation.
>
> Goal: improve the real PPTX creation experience in Codex by adding a low-friction intake layer, a research strategy gate, a visual inspiration gate before generation, and a visual revision layer after the first draft, while leaving high-quality PPTX rendering to the Codex Presentations plugin.
>
> Prototype entrypoint: `scripts/presentation_director.py`, a thin wrapper around `skills/deck-builder/scripts/presentation_director.py` so the same helper can ship with the global `deck-builder` skill.

## First-Principles Analysis

### 1. 问题本质

Codex Presentations plugin 已经很强，尤其在以下方面：

- 生成 editable PPTX
- artifact-tool presentation JSX
- contact sheet
- layout JSON
- comeback rubric
- 渲染后迭代
- 专业场景 profile

当前真正的问题不是缺少 PPTX 生成能力，而是两个交互断点：

1. 生成前，用户经常没有一次性给出足够清楚的 audience、goal、research strategy、source boundary、content language、UI communication language、logo policy、image policy 和 output constraints。
2. 生成后，agent 通常只问“你觉得怎么样”，用户很难用抽象语言描述要换什么视觉方向。
3. 当用户只给主题并希望 agent 查资料时，资料研究深度、联网成本和外部 Deep Research 资料包使用方式没有被显式确认。
4. 当用户没有给参考 deck 时，视觉方向经常被推迟到 v1 之后再救火式修改，第一版表现力不足。

因此，增强方向不应该是重新造一个 PPTX renderer，而是做一个 `Presentation Director`，让 Presentations plugin 在更清楚的上下文中工作，并让用户通过点击完成下一轮风格重绘选择。

### 2. 现有机制审查

可以复用的现有机制：

| Mechanism | Role in this workflow |
|-----------|-----------------------|
| Codex Presentations plugin | Primary PPTX renderer and QA engine |
| deck-builder | Conceptual upstream workflow, but Codex mode should be lighter |
| `docs/quality-gates.md` | Shared output quality model |
| `design-locks/` | Optional style lock, not required for the first Codex draft |
| `ui-ux-pro-max` / design-consultant | Optional advisor for palettes and visual alternatives |

不应重复建设：

- 不重写 artifact-tool PPTX build pipeline。
- 不在第一版生成前锁死每页 layout。
- 不强制用户维护 `deck.md` + HTML + JSON 多个事实源。
- 不把 `design-locks` 当作 Codex 首版生成的硬前置条件。

### 3. 约束条件

Hard constraints:

- Codex 环境下，PPTX 生成仍然交给 Presentations plugin。
- 生成前必须有用户确认的 brief，不能仅凭模糊请求直接生成。
- 交互式 Codex 会话必须打开确认页并等待用户点击确认；agent 不得后台 POST `/api/confirm` 或写入确认状态来替代用户确认。
- Claude Code / offline fallback 也必须使用同一套内容语言、页数/时长和生成前确认原则；可用 Presentation Director 时先跑 guard，不可用时做等价 chat/static confirmation。
- 用户不应被要求 copy/paste JSON 或命令。
- Logo、学校标志、企业标志、产品 UI、客户 logo 必须有来源或由用户提供，不能伪造。
- AI 生图必须由用户授权，且不能伪造真实人物、真实产品、真实品牌资产。
- 第一版生成不应被过度 design-lock 限制，除非用户明确选择固定风格。

Soft constraints:

- `deck.md` 可以作为内部 handoff 或审计文件，但不是本流程的第一交互界面。
- Intake UI 可以先用本地 HTML + 本地服务实现。
- 如果本地服务不可用，可以退化为 chat-based multiple choice，但这是 fallback。
- Style review 可以先提供文字加 contact sheet 的可视化选择，再逐步升级为真正的 interactive UI。

### 4. 方案评估

#### Option A: 继续用普通 chat prompt 触发 Presentations

Pros:

- 最简单。
- 不需要额外脚本或界面。
- 完全依赖 Presentations plugin 的默认能力。

Cons:

- 用户容易漏掉 audience、goal、logo、image policy 等关键输入。
- 后续修改依赖模糊自然语言反馈。
- 难以系统比较多个视觉版本。

#### Option B: 在生成前强制完整 deck-builder planning

Pros:

- 内容和结构更可控。
- 适合 Claude / fallback 环境。

Cons:

- Codex 下可能限制 Presentations plugin 的表现力。
- 用户要做更多前置工作。
- 过早锁死结构层会降低 contact sheet rhythm 和版式创造性。

#### Option C: Presentation Director

Pros:

- 只收集影响结果质量的关键 brief。
- 用户主要通过点击完成选择。
- 第一版让 Presentations plugin 自由发挥。
- 生成后用 visual options 做二次重绘，而不是模糊反馈。
- 不复制 Presentations plugin 的 renderer 能力。

Cons:

- 需要一个轻量本地 UI / file-signal 机制。
- 需要定义 intake、confirmation、style review、compare 几个页面。

Recommendation: choose Option C for Codex.

### 5. 最小化检查

最小可行版本不需要实现完整产品，只需要：

1. 一份 confirmed brief。
2. 一个生成前 confirmation gate。
3. 一个 research strategy gate，明确使用 Codex 深度联网、外部 Deep Research 资料包、Hybrid，还是仅用用户资料。
4. 一个 visual inspiration gate，在 full PPTX 生成前给出 3 个动态视觉候选。
5. 一个基于 first draft contact sheet 的 style review 页面。
6. 一个 revision request 文件，让 agent 自动读取并调用 Presentations plugin 修改。

不要先做复杂 schema、账号系统、网页发布或独立 PPTX renderer。

### 6. 副作用检查

影响范围：

- Codex 使用流程
- Presentations handoff prompt
- 未来的 `deck-builder` Codex mode
- 可能新增 `scripts/presentation_director.py`
- 可能新增 project-local workspace under `PPTX/<task-slug>/`

风险：

- 如果 intake 问题太多，用户体验会变重。
- 如果 style options 太抽象，用户仍然不知道怎么选。
- 如果自动继续机制不稳定，生成流程会停住。

Mitigation:

- 用 preset 先自动填大部分答案。
- 每个问题都允许 `自定义`。
- 生成前加 brief confirmation gate。
- 本地服务失败时优先修复/重启服务；copy/paste 只能作为明确标记的降级应急，不作为标准流程。

## Product Position

`Presentation Director` is not a PPTX generator.

It is a Codex interaction layer around the Presentations plugin:

```text
User source material
  -> click-based intake
  -> research strategy gate
  -> visual inspiration gate
  -> brief confirmation gate
  -> Presentations plugin v1 generation
  -> style-review UI
  -> revision request
  -> Presentations plugin v2/v3 revision
  -> compare UI
  -> final QA and selected PPTX
```

The key principle:

```text
Before generation: lock intent, sources, audience, constraints, and asset policy.
During generation: let Presentations own composition and visual expression.
After generation: let the user choose visual revision directions from concrete options.
```

## Full Codex Workflow

### Step 0 - User Trigger

User says they want to create a PPTX and provides one or more inputs:

- topic
- pasted text
- article URL
- web page URL
- Google Drive / Docs / Slides / Sheets URL
- PDF
- existing PPTX
- project folder
- README/docs folder
- data file
- reference deck

The agent should recognize this as Codex Presentations work, but route through Presentation Director before starting generation.

### Step 1 - Source Scan and Draft Brief

Agent performs a light source scan:

- identify source files and links
- infer topic
- infer likely audience
- infer likely deck type
- detect whether logo / screenshots / metrics / reference deck are present
- detect missing high-risk assets

Output:

```text
PPTX/<task-slug>/brief-draft.json
```

This draft is not final. It is used to pre-fill the intake UI.

### Step 2 - Click-Based Intake UI

Open:

```text
PPTX/<task-slug>/intake.html
```

The UI should be mostly click-based:

- one recommended option preselected
- 3-5 common options
- always include `自定义`
- optional short free-text field when `自定义` is selected
- source entry accepts one item per line: local folder, local file, web URL, or Google Drive / Docs / Slides / Sheets URL

The user should not answer ten open-ended questions in chat.

Research strategy is part of intake and should be explicit when the user only gave a topic:

| Option | Use When |
|--------|----------|
| Hybrid: External Deep Research + Codex verification | Default for dense research topics such as medicine, policy, industry, finance, or technical trends |
| Codex deep web research | User wants Codex to find, filter, and verify sources directly despite higher time/token cost |
| External Deep Research packet | User will provide Gemini Deep Research, Perplexity Deep Research, or another source package |
| Provided materials only | User wants no web expansion and missing facts should be marked |

### Step 2.5 - Visual Inspiration Gate

After intake, open:

```text
PPTX/<task-slug>/visual-inspiration.html
```

This page should dynamically generate 3 visual candidates from the topic, deck type, audience, and source density. The candidates should borrow from existing UI/deck design assets:

- `design-locks/` for palette, typography, and layout constraints
- `ui-ux-pro-max` for product/style/color/chart/UX reasoning
- HTML deck and UI-generation projects for 3-option preview selection, tokenized theme catalogs, locked visual systems, image slots, and QA discipline

Each candidate must show:

- best-for / avoid-for
- palette
- background strategy
- typography / title style
- layout rhythm
- chart grammar
- image strategy
- inspiration source
- risk

The selected candidate is saved into:

```text
PPTX/<task-slug>/intake-selection.json
```

under `visual_direction.selected_candidate`.

### Step 3 - Brief Confirmation Gate

After the user clicks through intake, do not start PPTX generation yet.

Open:

```text
PPTX/<task-slug>/brief-confirm.html
```

This page summarizes the generation plan in plain language.

It must show:

- selected values
- inferred defaults
- source of each value: `user-selected`, `agent-inferred`, or `default`
- generation risks
- missing assets
- final output assumptions

Buttons:

- `返回修改`
- `确认并开始生成`

Only after the user clicks `确认并开始生成` and the generation guard writes `status/guard-passed.ready` should the agent call the Presentations capability. If the plugin is not visible in the Codex UI, the agent must resolve the bundled runtime before deciding that Presentations is unavailable.

In an interactive Codex session, the agent must not call `POST /api/confirm`, write `brief-confirmed.json`, or touch `confirmed.ready` on behalf of the user unless the user explicitly says to skip confirmation or generate directly. The confirmation click writes `confirmed.ready`; `serve-wait --then-guard` then validates the task and writes `guard-passed.ready`, which is the cross-agent start-generation signal.

Output:

```text
PPTX/<task-slug>/brief-confirmed.json
PPTX/<task-slug>/status/confirmed.ready
PPTX/<task-slug>/status/guard-passed.ready
```

### Step 4 - Generate First PPTX Draft

The agent calls Presentations with:

- confirmed brief
- source material paths / links
- reference deck path if any
- asset policy
- logo policy
- imagegen policy
- content language
- output constraints

Runtime resolution is mandatory for Codex PPTX output:

1. Use the active Codex `Presentations` skill / plugin if it is exposed in the current session.
2. If it is not exposed, resolve the bundled runtime under `$HOME/.codex/plugins/cache/openai-primary-runtime/presentations/*/skills/presentations`.
3. Set `SKILL_DIR` to the resolved directory and run `node "$SKILL_DIR/scripts/check_presentation_runtime.mjs" --workspace "$WORKSPACE"`.
4. For net-new PPTX export, call `node "$SKILL_DIR/scripts/build_artifact_deck.mjs" --workspace "$WORKSPACE" --slides-dir "$SLIDES_DIR" --out "PPTX/<task-slug>/v1/final.pptx" --preview-dir "PPTX/<task-slug>/v1/slides" --layout-dir "$WORKSPACE/layout" --contact-sheet "PPTX/<task-slug>/v1/contact-sheet.png"`.

If neither an active plugin nor the bundled runtime exists, or the runtime check fails, stop and report the missing Codex Presentations runtime. Do not use pptxgenjs, python-pptx, Google Slides, Keynote, PowerPoint automation, QuickLook, or Marp as a substitute unless the user explicitly asks to bypass Codex Presentations.

Important instruction to Presentations:

```text
Content, audience, source boundaries, content language, logo policy, image policy, and output constraints are locked.
Composition, contact-sheet rhythm, hierarchy, chart treatment, and visual expression are delegated to Presentations.
Do not treat design-locks as mandatory unless the user selected one explicitly.
```

Output:

```text
PPTX/<task-slug>/v1/
  final.pptx
  contact-sheet.png
  qa-summary.md
  render-evidence/
```

### Step 5 - Style Review UI

Open:

```text
PPTX/<task-slug>/style-review.html
```

The page shows:

- v1 contact sheet
- PPTX path
- short QA summary
- current visual diagnosis
- visual revision options

The user can choose:

- keep current version
- generate one revised version
- generate multiple comparison variants

The user should click, not copy/paste.

Output:

```text
PPTX/<task-slug>/revision-request.json
PPTX/<task-slug>/status/revision.ready
```

### Step 6 - Generate Revised Versions

The agent reads `revision-request.json` and asks Presentations plugin to revise v1.

Rules:

- preserve confirmed brief
- preserve factual content unless user explicitly changes it
- preserve source and attribution rules
- preserve official logo / asset policy
- apply selected visual direction
- render new contact sheet
- run QA again

Output:

```text
PPTX/<task-slug>/v2/
  final.pptx
  contact-sheet.png
  qa-summary.md

PPTX/<task-slug>/v3/   # optional
  final.pptx
  contact-sheet.png
  qa-summary.md
```

### Step 7 - Compare UI

Open:

```text
PPTX/<task-slug>/compare.html
```

The page shows:

- v1 / v2 / v3 contact sheets
- short description of what changed
- QA status
- file size and slide count
- known risks

Buttons:

- `选择 v1`
- `选择 v2`
- `选择 v3`
- `继续修改`

Output:

```text
PPTX/<task-slug>/final-selection.json
PPTX/<task-slug>/status/final-selected.ready
```

### Step 8 - Final QA and Delivery

The selected PPTX becomes the final deliverable.

Run final checks from `docs/quality-gates.md` and Presentations plugin's own mechanical verification.

Final output:

```text
PPTX/<task-slug>/final/<task-slug>.pptx
PPTX/<task-slug>/final/<task-slug>-companion.html
PPTX/<task-slug>/final/final-report.md
```

The final report should include:

- selected version
- final PPTX absolute path
- final HTML companion absolute path
- contact sheet path
- QA evidence
- remaining risks

## Intake UI Questions

### Question 1 - Deck Type Preset

This should be the first question because it pre-fills many later defaults.

Prompt:

```text
你要做哪类 PPT?
```

Options:

1. 项目汇报
2. 工程 / 技术方案介绍
3. 投资人 / 路演 deck
4. 学术 / 课程 / 知识讲解
5. 客户销售 / 产品介绍
6. 自定义

Preset behavior:

| Preset | Default Audience | Default Goal | Default Proof Objects | Default Visual Intent |
|--------|------------------|--------------|------------------------|-----------------------|
| 项目汇报 | 老板 / 团队 / 评审 | 说明进展和下一步 | roadmap, metric, status, risk | clear executive report |
| 工程 / 技术方案 | 技术负责人 / 产品负责人 | 解释系统价值和实现方式 | architecture, data flow, tradeoff, metric | engineering-platform |
| 投资人 / 路演 | 投资人 / 评委 | 说服对方相信增长潜力 | market, traction, business model, roadmap | high-polish investor |
| 学术 / 课程 | 学生 / 老师 / 研究者 | 讲清知识结构 | framework, timeline, examples, citations | explanatory editorial |
| 客户销售 | 客户 / 合作方 | 促成理解和转化 | pain point, solution, demo, proof | product-led polished |

### Question 2 - Audience

Prompt:

```text
这份 PPT 主要给谁看?
```

Options:

1. 高层 / 老板 / 决策者
2. 投资人 / 评委 / 路演对象
3. 技术团队 / 工程评审
4. 客户 / 销售对象
5. 学生 / 老师 / 研究者
6. 自定义

### Question 3 - Goal

Prompt:

```text
这份 PPT 的主要目标是什么?
```

Options:

1. 让对方快速理解一个主题
2. 说服对方做决定
3. 汇报进展、成果和风险
4. 教学讲解 / 知识传达
5. 展示产品 / 项目价值
6. 自定义

### Question 4 - Source Boundary

Prompt:

```text
资料应该怎么使用?
```

Options:

1. 严格只用我提供的材料
2. 可以联网补充，但必须标注来源
3. 以已有 PPT / 文档为内容基础
4. 以参考 deck 作为质量和风格标杆
5. 自定义

### Question 5 - Content Language

Prompt:

```text
PPT 正文使用什么语言?
```

Options:

1. 中文
2. English
3. Deutsch
4. Français
5. Italiano
6. Español
7. 双语
8. 自定义

### Question 6 - Output Constraints

Prompt:

```text
页数和演讲时长限制是什么?
```

Options:

1. 8-10 页
2. 10-12 页
3. 15-20 页
4. 自定义时长和页数

### Question 7 - Logo and Brand Assets

Prompt:

```text
Logo 和品牌素材怎么处理?
```

Options:

1. 不使用 logo
2. 只使用我提供的 logo / 图片
3. 可以查找官方 logo 和官方素材
4. 只在封面和结束页使用 logo
5. 自定义

Hard rule:

```text
Never fabricate logos, school marks, company marks, product UI, customer logos, or official-looking brand assets.
```

### Question 7 - Image Generation Policy

Prompt:

```text
是否允许使用 AI 生图?
```

Options:

1. 不使用 AI 生成图片
2. 只允许生成抽象背景 / 概念图
3. 允许生成封面和章节图
4. 每次生图前先问我
5. 自定义

Hard rule:

```text
AI images may support atmosphere or abstraction. They must not fake real products, people, screenshots, logos, or official assets.
```

### Question 8 - First Draft Visual Freedom

Prompt:

```text
第一版视觉方向怎么处理?
```

Options:

1. 交给 Presentations 自由发挥
2. 更正式克制
3. 更科技 / 工程感
4. 更投资人路演 / 高对比
5. 更学术 / 编辑风
6. 自定义

Default:

```text
交给 Presentations 自由发挥
```

### Question 9 - Reference Deck

Prompt:

```text
是否有参考 deck 或风格样张?
```

Options:

1. 没有参考，按内容生成
2. 有参考，但只作为质量标杆
3. 有参考，需要接近其视觉风格
4. 有已有 PPT，需要在它基础上改
5. 自定义

## Brief Confirmation Gate

The confirmation page is mandatory.

It should convert all selections into a readable generation brief:

```text
你即将生成的 PPTX

主题:
<title / inferred topic>

资料来源:
- <source 1>
- <source 2>

听众:
<audience>
来源: user-selected / inferred / default

目标:
<goal>
来源: user-selected / inferred / default

输出:
<language, page count, duration, format>

内容边界:
<source boundary>

资料研究策略:
<Codex deep web / external Deep Research packet / hybrid / provided-only>

Logo / 品牌:
<logo policy>

AI 图片:
<image policy>

第一版视觉方向:
<selected visual candidate: palette, background, layout rhythm, chart grammar, image strategy>

生成策略:
先生成 v1 PPTX 和 contact sheet，然后打开 style-review.html 供选择是否重绘。
```

### Risk Summary

The confirmation page should show risks before generation:

```text
生成前风险:
- 未提供官方 logo 文件
- 未提供明确量化指标
- 没有产品截图
- 参考 deck 未提供
- 用户禁止联网，部分数据无法验证
```

Risk summary is not a blocker unless it violates a hard rule. It sets expectations.

## Style Review UI

After v1 is generated, the review page should not ask vague questions.

It should show concrete revision families.

### Section 1 - Current Version

Show:

- contact sheet
- output PPTX path
- slide count
- QA summary
- current visual diagnosis

Example diagnosis:

```text
当前版本: editorial analytics style, restrained palette, strong whitespace.
Potential issue: architecture slide could be more explicit; logo presence is low.
```

### Section 2 - Palette Direction

Prompt:

```text
是否要改变配色方向?
```

Options:

1. 保持当前
2. 暖色纸感 / 编辑风
3. 工程蓝灰 / 技术风
4. 高对比 / 路演风
5. 强化品牌色
6. 自定义

### Section 3 - Structure and Rhythm

Prompt:

```text
是否要改变结构节奏?
```

Options:

1. 保持当前
2. 更强故事节奏
3. 更数据分析
4. 更架构 / 系统图
5. 更产品发布 / demo 感
6. 更高密度内部汇报
7. 自定义

### Section 4 - Visual Expression

Prompt:

```text
是否要改变视觉表现力?
```

Options:

1. 保持当前
2. 更高级 / 更有设计感
3. 更克制 / 更少装饰
4. 更少卡片，更开放构图
5. 更强图表和 evidence-led storytelling
6. 自定义

### Section 5 - Image Strategy

Prompt:

```text
图片和视觉素材怎么调整?
```

Options:

1. 保持当前
2. 减少装饰图
3. 增加 AI 概念图
4. 只用真实截图 / 官方素材
5. 增强封面或章节视觉
6. 自定义

### Section 6 - Logo / Brand Presence

Prompt:

```text
Logo 和品牌露出怎么调整?
```

Options:

1. 保持当前
2. 只保留封面和结束页
3. 增强页脚品牌感
4. 增加合作方 / 学校 / 企业 logo 页
5. 移除所有 logo
6. 自定义

### Action Buttons

Buttons:

- `保持 v1，进入最终 QA`
- `生成一个对比版本`
- `生成两个对比版本`
- `返回修改选择`

No copy/paste should be required.

## Compare UI

After revisions are generated, show:

```text
版本对比

v1 original
- contact sheet
- style summary
- QA summary
- known risks

v2 warm editorial
- contact sheet
- changed palette and rhythm
- QA summary
- known risks

v3 engineering analytic
- contact sheet
- stronger diagrams and data layouts
- QA summary
- known risks
```

Buttons:

- `选择 v1`
- `选择 v2`
- `选择 v3`
- `继续修改`

The selected version is copied or exported to:

```text
PPTX/<task-slug>/final/<task-slug>.pptx
```

## No-Copy Interaction Mechanism

Primary mechanism:

```text
local server + file signals
```

Proposed script:

```text
scripts/presentation_director.py
```

Possible commands:

```bash
python3 scripts/presentation_director.py init --task "<task-slug>" --source "<path-or-url>" --conversation-text "<recent user prompt>"
python3 scripts/presentation_director.py serve --task "<task-slug>"
python3 scripts/presentation_director.py open-page --task "<task-slug>" --page confirm
python3 scripts/presentation_director.py render --task "<task-slug>" --open-page style-review
python3 scripts/presentation_director.py render --task "<task-slug>" --open-page compare
python3 scripts/presentation_director.py wait --task "<task-slug>" --for confirmed
python3 scripts/presentation_director.py wait --task "<task-slug>" --for revision
python3 scripts/presentation_director.py wait --task "<task-slug>" --for final-selection
python3 scripts/presentation_director.py prompt --task "<task-slug>" --kind initial
python3 scripts/presentation_director.py prompt --task "<task-slug>" --kind revision
python3 scripts/presentation_director.py share-html --task "<task-slug>" --version "<selected-version>"
```

`ui_language` controls the Director HTML gate communication language (`intake`, `visual-inspiration`, `confirm`, `style-review`, and `compare`) and defaults to auto-detection from `--conversation-text`; `content_language` remains the generated deck's body-copy language.

Possible endpoints:

| Endpoint | Purpose |
|----------|---------|
| `GET /intake` | show click-based intake |
| `POST /api/intake` | save intake selections |
| `GET /visual-inspiration` | show 3 dynamic visual direction candidates |
| `POST /api/visual-inspiration` | save selected visual direction |
| `GET /confirm` | show brief confirmation |
| `POST /api/confirm` | save confirmed brief and signal ready only when the confirmation form token is submitted |
| `GET /style-review` | show v1 contact sheet and revision options |
| `POST /api/revision` | save revision request and signal ready |
| `GET /compare` | show version comparison |
| `POST /api/final-selection` | save final selected version |

File signals:

```text
PPTX/<task-slug>/status/confirmed.ready
PPTX/<task-slug>/status/guard-passed.ready
PPTX/<task-slug>/status/revision.ready
PPTX/<task-slug>/status/final-selected.ready
```

The agent waits for these signals and continues automatically. In interactive Codex sessions, prefer:

```bash
python3 scripts/presentation_director.py serve-wait --task "<task-slug>" --for confirmed --then-guard
```

Start generation only after `status/guard-passed.ready` exists or `GUARD_PASSED` is visible in flushed output.

The user should only click in the HTML UI. Do not ask the user to copy/paste anything or return to chat to say "confirmed".

Fallback mechanism:

If local server is unavailable:

1. Render static HTML.
2. Fix or restart the local server and resume file-signal waiting.
3. Only if the server cannot run at all, use a clearly marked degraded chat confirmation.

This fallback should be clearly marked as less convenient.

## Workspace Layout

Recommended structure:

```text
PPTX/<task-slug>/
  sources/
  brief/
  brief-draft.json
  intake.html
  intake-selection.json
  visual-inspiration.html
  brief-confirm.html
  brief-confirmed.json
  style-review.html
  revision-request.json
  compare.html
  final-selection.json
  final-report.md
  status/
    confirmed.ready
    guard-passed.ready
    revision.ready
    final-selected.ready
  v1/
    final.pptx
    slides/
      slide-001.png
      slide-002.png
    contact-sheet.png
    qa-summary.md
  v2/
    final.pptx
    slides/
    contact-sheet.png
    qa-summary.md
  v3/
    final.pptx
    slides/
    contact-sheet.png
    qa-summary.md
  final/
    <task-slug>.pptx
    <task-slug>.html       # Reveal.js deck for html-revealjs or both
    <task-slug>-companion.html  # PPTX-only companion
    final-report.md
```

Codex Presentations may still use its required internal scratch workspace under `outputs/<thread-id>/presentations/...`. The user-facing brief, versions, per-slide preview images, contact sheets, QA summaries, comparisons, final PPTX, and final HTML companion must be saved or copied into `PPTX/<task-slug>/`.

## Brief JSON Shape

Minimal shape:

```json
{
  "version": "0.1",
  "task_slug": "project-introduction",
  "topic": "MD2PPT project introduction",
  "sources": [
    {
      "path": "/absolute/path/or/url",
      "priority": "primary",
      "type": "folder"
    }
  ],
  "deck_type": {
    "value": "engineering-platform",
    "source": "user-selected"
  },
  "audience": {
    "value": "technical leaders and product owners",
    "source": "user-selected"
  },
  "goal": {
    "value": "explain project value and implementation path",
    "source": "user-selected"
  },
  "research_strategy": {
    "value": "hybrid-deep-research",
    "source": "user-selected",
    "meaning": "Use an external Deep Research packet when available, then let Codex verify key facts and sources."
  },
  "output": {
    "format": "pptx",
    "language": "zh",
    "page_count": "10-12",
    "duration_minutes": "10-15"
  },
  "source_boundary": {
    "policy": "provided-materials-only",
    "web_allowed": false
  },
  "logo_policy": {
    "usage": "cover-and-final-only",
    "source": "user-provided-only"
  },
  "image_policy": {
    "ai_images": "ask-before-use",
    "allowed": ["abstract-background", "section-art"]
  },
  "visual_direction": {
    "selected_candidate": {
      "key": "signal-system",
      "name": "Signal System",
      "palette": ["#f8fafc", "#111827", "#0061ff", "#16a34a"],
      "background": "light engineering grid with restrained signal lines",
      "layout": "architecture diagrams, data flows, metric dashboards",
      "chart": "latency charts, dependency maps, before/after bars",
      "image_strategy": "use real screenshots first; beautify but do not redraw facts"
    },
    "avoid": ["generic SaaS card grid", "fake logos", "unverified metrics"]
  },
  "risks": [
    "No official logo file provided",
    "No quantitative metrics found"
  ],
  "confirmed": true
}
```

## Revision Request JSON Shape

Minimal shape:

```json
{
  "version": "0.1",
  "base_version": "v1",
  "revision_count": 1,
  "palette_direction": "warm-editorial",
  "structure_direction": "more-analytical",
  "visual_expression": "more-premium-less-cards",
  "image_strategy": "keep-current",
  "logo_strategy": "cover-and-final-only",
  "preserve": [
    "slide claims",
    "source attribution",
    "logo policy",
    "no fabricated metrics"
  ],
  "notes": ""
}
```

## Presentations Handoff Prompt Pattern

The agent should pass a clear handoff to Presentations:

```text
Use the Codex Presentations skill and artifact-tool presentation JSX.
If the plugin is not visible in the Codex UI, resolve bundled runtime at:
$HOME/.codex/plugins/cache/openai-primary-runtime/presentations/*/skills/presentations
Set SKILL_DIR to that directory.

Confirmed brief:
<brief-confirmed.json summary>

Source material:
<resolved paths and links>

Rules:
- Audience, goal, source boundary, content language, logo policy, image policy, and output constraints are locked.
- Do not fabricate metrics, logos, customer names, or screenshots.
- Use official or user-provided brand assets only.
- AI images are allowed only according to the confirmed image policy.
- Composition, layout rhythm, chart treatment, typography hierarchy, and visual expression are delegated to Presentations.
- Do not use a fixed design-lock unless the confirmed brief explicitly asks for it.

Output:
- Use the Presentations internal scratch workspace as required by the plugin/runtime.
- Before building, run `node "$SKILL_DIR/scripts/check_presentation_runtime.mjs" --workspace "$WORKSPACE"` and keep the result in QA notes.
- For net-new PPTX export, the final PPTX must be produced by `node "$SKILL_DIR/scripts/build_artifact_deck.mjs" --workspace "$WORKSPACE" --slides-dir "$SLIDES_DIR" --out "PPTX/<task-slug>/v1/final.pptx" --preview-dir "PPTX/<task-slug>/v1/slides" --layout-dir "$WORKSPACE/layout" --contact-sheet "PPTX/<task-slug>/v1/contact-sheet.png"`.
- Copy editable PPTX to `PPTX/<task-slug>/v1/final.pptx`.
- Copy per-slide preview PNGs to `PPTX/<task-slug>/v1/slides/`.
- Copy contact sheet and concise QA summary to `PPTX/<task-slug>/v1/`.
- Generate layout JSON in the Presentations workspace.
- Complete at least one fix-and-rerender cycle.
- Generate a view-only HTML companion at `PPTX/<task-slug>/final/<task-slug>-companion.html` after final selection for PPTX-only output.
- Return PPTX path, HTML companion path, contact sheet path, QA summary, and remaining risks.
```

## Revision Handoff Prompt Pattern

```text
Revise the existing v1 PPTX using the selected revision request.

Base version:
<v1 final.pptx path>

Revision request:
<revision-request.json summary>

Preserve:
- factual content
- slide claims
- sources and omission notes
- official asset policy
- imagegen policy

Change:
- palette direction
- structure rhythm
- visual expression
- image/logo treatment only as selected

Render and QA:
- use the Presentations internal scratch workspace as required by the plugin
- copy revised PPTX to `PPTX/<task-slug>/v2/final.pptx` or `PPTX/<task-slug>/v3/final.pptx`
- copy per-slide preview PNGs to the version's `slides/` folder
- copy contact sheet and concise QA summary to the same version folder
- compare against v1
- regenerate the view-only HTML companion from the selected version's per-slide previews after final selection
- document what changed and any remaining risks
```

## Guardrails

Do:

- Ask via UI, not long chat interrogation.
- Preselect sensible defaults.
- Always allow `自定义`.
- Show confirmation before generation.
- Show risks before generation.
- Preserve versions for comparison.
- Use Presentations for actual PPTX generation.

Do not:

- Start generation immediately after intake selection without confirmation.
- Ask the user to copy/paste JSON or reply "confirmed" in chat in the primary flow.
- Lock design structure before first draft unless the user explicitly asks.
- Treat intake, style-review, compare, or other preview HTML as the final share HTML companion or final HTML deck.
- Fabricate logos, official marks, screenshots, product UI, customer marks, or metrics.
- Use AI-generated images without the confirmed policy.

## Implementation Phases

### Phase 1 - Documentation and Prompt Upgrade

Work:

- Keep this workflow as the Codex mode reference.
- Add a Codex Presentation Director prompt template.
- Clarify that Codex mode uses lighter pre-planning than Claude/fallback mode.

Done when:

- Agent can manually follow the workflow without scripts.

### Phase 2 - Static Intake and Confirmation Pages

Work:

- Generate `intake.html` and `brief-confirm.html`.
- For now, user may still respond in chat after reviewing the page.

Done when:

- The questions and confirmation structure are validated with real use.

### Phase 3 - Local Server and No-Copy Flow

Work:

- Implement `scripts/presentation_director.py`.
- Add local server endpoints.
- Add `serve-wait` so the agent opens HTML, waits for the file signal, and continues automatically after the click.
- Write `brief-confirmed.json` and status files only after the user submits the confirmation form.

Done when:

- User can confirm intake by clicking, and Codex continues without copy/paste or chat replies.

### Phase 4 - Style Review and Compare UI

Work:

- Generate `style-review.html` after v1.
- Generate `revision-request.json` by button click.
- Generate `compare.html` after v2/v3.

Done when:

- User can select visual revisions and final version by clicking.

## Claude / Offline Parity

Claude Code and other local/offline agents use different renderers, but they must not bypass the upstream decision gates for net-new PPTX work.

Required parity:

- Use the same separate fields: `content_language` and `output_constraints`.
- Confirm audience, goal, source boundary, research strategy, visual direction, language, and page/time range before generation.
- If Presentation Director exists in the workspace, run `presentation_director.py guard --task "<task-slug>"` before pptxgenjs or HTML generation.
- If the Director helper is unavailable, present the equivalent plan in chat or static HTML and stop until the user explicitly confirms.
- Do not treat a generic "continue" after source upload as confirmation of language, page count, structure, and visual direction unless the user explicitly says to skip the gate or generate directly.

Hook adapters:

- `scripts/hooks/presentation-director-guard.sh` validates an existing task before generation.
- `scripts/hooks/claude-presentation-director-prompt.py` can be registered as a Claude `UserPromptSubmit` hook to inject this workflow when a PPT/deck prompt is detected.

### Phase 5 - Real Deck Trials

Run at least three real cases:

1. Article / knowledge deck
2. Engineering project deck
3. Product or pitch deck

Measure:

- number of user chat turns
- first draft quality
- number of revisions
- whether style-review options were useful
- whether users needed custom text anyway

## Open Questions

1. Should the intake UI be a generated static page first, or a small persistent local app?
2. Should style-review variants be generated as mock preview cards before asking Presentations to redraw, or should they be descriptive options only?
3. Should version comparison include rendered full-size previews per slide, or contact sheets are enough for v1?
4. Should `deck.md` be generated after confirmed brief as an audit artifact, or skipped in Codex mode unless requested?
5. Should this become a separate skill, or a Codex-specific mode inside `deck-builder`?

## Recommended Next Step

The local server prototype now exists. Next, test it with one real PPTX task:

```text
1. Create a brief-draft from user sources.
2. Present intake choices in chat or a static HTML page.
3. Show a confirmation summary.
4. Generate v1 with Presentations.
5. Show a style-review option list.
6. Generate one revised version.
7. Compare v1 and v2.
```

If this reduces friction and improves output quality, promote the prototype into the default Codex mode for `deck-builder`.
