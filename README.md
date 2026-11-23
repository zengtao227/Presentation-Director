# Presentation Director

Presentation Director 是一套面向高质量演示文稿生成和修改的工作流。它从 briefing、结构规划、设计方向、PPTX 生成、渲染 QA 到最终交付进行编排，默认目标是生成可编辑、可验证、可继续迭代的 `.pptx`。

仓库早期名为 MD2PPT，重点是 Markdown 到 PPTX/PDF 的稳定导出。现在的主定位已经升级为 Presentation Director：优先使用 intake、brief confirmation、Codex Presentations、render QA、style-review 和 targeted edit 流程；Markdown/Marp 仍保留为快速写作与离线备用路径。

## 推荐工作流

### 1. Codex 主路径（首选）

适合：新建专业可编辑 `.pptx`、需要 intake / brief confirmation / render QA / style-review 的任务。

1. 先走 [专业可编辑 PPTX 主流程](docs/pptx-master-workflow.md)。
2. 用 Presentation Director 完成 intake、资料路径/网页/Google Drive 地址录入、资料研究策略选择和 visual inspiration 候选选择。
3. 通过 brief confirmation 锁定内容边界、研究策略、视觉方向和输出限制。
4. 交给 Codex `Presentations` 生成 v1，并完成 render QA、style-review、final compare；按 Presentations 技能的本地 PPTX 路径导出并经其 finalizer 校验（不走 Spaces 交付，原因见 CONTEXT.md「Codex Presentations」）；插件 UI 中看不到 `Presentations` 时，使用 bundled 目录里的同一技能，而不是降级到其他 PPTX 工具。
5. 输出到 `Decks/<task-slug>/final/`。

### 2. Claude Code / 本地代理（次选）

适合：没有 Codex `Presentations`、需要离线运行，或者想直接控制代码层生成逻辑的任务。

1. 先写 `deck.md` 和 `design-locks/`。
2. 读取 官方 `pptx` 技能的 `SKILL.md`，用 `pptxgenjs` 生成可编辑 `.pptx`（Anthropic 专有授权，本仓库不再附带；Claude Code 已内置，其他环境从 https://github.com/anthropics/skills 安装）。
3. 再跑缩略图 / 渲染检查，修复后重新导出。

### 3. VS Code + Marp（轻量兜底）

适合：快速写作、预览、PDF、放映版，或者只需要先看版式草稿的场景。

1. 安装 VS Code 插件：`Marp for VS Code`
2. 修改根目录的 `deck.md`
3. 在 VS Code 里用 Marp Preview 检查版式
4. 导出文件：

    ```bash
    npm install
    npm run export:all
    ```

    导出结果在 `outputs/`：

    - `outputs/deck.html`
    - `outputs/deck.pdf`
    - `outputs/deck.pptx`

正式可编辑 PPTX 仍然优先走 Codex 主路径；Marp 只承担快速草稿和轻量导出。

## 核心原则

- 只改 `.md`，不要手改导出的 HTML/PDF/PPTX。
- 每一页用 `---` 分隔，单页内容不要依赖浏览器滚动。
- 复杂布局优先使用 table-like CSS，不优先使用 CSS Grid/Flex。
- 尽量避免 `filter`、`backdrop-filter`、复杂 `box-shadow`、复杂透明叠加。
- 图片提前压缩并固定尺寸，避免导出时重新排版。
- PPTX 导出通常更适合提交和放映，不适合逐字编辑。

## 文档

- [专业可编辑 PPTX 主流程](docs/pptx-master-workflow.md)
- [PPTX 生成方案对比](docs/pptx-generation-schemes.md)
- [Open Design 集成说明](docs/workflow-with-open-design.md)
- [Marp 快速导出流程](docs/export-workflow.md)
- [Markdown 写作与排版规范](docs/markdown-writing-guide.md)
- [预览与导出一致性指南](docs/preview-export-consistency.md)
- [导出稳定性检查清单](docs/checklist.md)
- [UI/UX Pro Max 设计支持](docs/design-skill.md)

## 设计支持

设计知识库使用全局安装的官方 [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) skill（`~/.claude/skills/ui-ux-pro-max` 或 `~/.codex/skills/ui-ux-pro-max`），本仓库不再内置副本。做路演、比赛答辩、项目方案类 PPT 前，先用它检索合适的产品类型、视觉风格、字体、配色和 UX 检查项，再进入 Markdown 或 PPTX 生成。

如果目标是专业、可编辑的 `.pptx`，优先按 [专业可编辑 PPTX 主流程](docs/pptx-master-workflow.md) 使用 Codex `Presentations` 能力。若 Codex 插件列表里搜不到 `Presentations`，检查 bundled 目录：`$HOME/.codex/plugins/cache/openai-primary-runtime/presentations/*/skills/presentations`，按其本地 PPTX 路径导出并用 finalizer 校验（详见 `skills/deck-builder/SKILL.md` 工具表）。Claude Code / 本地代理的备用路径是 官方 `pptx` 技能 + pptxgenjs。Marp / VS Code 只保留给快速写作、预览、PDF 和放映版输出，不作为默认的专业 PPTX 路径。

常用命令示例：

```bash
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "AI SaaS investor pitch" --design-system --format markdown --project-name "Demo Deck"
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "professional education service" --domain product
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "minimal professional editorial" --domain style
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "professional modern" --domain typography
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "Noto Sans SC Chinese presentation" --domain google-fonts
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "service education" --domain color
python3 ~/.claude/skills/ui-ux-pro-max/scripts/search.py "accessibility layout spacing contrast" --domain ux
```

## 适合场景

- 路演 PPT
- 比赛答辩
- 课程汇报
- 项目方案
- 需要快速迭代多个版本的演示稿

## 不适合场景

- 需要在 PowerPoint 里逐个编辑文本框和图形的商业模板
- 依赖大量动画、母版、SmartArt 的传统 PPT
- 复杂网页 HTML 直接无损转 PPTX

## 最重要的经验

不要把 Markdown PPT 当成网页来写。浏览器打开 HTML 属于显示模式渲染，CSS 支持最完整；Marp 导出 PDF/PPTX 会进入 Chromium 打印/截图相关链路，部分 CSS 在分页、缩放、`section` 容器里会出现差异。

为了让 Preview、PDF、PPTX 尽量一致，建议从一开始就采用“导出友好”的写法：

- 并排布局用 `display: table`，不要依赖复杂 Grid/Flex。
- 页面居中用固定 padding、`text-align`、稳定高度，不依赖 `section { display:flex }`。
- 时间线、三列卡片、截图并排都用 table-like 结构。
- logo 和图片统一加 `max-width`、`height:auto`、`object-fit:contain`。
- 少用透明叠加、filter、backdrop-filter、复杂阴影。

完整说明见 [预览与导出一致性指南](docs/preview-export-consistency.md)。
