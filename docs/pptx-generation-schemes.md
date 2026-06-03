# PPTX 生成方案研究与选型（2026-05）

## 核心需求

- 内容逻辑清晰：每页有结论、证据对象和来源
- 设计语言专业：整份 deck 有统一视觉系统和版式节奏
- PPTX 可编辑：PowerPoint 里能继续改文字、形状、图表或表格
- 验证闭环明确：能渲染预览、检查缩略图、修复后再验证
- 尽量支持中文内容

---

## 当前推荐

**首选：Codex `Presentations` 能力 + artifact-tool presentation JSX。**

原因：

- 它不是简单“Markdown 转 PPTX”，而是完整 deck 工作流：claim spine、design system、contact-sheet plan、render QA、rubric 评分、迭代修复。
- 输出是可编辑 PowerPoint。
- 能把 `ui-ux-pro-max` 的设计情报和 `design-locks/` 的 Open Design 视觉合同结合起来。
- 比单纯 pptxgenjs 脚本更适合生成有专业叙事和视觉节奏的 deck。
- 在 Codex Desktop 插件 UI 搜不到 `Presentations` 时，仍应检查 bundled runtime：`$HOME/.codex/plugins/cache/openai-primary-runtime/presentations/*/skills/presentations`。存在则用其中的 `scripts/check_presentation_runtime.mjs` 和 `scripts/build_artifact_deck.mjs`，不得直接降级到 fallback。

本仓库 `skills/pptx` + pptxgenjs 保留为 Claude Code / 离线备用路径。Marp 保留为快速写作、预览和提交 PDF 的路径。

---

## 方案对比总览

| 方案 | 预览 / QA | PPTX 可编辑 | 中文字体 | 推荐度 | 定位 |
|------|-----------|-------------|----------|--------|------|
| Codex `Presentations` | artifact-tool 渲染、contact sheet、layout JSON、rubric；插件 UI 不显示时使用 bundled runtime scripts | ✅ | ✅ 需检查本机字体 | ⭐⭐⭐⭐⭐ **当前首选** | 高质量可编辑 PPTX |
| 本地 `skills/pptx` + pptxgenjs | LibreOffice/Poppler 缩略图 | ✅ | ✅ 需检查字体 | ⭐⭐⭐⭐ | Claude/离线备用 |
| Marp CLI 直接导出 | VS Code Marp Preview | ❌ 更接近截图/视觉成品 | ✅ | ⭐⭐⭐ | 快速草稿、PDF、放映 |
| Google Slides 导入 | 浏览器 Google Slides | ✅ | ⚠️ 导出后可能替换 | ⭐⭐⭐ | 需要协作或原生 Slides |
| Office-PowerPoint-MCP-Server | 无内置强 QA | ✅ | ✅ | ⭐⭐ | 可探索 |
| pptx-generator-mcp | 无内置强 QA | ✅ | ✅ | ⭐⭐ | 可探索 |
| Alai MCP | 在线编辑器 | ✅ 需付费 | ✅ | ⭐⭐⭐⭐ | 付费低摩擦路径 |

---

## 1. Codex Presentations（当前首选）

**工作流：**

```text
deck.md + design-lock
        ↓
Codex Presentations
claim spine → design system → contact-sheet plan
        ↓
artifact-tool presentation JSX 构建可编辑 slides
        ↓
build_artifact_deck.mjs 导出 PPTX / 预览 / contact sheet
        ↓
渲染 PNG / contact sheet / layout JSON
        ↓
修复弱页并重新验证
        ↓
PPTX/<task-slug>/final/<task-slug>.pptx
PPTX/<task-slug>/final/<task-slug>-companion.html
```

**优点：**

- 把内容叙事、设计系统和视觉 QA 放在同一条工作流里。
- 可显式要求使用 `ui-ux-pro-max` 设计情报和 Open Design `design-locks/`。
- 适合商业计划、投资人 deck、技术方案、数据报告等需要专业成品感的任务。
- PowerPoint 输出可编辑；HTML companion 用于简单分享，不作为编辑源。

**缺点：**

- 需要 Codex 环境中的 `Presentations` 插件能力。
- 生成前要把内容和设计约束讲清楚，否则插件会花时间补齐不明确的部分。
- 最终仍需要人工检查字体、事实、logo 和敏感数据。

**适合场景：** 当前项目中“主题/文字内容 → 专业可编辑 PPTX”的主路径。

---

## 2. 本地 skills/pptx + pptxgenjs（备用）

**工作流：**

```text
Claude Code / 本地 agent
        ↓
读取 skills/pptx/SKILL.md
        ↓
pptxgenjs 生成 .pptx
        ↓
thumbnail.py 生成缩略图
        ↓
人工指出问题，再改代码重新生成
```

**优点：**

- 完全本地，可控，PPTX 可编辑。
- `skills/pptx` 已包含读取、编辑、打包、缩略图等辅助脚本。
- 适合 Claude Code 或没有 Codex `Presentations` 插件的环境。

**缺点：**

- 叙事编辑、版式节奏和 comeback rubric 需要手动要求。
- QA 主要依赖缩略图和人工复查，不如 Presentations 插件完整。
- Prompt 里容易把“设计档案”误当成固定模板，导致页面重复。

**适合场景：** 离线生成、Claude Code 备用、需要直接控制 pptxgenjs 代码。

---

## 3. Marp CLI 直接导出

**工作流：** VS Code 写 Marp MD → Marp Preview → `npm run export:all`

**优点：**

- 写作和预览最快。
- PDF/HTML 导出稳定，适合提交和放映。
- 中文渲染通常最稳。

**缺点：**

- PPTX 基本不是“原生可编辑对象”，更适合视觉成品。
- 复杂 CSS 在导出链路中可能变形。

**适合场景：** 快速草稿、课程展示、比赛提交 PDF、无需对方继续编辑。

---

## 4. Google Slides 路径

有两种用法：

1. **推荐用法**：先用 Codex `Presentations` 生成本地 PPTX，再通过 Google Drive 插件导入为 native Google Slides。
2. **备用用法**：直接通过 Google Slides MCP 写入 Slides。

**优点：**

- 浏览器协作方便。
- Google Slides 中可继续调整。

**缺点：**

- 字体从 Google Slides 导出 PPTX 时可能替换。
- 直接 MCP 写 Slides 的视觉质量和验证闭环通常不如先生成本地 PPTX。
- 复杂图表可能不是 PowerPoint 原生可编辑图表对象。

**适合场景：** 最终交付必须在 Google Drive / Google Slides 内协作。

---

## 5. Office-PowerPoint-MCP-Server / pptx-generator-mcp

这两类 MCP 可以生成可编辑 PPTX，但当前不作为主路径。

**原因：**

- 没有像 `Presentations` 那样强制 claim spine、design system、contact sheet 和 comeback rubric。
- 需要更重的 Prompt 管理才能稳定产出专业视觉系统。
- 对本项目已有的 Open Design 档案和 ui-ux-pro-max 设计情报没有天然整合。

**适合场景：** 后续如果要做专门的 PowerPoint API 自动化，可以继续研究。

---

## 6. Alai MCP

**优点：**

- 在线编辑器体验顺滑。
- 对不想处理本地依赖的人很友好。

**缺点：**

- PPTX 导出通常需要付费。
- 工作流和本仓库的 `deck.md` / design-lock / Codex QA 体系不完全一致。

**适合场景：** 愿意付费并接受在线平台工作流时使用。

---

## 当前推荐工作流

```text
写 deck.md
        ↓
用 ui-ux-pro-max --design-system 生成设计情报简报
按需补查 style / typography / google-fonts / color / chart / ux
        ↓
选择 design-locks/<lock>.md
        ↓
Codex Prompt 明确：
使用 Presentations + artifact-tool presentation JSX
插件 UI 不显示时解析 bundled runtime scripts
不要使用 pptxgenjs 作为主路径
        ↓
生成 claim spine / design system / contact-sheet plan
        ↓
构建、渲染、修复、再验证
        ↓
输出 `PPTX/<task-slug>/final/<task-slug>.pptx` 和 `PPTX/<task-slug>/final/<task-slug>-companion.html`
```

详见：`docs/pptx-master-workflow.md`。

---

## 未来升级路径

- 如果经常要把 PPTX 转成 Google Slides：增加 Google Drive 导入步骤说明。
- 如果要让 Claude Code 也稳定出高质量 deck：把 Presentations 的 claim spine / design-system / contact-sheet QA 思路迁移到 `skills/pptx` Prompt 模板。
- 如果需要公司统一品牌模板：新增 `design-locks/<brand>.md`，而不是每次在 Prompt 里临时描述品牌色。
