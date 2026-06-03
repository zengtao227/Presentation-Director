# 工作流：Open Design + ui-ux-pro-max + Codex Presentations

## 核心定位

Open Design 不是 PPTX 生成器，它提供的是成熟的设计语言。这个仓库把其中可复用的视觉方向整理成 `design-locks/`，再交给 Codex `Presentations` 插件生成可编辑 PPTX。

```text
deck.md 内容源
    ↓
ui-ux-pro-max 设计情报
    ↓
design-locks/ Open Design 视觉合同
    ↓
Codex Presentations
artifact-tool presentation JSX → render QA → export PPTX
    ↓
PPTX/<task-slug>/final/<task-slug>.pptx
PPTX/<task-slug>/final/<task-slug>-companion.html
```

## 三层分工

| 层 | 工具 | 作用 |
|----|------|------|
| 设计情报 | `skills/ui-ux-pro-max` | 判断行业气质、配色方向、字体、图表和 UX 风险 |
| 视觉合同 | `design-locks/` | 锁定 Open Design 风格的 hex、字体、层级、版式禁用项 |
| 生成与验证 | Codex `Presentations` | 生成 claim spine、design system、contact sheet、可编辑 PPTX |

需要注意：`skills/pptx` + pptxgenjs 是 Claude Code 或离线备用路径。Codex 主路径应优先使用 `Presentations` 插件的 artifact-tool `presentation-jsx`。

## 可用设计档案

| 文件 | 风格 | 适合场景 |
|------|------|----------|
| `swiss-klein-blue.md` | 瑞士国际主义，Klein Blue | 商业计划、产品路线、执行报告、竞赛答辩 |
| `linear-dark.md` | Linear 暗色，工程精准感 | SaaS 产品、技术平台、投资人 deck |
| `academic.md` | 靛蓝学术，冷调研究感 | 技术方案、数据报告、AI 产品介绍 |
| `editorial.md` | 暖纸叙事，编辑感 | 路演、课程汇报、观点型商业叙事 |
| `notion-warm.md` | Notion 暖白，亲和极简 | 内部文档、文化类、轻量展示 |

## 推荐操作步骤

### 第一步：准备内容

在 `deck.md` 里写清：

- 听众是谁
- 这份 PPT 要推动什么决定
- 每页的结论句 `Claim`
- 每页的证据对象 `Proof object`
- 每个数字、案例、截图或 logo 的来源

不要先写复杂样式。Open Design 档案负责视觉，不应该让内容源混入大量排版指令。

### 第二步：检索设计情报

先用新版聚合生成器拿到完整 design-system brief：

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<行业 + deck 类型 + 听众>" \
  --design-system \
  --format markdown \
  --project-name "<演示主题>"
```

再按需要补查具体域：

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<行业/项目类型>" --domain product
python3 skills/ui-ux-pro-max/scripts/search.py "<视觉气质>" --domain style
python3 skills/ui-ux-pro-max/scripts/search.py "<字体气质>" --domain typography
python3 skills/ui-ux-pro-max/scripts/search.py "<中文字体或英文字体>" --domain google-fonts
python3 skills/ui-ux-pro-max/scripts/search.py "<行业/场景>" --domain color
python3 skills/ui-ux-pro-max/scripts/search.py "<图表类型>" --domain chart
python3 skills/ui-ux-pro-max/scripts/search.py "layout spacing contrast accessibility" --domain ux
```

输出不需要逐字照抄，整理成设计判断即可：该用浅底还是深底、该走瑞士网格还是叙事编辑感、图表该用趋势线还是横向排名、有哪些对比度和排版风险。`--design-system` 输出偏 Web/UI，PPTX 流程只吸收 style、semantic palette、typography、anti-patterns 和 checklist。

### 第三步：选择设计档案

选择一个 `design-locks/*.md`，并把它作为硬约束交给 Codex：

- 色值尽量锁定，不让 AI 随手换色。
- 字体层级锁定，中文字体优先保证可读和可导出。
- 版式规则锁定，例如直角、少阴影、少渐变、页码、hairline。
- 版式名称只作为布局语汇，不是必须调用的固定 API。

### 第四步：给 Codex 的 Prompt

```text
请使用 Codex Presentations 技能生成一个可编辑 PPTX。

输入：
- deck.md
- design-locks/<lock>.md
- docs/pptx-master-workflow.md

要求：
- 使用 artifact-tool presentation JSX，不使用 pptxgenjs 作为主路径
- 先写 claim spine、design-system、contact-sheet plan
- 设计系统必须继承 design-lock 的颜色、字体、版式禁用项
- 可根据 ui-ux-pro-max 的结论选择图表和 proof object 表达方式
- 构建可编辑文本、形状、线条、表格和图表
- 渲染预览图、contact sheet、layout JSON，并完成至少一轮修复验证
- 最终输出 `PPTX/<task-slug>/final/<task-slug>.pptx` 和只读分享版 `PPTX/<task-slug>/final/<task-slug>-companion.html`
```

### 第五步：检查和迭代

检查顺序：

1. contact sheet：缩略图是否有节奏，是否像同一个设计系统。
2. 全尺寸预览：标题是否换行异常，文本是否溢出，图表和连接器是否清楚。
3. PowerPoint：对象是否可编辑，中文字体是否需要替换。
4. 内容：数字、来源、公司名、logo 是否准确。

反馈示例：

- `第 3 页标题仍是主题标签，请改成结论句。`
- `第 5 页和第 6 页都是三卡片，保留第 5 页，第 6 页改成横向时间线。`
- `第 7 页图表缺少直接标注，请去掉图例并把数值贴近条形。`
- `第 9 页新增了 design-lock 外的渐变，请回到 swiss-klein-blue 的纯色系统。`

## 备用：Claude Code / pptxgenjs

如果不用 Codex `Presentations`，可以走本地 `skills/pptx`：

```text
Claude Code
    ↓
读取 skills/pptx/SKILL.md
    ↓
用 pptxgenjs 生成 `PPTX/<task-slug>/final/<task-slug>.pptx` 和只读分享版 HTML
    ↓
用 skills/pptx/scripts/thumbnail.py 生成缩略图检查
```

这个路径的 Prompt 应写成：

```text
使用本仓库 skills/pptx/SKILL.md 的 pptxgenjs 工作流。
读取 deck.md 和 design-locks/<lock>.md。
生成 `PPTX/<task-slug>/final/<task-slug>.pptx`。
同时生成 `PPTX/<task-slug>/final/<task-slug>-companion.html` 作为只读分享版。
生成后运行 skills/pptx/scripts/thumbnail.py 做缩略图检查。
```

## 参考资源

- 主流程：`docs/pptx-master-workflow.md`
- 方案对比：`docs/pptx-generation-schemes.md`
- Codex 主插件：`Presentations`
- 本地备用技能：`skills/pptx/SKILL.md`
- 设计情报：`skills/ui-ux-pro-max/SKILL.md`
- Open Design 原始仓库：https://github.com/nexu-io/open-design
