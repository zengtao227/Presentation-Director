# 从主题到专业可编辑 PPTX：主工作流

> 适用场景：只有一个主题，或已经有文字内容，想用 Codex 生成设计语言专业、叙事逻辑清晰、可在 PowerPoint 里继续编辑的 `.pptx`。

---

## 先纠偏：Codex 主路径不是 pptxgenjs

本项目里有两套容易混淆的能力：

| 路径 | 适合工具 | 生成引擎 | 定位 |
|------|----------|----------|------|
| **主路径** | Codex `Presentations` 能力 | artifact-tool `presentation-jsx` + bundled runtime scripts | 高质量可编辑 PPTX，带叙事、设计系统、渲染 QA |
| **备用路径** | Claude Code / 离线脚本 | `skills/pptx` + pptxgenjs | 没有 Codex Presentations runtime，或用户明确绕过 Codex 主路径时的可编辑 PPTX 方案 |

因此，在 Codex 里写 PPTX 时，Prompt 应该明确要求：

- 使用 **Presentations** 技能 / 插件
- 使用 **artifact-tool presentation JSX**
- 如果插件 UI / tool search 不显示 Presentations，检查 `$HOME/.codex/plugins/cache/openai-primary-runtime/presentations/*/skills/presentations`
- 先运行 `scripts/check_presentation_runtime.mjs` 验证 runtime，再用 `scripts/build_artifact_deck.mjs` 导出 net-new PPTX
- 输出可编辑 `.pptx`
- 通过渲染预览、contact sheet、layout JSON 做质量检查
- 不要把 `pptxgenjs` 当成 Codex 主生成引擎

`pptxgenjs` 仍然有价值，但它属于本仓库 `skills/pptx` 的备用工作流，不是 Codex 的首选路径。

---

## 推荐总流程

```text
[1] 内容源
    主题 / 原始文字 / 数据 / 参考资料 / 代码仓库
        ↓
[2] Presentation Director（Codex net-new PPTX）
    点击式收集听众、目标、资料边界、logo、AI 生图、输出限制
        ↓
[3] Research Strategy Gate
    选择 Codex 深度联网、外部 Deep Research 资料包、Hybrid 或只用用户资料
        ↓
[4] Visual Inspiration Gate
    根据主题和场景生成 3 个视觉方向候选，用户选择一个作为第一版视觉目标
        ↓
[5] brief confirmation gate
    用户确认后才调用 Codex Presentations
        ↓
[6] Codex Presentations 生成
    confirmed brief → claim spine → design system → contact-sheet plan
    → artifact-tool presentation JSX → build_artifact_deck.mjs → render → QA → export v1
        ↓
[7] style-review
    看 contact sheet，选择保持、换配色、换结构、增强表现力或生成对比版本
        ↓
[8] final compare and selection
        ↓
[最终] PPTX/<task-slug>/final/<主题名>.pptx
       PPTX/<task-slug>/final/<主题名>.html
```

这个流程的关键不是“把 Markdown 套模板”，而是先锁住目标、受众、资料边界和输出约束，再让 Presentations 插件负责叙事组织、视觉系统、可编辑构建和渲染 QA。

---

## PPTX Slide Planner 是什么

`PPTX slide planner` 是从原始材料到 `deck.md` 的规划层。它不负责画幻灯片，也不直接生成 `.pptx`，而是先决定“这份 deck 应该如何讲”。

它的输出应该包括：

- `audience`：谁会看这份 PPT
- `goal`：希望对方理解、相信或决定什么
- `thesis`：整份 deck 要证明的一句话
- `arc`：从问题到结论的叙事路径
- `slide count`：目标页数
- `slide plan`：每页的 claim、proof object、layout family、source、missing info
- `appendix plan`：哪些材料只放附录，不进入主线

它解决的是“材料太多、结构不清、直接生成会变成信息堆砌”的问题。真正的 PPTX 生成要等 planner 把每页的职责定清楚之后再开始。

---

## 两类常见输入流程

### A. 文章 / 知识文稿 / 一本书

这类输入的关键不是逐段搬运，而是提炼和重组。

```text
文章 / 书 / 知识文稿
    ↓
提取核心论点、章节结构、关键证据、引用、案例
    ↓
PPTX slide planner：决定 6-12 页主线和 appendix
    ↓
deck.md：每页 claim + proof object + source
    ↓
设计情报 + visual contract
    ↓
Codex Presentations 生成 PPTX
```

建议 planner 优先问：

- 这份材料最值得听众记住的一句话是什么？
- 哪些观点是主线，哪些只是背景？
- 哪些内容可以视觉化成时间线、框架、对比、因果链、分类图？
- 哪些数字、引用、案例必须保留来源？
- 如果只能讲 8 页，哪些内容必须删掉？

推荐 deck 结构：

| 页 | 作用 |
|----|------|
| 1 | 封面：主题 + 一句话 thesis |
| 2 | 为什么这个主题重要 |
| 3 | 核心框架 / 目录，但标题必须是结论句 |
| 4-7 | 关键观点，每页一个 claim + 一个 proof object |
| 8 | 综合模型 / 方法论 / 总结图 |
| 9 | 对听众的启示或行动建议 |
| 10+ | 附录：原文引用、详细数据、延伸阅读 |

### B. 工程项目介绍

这类输入的关键是让听众快速理解“为什么做、做了什么、怎么做、有什么结果、下一步是什么”。

```text
工程项目资料 / README / 代码仓库 / 设计文档
    ↓
提取问题、用户场景、系统边界、模块、数据流、技术选择、指标
    ↓
PPTX slide planner：决定项目叙事和架构图/流程图位置
    ↓
deck.md：每页 claim + proof object + source
    ↓
设计情报 + visual contract
    ↓
Codex Presentations 生成 PPTX
```

建议 planner 优先问：

- 项目解决的真实问题是什么？
- 听众是业务方、评委、投资人、工程师，还是未来维护者？
- 哪张图最能解释系统：架构图、数据流、调用链、流程图还是部署图？
- 有哪些可量化结果：性能、成本、准确率、效率、稳定性、覆盖率？
- 哪些技术选择需要解释 tradeoff？

推荐 deck 结构：

| 页 | 作用 |
|----|------|
| 1 | 封面：项目名 + 价值主张 |
| 2 | 背景问题：为什么需要这个项目 |
| 3 | 使用场景 / 用户旅程 |
| 4 | 解决方案总览 |
| 5 | 系统架构图 |
| 6 | 核心流程 / 数据流 |
| 7 | 关键技术选择与取舍 |
| 8 | 当前成果 / 指标 / demo 截图 |
| 9 | 风险、限制和下一步 |
| 10 | 决策请求 / 合作方式 / Q&A |

---

## 工具分工

| 层 | 工具 / 文件 | 职责 |
|----|-------------|------|
| 内容层 | `deck.md` | 事实、顺序、主张、证据对象、数据来源 |
| 设计情报层 | `skills/ui-ux-pro-max` | 查适合行业的风格、字体、颜色、图表和 UX 检查项 |
| 视觉合同层 | `design-locks/` | 把 Open Design 的设计语言落成 hex、字体、版式、禁用项 |
| 生成层 | Codex `Presentations` | 叙事整理、设计系统锁定、JSX 构建、渲染 QA、导出 PPTX |
| 备用生成层 | `skills/pptx` + pptxgenjs | Claude Code 或离线场景备用 |
| 快速草稿层 | Marp | 快速写作、预览、PDF/不可细编辑 PPTX 导出 |

`ui-ux-pro-max` 和 Open Design 都不是 PPTX 生成器。前者负责帮你做设计判断，后者负责提供设计语言，真正把它们变成可编辑 `.pptx` 的主引擎是 Codex `Presentations`。

---

## 阶段一：写 deck.md

`deck.md` 不要写复杂样式，也不要把它写成 Marp 页面。它应该是内容和证据的唯一来源。

推荐结构：

```markdown
# 演示主题

## Metadata
- Audience: 听众是谁
- Goal: 这份 PPT 要让听众做什么决定
- Length: 目标页数
- Tone: 专业 / 路演 / 竞赛 / 内部汇报

## Thesis
一句话说明整份 deck 要证明什么。

## Slides

### 01 封面
- Claim: 一句话主张，不只是标题
- Proof object: 主题名 / 关键指标 / 场景图
- Source: 用户提供

### 02 问题
- Claim: 现在的问题为什么值得解决
- Proof object: 1 个数据、对比、流程断点或案例
- Source: 数据来源或“用户提供”

### 03 解决方案
- Claim: 方案如何直接回应问题
- Proof object: 架构图 / 流程图 / 三段式机制
- Source: 用户提供

### 04 结果 / 价值
- Claim: 已经产生或预计产生什么结果
- Proof object: KPI、趋势、对比表
- Source: 数据来源

### 05 下一步
- Claim: 现在需要推进的具体动作
- Proof object: roadmap / owner / decision ask
- Source: 用户提供
```

写作要求：

- 每页都要有 `Claim`，不要只写“市场分析”“产品介绍”这种题目。
- 每页只承载一个主要证据对象：图表、流程、时间线、对比、案例或大数字。
- 数字必须来自原始资料；没有数据就写“缺失”，不要让 AI 补。
- 已有长文内容时，先让 Codex 把它压缩成 claim spine，再进入设计。

---

## 阶段二：用 ui-ux-pro-max 做设计情报

新版 `ui-ux-pro-max` 支持 `--design-system` 聚合生成。优先先跑一条总检索，把行业推理规则、风格、语义色板、字体、页面模式和反模式汇总出来：

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<行业 + deck 类型 + 听众>" \
  --design-system \
  --format markdown \
  --project-name "<演示主题>"
```

这份输出是**设计情报简报**，不是最终 PPTX 视觉合同。它偏 Web/UI 语境，里面的动画、CTA、landing section 需要翻译成 deck 语言：版式节奏、proof object、视觉层级、图表语法、反模式。

然后根据需要补充定向检索：

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<行业/项目类型>" --domain product
python3 skills/ui-ux-pro-max/scripts/search.py "<视觉气质>" --domain style
python3 skills/ui-ux-pro-max/scripts/search.py "<字体气质>" --domain typography
python3 skills/ui-ux-pro-max/scripts/search.py "<中文字体或英文字体>" --domain google-fonts
python3 skills/ui-ux-pro-max/scripts/search.py "<行业/场景>" --domain color
python3 skills/ui-ux-pro-max/scripts/search.py "<证据类型>" --domain chart
python3 skills/ui-ux-pro-max/scripts/search.py "layout spacing contrast accessibility" --domain ux
```

常用关键词：

| 场景 | 检索词 |
|------|--------|
| 科技 / SaaS | `saas tech startup` |
| 金融 / 投资 | `fintech investment finance` |
| 医疗 / 健康 | `healthcare medical` |
| 教育 / 竞赛 | `education competition academic professional` |
| 消费品牌 | `brand consumer beauty retail` |
| 数据报告 | `trend comparison metrics timeline` |

把检索结果整理成 5 行设计简报即可：

```markdown
## Design Intelligence
- Generated brief: 来自 `--design-system` 的候选 style / palette / typography / anti-patterns
- Style: Swiss Modernism 2.0 / Minimalism / Editorial / Linear dark ...
- Palette direction: 语义色板 primary / accent / background / foreground / muted / border
- Typography direction: 中文优先 Noto Sans SC / Noto Serif SC，英文按 lock
- Chart grammar: 趋势用 line，排名用 horizontal bar，对比用 before/after
- UX risks: 对比度、标题换行、卡片拥挤、页脚撞内容
```

这一步不要求照抄检索结果。它的作用是帮助你选择或微调设计档案，并提前列出反模式。比如 `--design-system` 给出 Motion-Driven 时，PPTX 里不能照搬“滚动动效”，只能把它翻译成更强的章节节奏、转场页和 proof object 变化。

---

## 阶段三：选择 Open Design / design-lock

从 `design-locks/` 选一个作为视觉合同：

| 档案 | 风格 | 适合 |
|------|------|------|
| `swiss-klein-blue` | Klein Blue + 瑞士网格 | 商业计划、执行报告、产品路线、竞赛答辩 |
| `linear-dark` | 暗色 + 工程精准感 | SaaS 产品、技术平台、投资人 deck |
| `academic` | 靛蓝 + 冷调学术 / 研究感 | 技术方案、数据报告、AI 项目 |
| `editorial` | 暖纸色 + 叙事编辑感 | 通用商业、课程汇报、观点型演示 |
| `notion-warm` | 暖白 + 亲和极简 | 内部汇报、文化类、轻量展示 |

选择规则：

- 面向投资人或商业决策：优先 `swiss-klein-blue` / `linear-dark`
- 技术、AI、数据、竞赛：优先 `academic` / `swiss-klein-blue`
- 课程、内部、文化、说明型：优先 `editorial` / `notion-warm`
- 如果客户有品牌色，仍先选最接近的 lock，再把品牌色作为有限 accent，不要重写整套视觉系统。

建议在 `deck.md` 后面补一个简短 `Design Contract`：

```markdown
## Design Contract
- Lock: design-locks/swiss-klein-blue.md
- Must keep: lock hex values, typography hierarchy, straight-edge grid grammar
- May adapt: layout families according to content proof objects
- Must avoid: gradients, generic card grids, invented logos, unsupported metrics
```

---

## 阶段四：给 Codex 的生成 Prompt

在 Codex 中直接给下面的 Prompt。把 `<...>` 替换成实际内容。

```text
我要生成一个高质量、可编辑的 PowerPoint deck。

请使用 Codex 的 Presentations 技能 / 插件作为主工作流。
生成引擎使用 artifact-tool presentation JSX。
如果当前 Codex 插件 UI 里没有 Presentations，请先检查 bundled runtime：
$HOME/.codex/plugins/cache/openai-primary-runtime/presentations/*/skills/presentations
只要该目录存在，就设置 SKILL_DIR 指向它，运行 scripts/check_presentation_runtime.mjs 验证 runtime，然后用 scripts/build_artifact_deck.mjs 完成 PPTX 导出。
不要使用 pptxgenjs、Marp 或 Google Slides 作为主生成路径，除非你明确说明它们只是备用。

[输入文件]
- 内容源：deck.md
- 设计档案：design-locks/<lock>.md
- 工作流参考：docs/pptx-master-workflow.md

[目标]
- 输出可编辑 .pptx 到 PPTX/<task-slug>/final/<task-slug>.pptx
- 同时输出只读 HTML 分享版到 PPTX/<task-slug>/final/<task-slug>-companion.html
- scratch / preview / layout / QA 文件放在 Presentations 技能自己的 workspace 中
- 最终只把可交付 PPTX 放到 PPTX/<task-slug>/final/

[叙事要求]
- 先从 deck.md 写 claim spine：thesis、audience、one-line arc、每页 claim、proof object、source
- 每页标题必须是结论句，不是主题标签
- 不得编造数字、客户、来源、logo 或品牌资产
- 缺失数据要在 source notes 或 omission notes 里说明

[设计要求]
- 读取 design-lock，把颜色、字体、层级、禁用项作为硬约束
- 结合 ui-ux-pro-max 的设计情报选择图表和版式
- 建立 design-system：背景、字体、色板、图表语法、页码、脚注、kicker、layout families
- 不要连续 3 页使用同一种大版式
- 避免通用 SaaS 卡片堆叠，优先让每页有明确 proof object

[构建要求]
- 使用可编辑文本、形状、线条、表格、图表或由形状构成的可编辑图表
- 图表需要直接标注，少用图例
- 结构图和流程图的连接关系必须清楚，不要用装饰箭头替代语义

[验证要求]
- 渲染每页预览图、生成 contact sheet 和 layout JSON
- 用 Presentations comeback rubric 自评
- 至少完成一次“发现问题 → 修复 → 重新渲染验证”的循环
- 最终回复提供：PPTX 绝对路径、验证命令/结果、仍需人工确认的风险
```

为什么要这样写：

- `Presentations` 会先做叙事和设计系统，再生成 slide modules。
- 它要求渲染 contact sheet，而不是只“打开 PPT 看一眼”。
- 它会把图表、连接器、文本溢出、字体、节奏作为 QA 对象。
- 这样更容易得到专业 deck，而不是一组套了颜色的普通页面。

---

## 阶段五：迭代方式

不要只说“再高级一点”。反馈要指向页码、问题和目标。

| 问题 | 推荐反馈 |
|------|----------|
| 标题像目录 | `第 3 页标题改成结论句，说明为什么这个问题现在必须解决。` |
| 版式重复 | `第 4-6 页连续都是三卡片，请保留第 5 页，其余两页改成时间线和对比图。` |
| 数据页弱 | `第 7 页把 KPI 做成主 proof object，数字 56pt，右侧加 2 行解释，不要再放四个小卡。` |
| 文字太多 | `第 2 页正文压成 3 个短句，每句不超过 16 个汉字。` |
| 图表不清楚 | `第 6 页去掉图例，改成直接标注，并把横轴标签减少到 4 个。` |
| 风格跑偏 | `第 8 页回到 design-lock 的 paper / ink / accent，不要新增渐变或阴影。` |

每次迭代后都要求：

- 重新渲染受影响页
- 更新 contact sheet
- 确认没有产生新的文字溢出、遮挡、低对比问题

---

## 备用路径：Claude Code / 本地 pptxgenjs

只有在不用 Codex `Presentations` 插件时，才走这条路。

```text
deck.md + design-lock
    ↓
Claude Code 读取 skills/pptx/SKILL.md
    ↓
pptxgenjs 生成可编辑 .pptx
    ↓
skills/pptx/scripts/thumbnail.py 生成缩略图
    ↓
人工反馈并重新生成
```

给 Claude Code 的 Prompt 可以明确：

```text
使用本仓库 skills/pptx/SKILL.md 的 pptxgenjs 工作流。
读取 deck.md 和 design-locks/<lock>.md。
生成 PPTX/<task-slug>/final/<task-slug>.pptx。
同时生成 PPTX/<task-slug>/final/<task-slug>-companion.html 作为只读分享版。
生成后运行 skills/pptx/scripts/thumbnail.py 做缩略图检查。
```

这条路径能生成可编辑 PPTX，但叙事编辑、contact-sheet 质量门槛和渲染 QA 不如 Codex `Presentations` 完整，需要你自己更严格地审查。

---

## 与 Marp、Google Slides 的关系

| 需求 | 推荐路径 |
|------|----------|
| 快速写内容、预览、导出 PDF | Marp |
| 高质量可编辑 PowerPoint | Codex `Presentations` 能力；插件 UI 不显示时使用 bundled runtime scripts |
| 没有 Codex Presentations runtime，但仍要可编辑 PPTX | 仅在用户明确绕过 Codex 主路径时用 `skills/pptx` + pptxgenjs |
| 最终要交 Google Slides 原生文件 | 先用 Presentations 生成本地 PPTX，再通过 Google Drive 导入为 native Google Slides |

不要把 Marp 导出的 PPTX 当作“可编辑 PPTX”。Marp 更接近视觉成品导出，适合放映和提交，不适合对方在 PowerPoint 里逐个编辑文本框和图形。

---

## 最小顺畅方案

如果只想记住一个流程：

```text
1. 写 deck.md：每页 claim + proof object + source
2. 用 ui-ux-pro-max 查 5 类信息：style / typography / color / chart / ux
3. 选一个 design-lock，作为 Open Design 视觉合同
4. 在 Codex Prompt 中强制使用 Presentations + artifact-tool presentation JSX；插件 UI 不显示时强制解析 bundled runtime scripts
5. 要求 claim spine、design-system、contact-sheet plan、render QA、至少一轮修复
6. 输出 PPTX/<task-slug>/final/<主题名>.pptx 和只读分享版 HTML
```

这就是当前最顺畅的高质量 PPTX 工作流。

---

## 文件索引

```text
MD2PPT/
├── deck.md                          # 内容源：主题、主张、证据、数据来源
├── design-locks/                 # Open Design 派生视觉合同
│   ├── editorial.md                 # 暖纸叙事，编辑感
│   ├── academic.md                  # 靛蓝学术，冷调研究感
│   ├── swiss-klein-blue.md          # Klein Blue + 瑞士网格
│   ├── linear-dark.md               # 工程暗色，精准感
│   └── notion-warm.md               # 暖白极简
├── assets/                          # AI 生成的背景图（gitignore，临时文件）
│   └── cover-bg.png                 # 封面背景图（可选步骤生成）
├── skills/
│   ├── pptx/                        # Claude / 本地备用：pptxgenjs 工作流
│   └── ui-ux-pro-max/               # 设计情报数据库
├── docs/
│   ├── pptx-master-workflow.md      # ← 主流程（你在这里）
│   ├── ai-background-image.md       # 可选：AI 背景图生成说明
│   ├── roadmap.md                   # 后续开发路线图
│   ├── competitive-analysis-pi.md   # 竞品分析：pi.inc vs DeepVinci
│   ├── workflow-with-open-design.md # Open Design 集成说明
│   └── pptx-generation-schemes.md  # 方案对比
└── PPTX/                            # 每次生成的用户可见工作区（gitignore）
    ├── deck.pptx
    ├── deck.pdf
    └── deck-longimage.png           # 可选：长图导出
```
