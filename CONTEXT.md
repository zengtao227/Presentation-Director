# Presentation Director 项目上下文

## 项目定位

Presentation Director 是一个把主题、文章、知识文稿、书籍摘要或工程项目资料转成高质量演示文稿的工作流仓库。仓库早期名为 MD2PPT；以后统一用 Presentation Director 指代这个项目和流程。

当前首选目标不是“快速导出一份能放映的幻灯片”，而是生成：

- 内容逻辑清晰
- 设计语言统一
- 可在 PowerPoint 中继续编辑
- 有渲染预览和 QA 证据的 `.pptx`

同时，`deck-builder` 已把 Reveal.js HTML deck 纳入 first-class 输出路径：当用户需要浏览器演示、动画过渡、presenter mode 或 `?print-pdf` 导出时，可以选择 `output_format = "html-revealjs"`；当需要可编辑交付时选择 `pptx`；需要两者时选择 `both`。

## 主要术语

### Source Material

原始材料。可以是一个主题、一篇文章、一本书的章节、访谈稿、产品文档、代码仓库、工程项目说明、数据表、已有 PPTX、本地文件夹、本地文件、普通网页 URL 或 Google Drive / Docs / Slides / Sheets 地址。

### PPTX Slide Planner

从原始材料到 `deck.md` 之间的规划层。它不负责画幻灯片，也不直接生成 `.pptx`，而是输出每一页的演示蓝图：

- 这份 deck 给谁看
- 要推动什么决定或理解
- 整体 thesis 和叙事弧线
- 每页的 claim
- 每页的 proof object
- 每页适合的 layout family
- 需要的数据、截图、图表、架构图或引用
- 缺失信息和不可编造项

### deck.md

最终交给生成层的内容源。它应该包含 thesis、audience、slide list、claim、proof object、source 和 omission notes，不应该混入大量样式代码。

### Design Intelligence

由 `skills/ui-ux-pro-max` 生成的设计情报。新版优先使用 `--design-system` 聚合输出，再按需补查 `style`、`typography`、`google-fonts`、`color`、`chart`、`ux`。

### Visual Contract

由 `design-locks/` 提供的视觉合同。它把 Open Design 风格落成可执行约束：颜色、字体、字号层级、版式语法、禁用项和页码/脚注规则。

### Codex Presentations

Codex 中生成专业可编辑 PPTX 的主路径。它应使用 artifact-tool `presentation-jsx`，并执行 claim spine、design system、contact-sheet plan、render QA、导出 PPTX。

在 Codex Desktop 中，`Presentations` 可能不会出现在插件列表或插件搜索 UI 里。不要仅凭 UI 不可见判断缺失；应先检查当前 session 是否暴露了 Presentations skill / plugin，然后检查 Codex primary runtime bundled 路径：

```text
$HOME/.codex/plugins/cache/openai-primary-runtime/presentations/*/skills/presentations
```

只要该 bundled runtime 存在，就视为 Codex Presentations 可用。PPTX 生成必须设置 `SKILL_DIR` 指向该目录，先运行 `scripts/check_presentation_runtime.mjs` 验证 `@oai/artifact-tool/presentation-jsx` 和 `PresentationFile.exportPptx` 可用，再通过 `scripts/build_artifact_deck.mjs` 完成 net-new PPTX 的最终导出、预览 PNG、layout JSON 和 contact sheet。插件 UI 不可见不是降级到 pptxgenjs、python-pptx、Google Slides、Keynote 或 PowerPoint 自动化的理由。

### Presentation Director

Codex 环境下创建全新演示文稿前的交互增强层。它不直接生成 PPTX 或 HTML，而是先用点击式 intake 收集输出格式、听众、目标、资料路径或网页地址、资料研究策略、资料边界、内容语言、logo/品牌素材、AI 生图许可、页数/时长限制和视觉方向，再通过 brief confirmation gate 让用户确认，之后才按 `output_format` 路由到 Reveal.js HTML 直写、Codex Presentations 或两者并行。

Director 的沟通界面语言和 PPT 正文语言是两个不同概念：`ui_language` 默认根据当前对话文本自动检测，用于 intake、visual-inspiration、confirm、style-review、compare 等 HTML gate 页面和按钮文案；`content_language` 用于控制 PPT 正文、标题和讲稿语言。运行 `init` 时应传入最近用户请求作为 `--conversation-text`，让自动打开的 HTML 页面跟随用户对话语言。

Director 交互页应自动打开，不要让用户复制本地 URL、粘贴 JSON、或回到聊天里回复“已确认”。交互式流程应优先使用 `serve-wait --for confirmed`：用户点“下一步”后进入 `visual-inspiration`，再进入确认页；点击确认后写入状态文件，agent 自动继续生成。批处理或后台运行可显式传 `--no-open`，但仍应通过状态文件恢复，而不是通过聊天确认。

Codex 交互式全新 PPTX 请求必须打开确认页并自动等待用户在 HTML 中点击确认；agent 不得要求用户复制/粘贴、不得要求用户回聊天里回复“已确认”，也不得自己 POST `/api/confirm`、直接写入 `brief-confirmed.json` 或 `confirmed.ready` 来代替用户确认。只有用户明确说“跳过确认/直接生成/不用等我确认”时，才允许后台确认。`style-review` 和 `compare` 也应使用 HTML 点击 + 状态文件恢复；可用 `presentation_director.py open-page` 或 `render --open-page ...` 打开页面。

### Research Strategy Gate

当用户只给主题、没有给可直接使用的资料包时，不要马上开始 PPTX 生成。Presentation Director 应先让用户选择研究资料策略：

- `Hybrid`: 外部 Deep Research 资料包加 Codex 定点核验。适合医学、药物研发、政策、产业研究、技术趋势等资料密集主题，默认推荐。
- `Codex web deep research`: 由 Codex 深入联网检索、筛选和核验资料，质量高但更耗时和耗 token。
- `External Deep Research packet`: 用户先用 Gemini Deep Research、Perplexity Deep Research 等生成研究报告和来源列表，再交给 Codex 做二次筛选、结构化、关键事实核验和 PPTX 规划。
- `Provided materials only`: 严格只用用户提供资料，缺失信息必须标注。

研究策略和 `output_format` 必须写入 `brief-confirmed.json`，并在 handoff prompt 中作为内容边界的一部分。

### Visual Inspiration Gate

在 brief confirmation 之前，Presentation Director 应根据主题、听众、PPT 类型和资料密度动态生成 3 个视觉方向候选。候选不应写死为某个领域，而应从已有设计资产中抽取适配方向：

- `design-locks/`：稳定的颜色、字体、版式约束。
- `ui-ux-pro-max`：行业/场景匹配、配色、字体、图表和 UX 风险。
- HTML deck / UI 生成项目经验：3 候选预览、theme/layout catalog、locked visual system、图片槽位和 QA 规则。

每个候选至少说明适用场景、不适用场景、色板、背景策略、标题/字体风格、图表语法、图片策略、借鉴来源和风险。当 `output_format` 为 `"html-revealjs"` 或 `"both"` 时，候选还应显示 Reveal.js 的 `html_transition`、`html_animation` 和 `html_gradient`。用户选定后，再进入 brief confirmation 和按格式路由生成。

对于 Codex 里的 net-new PPTX 请求，默认路径必须先走 Presentation Director，不应直接调用 Presentations 生成。只有以下情况可以跳过：

- 用户明确要求跳过 intake / director
- 已经存在用户确认过的 `brief-confirmed.json`
- 任务是现有 PPTX 的小改、QA 或 targeted edit

### PPTX Workspace

在任何项目中生成 PPT 时，用户可见的所有相关文件都应集中放到项目内 `PPTX/<task-slug>/`，不要散落在根目录、`assets/` 或多个临时目录里。推荐结构：

```text
PPTX/<task-slug>/
  brief/
    draft-brief.json
    visual-contract.md
  sources/
  intake.html
  image-style.html
  image-placement.html
  brief-confirm.html
  brief-confirmed.json
  image-plan.json
  image-assets.json
  image-placement-request.json
  style-review.html
  revision-request.json
  compare.html
  final-selection.json
  v1/
    final.pptx
    final.html              # if output_format is html-revealjs or both
    slides/
      slide-001.png
      slide-002.png
    contact-sheet.png
    qa-summary.md
  v2/
    final.pptx
    final.html
    slides/
    contact-sheet.png
    qa-summary.md
  final/
    <task-slug>.pptx
    <task-slug>.html        # Reveal.js deck when output_format is html-revealjs or both
    <task-slug>-companion.html  # PPTX-only view-only companion
    final-report.md
```

Codex Presentations 插件内部可能仍按插件规则使用 `outputs/<thread-id>/presentations/...` 作为 scratch workspace；但交给用户看的 brief、版本、逐页预览图、contact sheet、QA 摘要、最终 PPTX 和最终 HTML 分享版必须复制或保存到 `PPTX/<task-slug>/`。

`brief-confirmed.json` 必须包含：

```text
output_format: "html-revealjs" | "pptx" | "both"
```

已确认 brief 中的 `output_format` 是生成路由的真实来源。确认之后如果用户在聊天中改口要求 HTML ↔ PPTX ↔ both，不得直接沿用旧 brief 生成另一种格式；必须重新打开确认页更新 brief，或得到用户明确的“跳过确认/直接改成 <format>”指令，并在最终报告里记录该覆盖来源。

### Layout QA / Safe Area / No Overlap Gate

任何 PPTX 生成或 targeted edit 都必须通过渲染级排版检查，而不是只通过代码、XML 或包结构检查：

- 必须生成逐页预览图和 contact sheet，并把它们放入对应版本目录。
- 必须定义并检查安全区。默认 1280×720 画布使用 `x=54, y=70, width=1172, height=590` 作为内容安全区；标题、正文、截图、图表、表格、代码块、说明文字等关键内容必须在安全区内。背景、网格和装饰性 bleed 可以延伸到页面边缘，但不得裁切或遮挡关键内容。
- 必须检查标题、副标题、正文、页脚、页码、图表标签、连接线和卡片之间是否互相重叠或裁切。
- 长标题必须预留换行高度；标题换行后不得压住副标题、小字说明或页面主体。
- 发现重叠后必须修复并重新渲染受影响页面；QA summary 中要写明修复前问题、修复动作和复检结果。
- 没有渲染证据、安全区检查和 no-overlap 检查结果时，不得把 PPTX 标记为完成。

### HTML Deck（Reveal.js 主输出）

当 `output_format` 为 `"html-revealjs"` 或 `"both"` 时，以 Reveal.js 5.1.0 生成完整可演示的 HTML 文件作为主输出（或与 PPTX 并行的输出）。

这不同于每个 PPTX 附带的只读 HTML Companion；HTML Deck 是功能完整的演示引擎：

- 支持动画过渡（slide / fade / zoom / convex）
- 支持 CSS 渐变背景（PPTX 不可用）
- 支持 auto-animate（元素平滑变形）
- 支持 presenter mode（按 S 键）
- 支持 `?print-pdf` 导出
- 输出为单 `.html` 文件，浏览器打开即用，无需安装

生成层：Claude/Codex 直接写 Reveal.js HTML。不要调用 Codex Presentations plugin，不依赖 `html-ppt-skill` 或 `guizang-ppt-skill`。

输出路径：每个候选版本先写入 `PPTX/<task-slug>/vN/final.html`；用户最终选择后，复制到 `PPTX/<task-slug>/final/<task-slug>.html`。

### HTML Companion

最终 `.pptx` 的只读分享版。它由最终版本的逐页渲染图生成，PPTX-only 输出时保存为 `PPTX/<task-slug>/final/<task-slug>-companion.html`，方便浏览器打开或简单分享。它不是编辑源，也不是 HTML deck 引擎的替代品；如果 PPTX 内容被修改，应从修改后的 PPTX 或重新渲染的逐页预览图再生成一次 HTML companion。`output_format="both"` 时，`final/<task-slug>.html` 是 Reveal.js Deck，不再单独生成 companion。

### AI Image Gates

`image_policy` 保持现有 intake 权限枚举：`none`、`abstract-only`、`cover-section`、`ask-before-use`、`custom`。执行层另由 Image Style Gate 写入 `image_generation_mode`：`none`、`global-background`、`cover-section-auto`、`post-v1-slot-review`、`hybrid`。

新 brief 必须先经过 `serve-wait --open-page image-style --for images-style`；旧 brief 如果没有 `image_generation_mode`，`guard` 会跳过图片门禁以保持兼容。pre-v1 生图必须写 `image-plan.json` 和 `image-assets.json`，其中 `final_status: "success"` 只能在输出图片文件存在且非空后写入；失败按 retry-2-then-stop 处理，不能静默降级成 CSS 渐变或 SVG 占位。`post-v1-slot-review` 和 `hybrid` 在 v1 preview artifact 就绪后，再通过 `serve-wait --open-page image-placement --for images-placement` 写 `image-placement-request.json`，然后生成 v2。

### HTML Theme & Motion

Image Style Gate 完成后，`brief-confirmed.json` 的 `html_config` 对象包含以下字段（仅 `html-revealjs` 和 `both` 格式有效；PPTX 路径忽略这些字段）：

| 字段 | 说明 |
|---|---|
| `theme_key` | 选定的 HTML 主题（如 `aurora`、`blueprint`、`academic-paper`）；用户可在 Image Style Gate 手动选，否则由 Visual Direction 候选自动推断 |
| `motion_level` | 动效强度：`subtle`（仅 fade/rise-in）、`expressive`（加 zoom-pop/counter-up）、`cinematic`（封面/章节/结束页可用 spotlight/kenburns，CSS-only） |
| `motion_profile` | 风格家族：`pitch`、`tech`、`editorial`、`product`、`presenter` |
| `layout_families` | 推荐布局序列（来自 html-layout-catalog.md），如 `["cover-hero","architecture-map","flow-diagram","code-terminal","timeline"]` |
| `transition` | Reveal.js 页面切换效果（`fade`/`slide`/`zoom`/`convex`）|
| `effects_runtime` | 固定为 `css-only`；Canvas/WebGL 为未来能力 |

生成 HTML 时必须遵守：
- 用 CSS `:root` 变量实现主题 token（`--deck-bg`、`--deck-ink`、`--deck-accent`、`--deck-muted`）
- 所有文字/图表/表格放在 `.slide-safe`（left:54px; top:70px; width:1172px; height:590px）
- AI 背景图用 `.bleed`（position:absolute; inset:0）
- 加载 Reveal.js Notes plugin；每页有 `<aside class="notes">`
- 数据幻灯片使用 Chart.js 4.x，直接数据标签，不用图例

pre-v1 图片生成使用 `skills/deck-builder/scripts/generate_images.py`（支持 `--api stub/dall-e-3/flux`）。

### PPTX Editability

最终 `.pptx` 是主要可编辑交付物。小改不需要重新生成整套 deck：文字替换、元素左右移动、颜色微调、替换图片、添加少量图片或图表，都应优先作为 PowerPoint 手工编辑或 Codex `Presentations` targeted-edit 处理。为了保留可回退历史，agent 修改现有 PPTX 时应复制成新版本，例如 `PPTX/<task-slug>/v2/final.pptx`，再重新生成 HTML companion。

如果某个元素被做成了截图或整页图片，它只能整体移动/裁剪，不能编辑内部文字、连接线或数据。需要可细编辑时，应要求 agent 把该页重建为原生文本框、形状、连接器、表格或图表。

### Fallback PPTX Path

本地 `skills/pptx` + pptxgenjs 路径。只用于 Claude Code、本地离线代理，或用户在 Codex 中明确要求绕过 `Presentations` 插件的特殊情况。

在 Codex 环境中，只要 `output_format` 是 `"pptx"` 或 `"both"`，就必须使用 Codex `Presentations` 能力 / `artifact-tool presentation-jsx` 生成 PPTX。可用性判断顺序是：当前 session 暴露的 Presentations skill / plugin → Codex primary runtime bundled Presentations path。只有两者都不存在，或 `scripts/check_presentation_runtime.mjs` 验证失败，agent 才能停止并说明“缺少 Codex Presentations runtime”。不得因为插件 UI 不显示就自动改用 `python-pptx`、pptxgenjs、Google Slides、Keynote、Microsoft PowerPoint 自动化或 QuickLook 等 fallback 路径。

Claude Code / 本地代理也要遵守同一套前置确认原则：内容语言和页数/时长分开收集；如果本地可用 Presentation Director helper，应先跑 intake / confirmation 并通过 `guard` 后再用 pptxgenjs 或 HTML 工具生成；如果 helper 不可用，必须在聊天或静态 HTML 中做等价确认，不能直接生成全新 deck。

### 工作流优先级

1. Codex `Presentations`：全新、可编辑、可验证 PPTX 的首选。
2. Claude Code / 本地代理：Presentation Director 或等价确认 → `skills/pptx` + pptxgenjs，作为非 Codex 环境的可编辑备选路径。
3. VS Code + Marp：快速草稿、预览、PDF 和放映版，不作为默认的专业 PPTX 路径。

## 当前推荐路径

```text
Source Material
    ↓
Presentation Director intake（含 output_format 选择）
    ↓
Research Strategy Gate
    ↓
Visual Inspiration Gate（HTML 格式时展示 transition / animation / gradient 字段）
    ↓
Brief Confirmation Gate（open page and wait for user）
    ↓
Image Style Gate（写入 image_generation_mode / image-plan.json；必要时 pre-v1 生图）
    ↓
Generation — route by output_format
    ├─ html-revealjs → Claude/Codex writes Reveal.js HTML directly to v1/final.html
    ├─ pptx → Codex Presentations runtime 写 v1/final.pptx（先查 session plugin，再查 bundled runtime；缺 runtime 则停止）
    └─ both → PPTX first via Codex Presentations runtime, then HTML to v1/final.html（缺 runtime 则停止）
    ↓
Post-v1 Image Placement Gate（仅 post-v1-slot-review / hybrid；写 v2）
    ↓
Render QA
    ├─ HTML: browser screenshot + text-overflow check
    └─ PPTX: contact sheet + no-overlap check（现有流程）
    ↓
PPTX/<task-slug>/final/<task-slug>.html          ← HTML Deck 主输出（如适用）
PPTX/<task-slug>/final/<task-slug>.pptx          ← PPTX 主输出（如适用）
PPTX/<task-slug>/final/<task-slug>-companion.html ← PPTX-only 只读 companion
```

### macOS PowerPoint 文件授权弹窗

默认优先使用 Codex Presentations artifact-tool 或 LibreOffice/headless 渲染路径，避免触发 Microsoft PowerPoint 的 macOS 沙盒文件授权弹窗。如果必须使用 PowerPoint 渲染并遇到 `Grant File Access` / `Please select the folder "render"`，应在渲染前启动：

```bash
scripts/macos/powerpoint-grant-access-watcher.sh 180 &
```

该 watcher 会尝试自动点击 `Select` / `Grant Access`。但 macOS 的 Accessibility/TCC 权限本身不能被项目代码静默绕过；如果系统第一次要求给 Codex/Terminal 自动控制权限，需要一次性授权，之后 watcher 才能自动处理 PowerPoint 弹窗。

在 Codex 环境中，`deck.md`、`design-locks` 和 `ui-ux-pro-max` 都可以作为可选的中间资料或风格约束，但不再是全新 PPTX 第一版生成前的硬性步骤。第一版应优先让 Presentations plugin 根据 confirmed brief 自主完成内容组织、设计系统、contact sheet rhythm 和渲染 QA。

如果目标是在线分享而非 PowerPoint 编辑，生成层可以走 Reveal.js HTML deck 路由。注意这不同于每个 PPTX 最终都会附带的只读 HTML companion；HTML deck 路由是把 HTML 作为主输出。

```text
deck.md
    ↓
Reveal.js 5.1.0 HTML generation spec
    ↓
browser QA / screenshot / text-overflow check
    ↓
PPTX/<task-slug>/vN/final.html
    ↓
PPTX/<task-slug>/final/<task-slug>.html
```

## 当前研究记录

- `docs/deck-builder-review-and-external-research.md`：记录 `deck-builder` 首轮审查发现，以及对 `ppt-master`、`frontend-slides`、`guizang-ppt-skill`、`html-ppt-skill`、`beautiful-html-templates` 的外部方案分析和后续路线图。

## 常见输入模式

### 知识文稿 / 文章 / 书

核心任务是“提炼与重组”，不是逐段搬运。

优先提取：

- 中心论点
- 3 到 5 个关键观点
- 支撑观点的证据、案例、数据、引用
- 适合视觉化的结构：时间线、对比、框架、流程、分类、因果链
- 不适合放进主 deck 的细节，放入 appendix 或 notes

### 工程项目介绍

核心任务是“让听众快速理解项目价值和实现方式”。

优先提取：

- 项目要解决的问题
- 使用者或业务场景
- 系统边界和核心模块
- 架构图、数据流、工作流、接口关系
- 关键技术选择及原因
- 当前进展、效果指标、风险和下一步

## 沟通约定

- 默认用中文沟通。
- 优先用 `Presentation Director`、`brief confirmation`、`Codex Presentations`、`style-review`、`deck.md`、`design intelligence`、`visual contract` 这些术语描述流程。
- 在 Codex 全新 PPTX 请求中，先走 Presentation Director；必须打开确认页并等待用户确认，不要直接启动 Presentations，除非用户明确跳过或已有用户确认过的 confirmed brief。
- 在 Claude Code / 本地代理中，也必须沿用同一套语言字段、页数字段和生成前确认门禁；可用 Presentation Director 时先跑 `guard`，不可用时做等价 chat/static confirmation。
- Claude 可用 `scripts/hooks/claude-presentation-director-prompt.py` 做 UserPromptSubmit 提醒，用 `scripts/hooks/presentation-director-guard.sh` 做生成前 guard adapter。
- 不把 Marp PPTX 称为可细编辑 PPTX；Marp 更适合快速写作、预览、PDF 和放映版输出。
- 不把 `ui-ux-pro-max` 或 Open Design 称为 PPTX 生成器；它们分别是设计情报和视觉合同来源。
- 全局设计规范见 `DESIGN.md`；它是软约束，优先级低于用户明确要求、`brief-confirmed.json` 和任务级 `brief/visual-contract.md`。
