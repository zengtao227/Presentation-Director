# AI 生图流程产品化 & HTML 动效内部化 — 实施设计说明

> 阶段 0 设计文档。不动代码，供 Claude 审查后再进入阶段 1。
> 覆盖范围：AI 生图决策模型重构（阶段 1–3）+ HTML 动效内部化（阶段 4–5）。

---

## 1. 核心概念澄清：两个字段，两个语义层

当前系统只有一个 `image_policy` 字段，承担了两件事：用户偏好声明 + 执行决策。
本次重构把它拆分为两个字段，职责严格分离。

### 1.1 `image_policy` — 安全边界（Intake 阶段声明）

**语义**：用户允许 AI 图出现的范围。这是一条不可逾越的权限边界，在 Intake 表单填写，保存进 `brief-confirmed.json`，整个流程中不变。

**现有枚举（来自 `presentation_director.py` 第 585 行，保持不变）：**

| 值 | 含义 |
|---|---|
| `none` | 禁止任何 AI 生成图片出现在最终输出中 |
| `abstract-only` | 仅允许抽象背景/概念图（最严格的允许档） |
| `cover-section` | 允许封面和章节分隔页使用 AI 图 |
| `ask-before-use` | 每张图生成前询问——**本次重构重点**：拆解为 `image_generation_mode = post-v1-slot-review` 实现 |
| `custom` | 自定义（用户自填描述） |

**迁移规则（新 `image_generation_mode` 对旧 `image_policy` 的默认映射）：**

| image_policy | 默认推荐的 image_generation_mode |
|---|---|
| `none` | `none`（Image Style Gate 中只显示此选项） |
| `abstract-only` | `global-background`（单张通用抽象背景） |
| `cover-section` | `cover-section-auto`（封面+通用章节背景） |
| `ask-before-use` | `post-v1-slot-review`（v1 后逐页确认） |
| `custom` | Image Style Gate 中全选项开放 |

**规则**：`image_generation_mode` 的实际执行范围不得超出 `image_policy` 所允许的边界。

---

### 1.2 `image_generation_mode` — 执行动作（Image Style Gate 阶段声明）

**语义**：实际执行何种生图行为、在流程的哪个阶段触发。这是执行层决策，在 Brief 确认之后、生成 v1 之前，由 Image Style Gate 中的用户选择决定。

| 模式 | 触发时机 | 含义 |
|---|---|---|
| `none` | 全流程 | 不生成 AI 图（无论 policy 允许什么） |
| `global-background` | v1 生成前 | 生成一张全局背景纹理图，用于封面、章节页、模板底纹 |
| `cover-section-auto` | v1 生成前 | 生成封面背景图 + **一张通用**章节分隔页背景图（v1 前不知道章节数量和各章主题，无法按章节分别生成） |
| `post-v1-slot-review` | v1 preview artifact 就绪后 | 渲染 v1 后逐页确认图片槽位和 Prompt（PPTX：contact sheet；HTML：screenshots）|
| `hybrid` | v1 前 + v1 后 | 先生成全局背景图（v1 前），v1 后再按页补图 |

**兼容性约束表**（§1.1 定义默认推荐 mode；本表只表示 allowed/not-allowed，⚠️ 表示 allowed 但非推荐路径，实现时须遵守附加约束）：

| image_policy \ image_generation_mode | none | global-background | cover-section-auto | post-v1-slot-review | hybrid |
|---|:---:|:---:|:---:|:---:|:---:|
| `none` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `abstract-only` | ✅ | ✅ | ✅ | ✅² | ✅ |
| `cover-section` | ✅ | ✅³ | ✅ | ✅² | ✅³ |
| `ask-before-use` | ✅ | ⚠️⁴ | ⚠️⁴ | ✅ | ⚠️⁴ |
| `custom` | ✅ | ✅ | ✅ | ✅ | ✅ |

> ² `post-v1-slot-review` 时，Image Placement Gate 中仅显示 policy 允许范围内的槽位，超出范围的操作灰化不可选。
> ³ `global-background` 生成一张背景纹理图，当 policy 为 `cover-section` 时只应用于封面和章节分隔页，内容页不使用。
> ⁴ `ask-before-use` 下，pre-v1 自动模式（`global-background`、`cover-section-auto`、`hybrid` 的 pre-v1 部分）是 allowed 但**非推荐**（默认推荐 `post-v1-slot-review`，见 §1.1 迁移规则）。若用户明确选择 pre-v1 模式，Image Style Gate **必须**逐条展示每个 target 的 Prompt 供用户确认后才可生图（见 §3.3）。

> **关于 `abstract-only` × `cover-section-auto`**：初稿标记为❌，理由是"封面图不是纯抽象背景"。这是错误的——所有 prompt 模板（`docs/ai-background-image.md`）生成的正是抽象几何纹理（"Abstract… no text, no people"），与 `abstract-only` 完全兼容。`image_policy` 的两个维度（图像内容类型 vs 允许出现的页面位置）在当前枚举中确实有些混用，但拆分枚举会破坏已有的 6 语言本地化，留待将来迭代。现阶段：`abstract-only` × `cover-section-auto` = ✅，只要生成的是抽象纹理即可。

---

### 1.3 字段关系图

```
Intake 阶段
  └─ image_policy = "cover-section"    ← 用户说"我允许封面/章节有 AI 图"

Brief 确认后（Image Style Gate）
  └─ image_generation_mode = "cover-section-auto"  ← 执行层决定"自动生成"

v1 生成前（若 mode ≠ post-v1-slot-review）
  └─ 生图 → 写入 image-assets.json

v1 生成，输出 contact sheet

v1 后（若 mode = post-v1-slot-review 或 hybrid）
  └─ Image Placement Gate → 用户逐页确认槽位
```

---

## 2. PPTX 与 HTML 的能力边界

两种输出路径在图片和动效上的能力不同，设计时必须明确边界，避免互相污染。

### 2.1 PPTX 路径（静态可编辑优先）

| 能力 | PPTX 是否支持 |
|---|---|
| 背景图（封面/章节页） | ✅ 嵌入 PNG，满铺 + 遮罩 |
| 内容页插图 | ✅ 嵌入 PNG，有明确槽位 |
| 内容内部动画（逐项出现等） | ⚠️ pptx 格式支持，但 Codex Presentations 不承诺还原 |
| CSS/JS 动画 | ❌ 不支持 |
| Canvas FX | ❌ 不支持 |
| 可编辑性 | ✅ 用 PowerPoint/Keynote 直接编辑 |
| 核心承诺 | **可编辑 + 图片精确落位** |

**规则**：`html_motion_level` 和 `html_motion_profile` 字段只影响 HTML 生成路径，PPTX 生成时完全忽略这两个字段。

### 2.2 HTML 路径（Reveal.js，动效表现优先）

| 能力 | HTML 是否支持 |
|---|---|
| 背景图 | ✅ CSS `background-image` |
| 内容内部动画（逐项出现、数字跳动）| ✅ Reveal.js Fragment + JS |
| 页面切换动效 | ✅ `html_transition` 字段 |
| Canvas FX（粒子、WebGL）| ⏳ **未来能力**，当前不实现；cinematic level 当前只用 CSS 动画 |
| Presenter Mode | ⚠️ Reveal.js 有 Notes plugin 支持，但当前 HTML prompt 未明确加载；需决定用 Reveal Notes plugin 还是其他方案（见下方注释） |
| PDF 导出 | ✅ `?print-pdf` 参数 |
| 可编辑性 | ❌ 源码即最终输出 |
| 核心承诺 | **视觉丰富 + 演讲体验** |

> **Presenter Mode 说明**：当前 HTML prompt（第 2868 行）要求在 `<aside class="notes">` 中写 speaker notes，这是 Reveal.js Notes plugin 的格式，但 HTML prompt 的 CDN 列表中没有加载 Notes plugin。两个选项：(a) 在 HTML prompt 中补充加载 `plugin/notes/notes.js`；(b) 维持现状（notes 写入 HTML 但 Presenter Mode 不可用，仅 PDF 导出时可见）。当前阶段建议选(a)，改动量极小。

---

## 3. 新增 Gate 序列

### 3.1 当前 Gate 序列

```
Intake → Visual Inspiration → Brief Confirmation → [生成 v1] → Style Review → Compare
```

### 3.2 新 Gate 序列（增加两个图片门禁）

```
Intake
  └─ 收集 image_policy（已有）
  ↓
Visual Inspiration
  └─ 设计方向选择（已有）
  ↓
Brief Confirmation
  └─ 用户 click 确认（已有）
  ↓
★ Image Style Gate（新增）
  └─ 选择 image_generation_mode
  └─ 写入 image-plan.json
  └─ touch: status/images-style.ready
  ↓
Pre-v1 生图（仅当 mode = global-background / cover-section-auto / hybrid）
  └─ 调用 API，下载 PNG → PPTX/<task>/assets/ai/
  └─ 记录到 image-assets.json（含 status: success/failed）
  └─ 失败时写 status: "failed"，记录 error_message，不静默跳过
  ↓
v1 生成（含已生成图片的引用）
  └─ 渲染 contact-sheet.png
  ↓
v1 preview artifact（output_format 决定触发物）
  ├─ pptx → v1/final.pptx + v1/contact-sheet.png + v1/slides/*.png
  ├─ html-revealjs → v1/final.html + v1/screenshots/*.png（浏览器截图）
  └─ both → v1/final.pptx + v1/final.html + v1/contact-sheet.png
  ↓
★ Image Placement Gate（新增，仅当 mode = post-v1-slot-review / hybrid）
  └─ 展示 v1 preview artifact（PPTX: contact-sheet.png；HTML: screenshots/*.png）
  └─ 用户逐页确认：哪些页要图、用什么 Prompt、placement_type、asset_kind
  └─ 写入 image-placement-request.json
  └─ touch: status/images-placement.ready
  ↓
Post-v1 生图 + 写入（Image Placement Gate 完成后，output_format 决定执行方式）
  ├─ pptx → targeted edit 将图片插入 v1/final.pptx → 产出 v2/final.pptx
  │          重新渲染 v2/contact-sheet.png + v2/slides/*.png
  │          在 v2/qa-summary.md 中记录
  ├─ html-revealjs → 用图片路径重新生成 Reveal.js HTML → v2/final.html
  │                  重新截图 v2/screenshots/*.png
  └─ both → 先 PPTX targeted edit → v2/final.pptx；再重生成 Reveal.js HTML → v2/final.html
  └─ 追加 final_status 到 image-assets.json
  ↓
Style Review（已有，此时展示的是含图片的 v2）
  ↓
Compare / Final（已有）
```

### 3.3 Image Style Gate 的展示内容

- 显示当前 `image_policy` 值（告知用户允许范围）
- 列出兼容的 `image_generation_mode` 选项（根据兼容性约束表过滤）
- 对每个选项说明触发时机和预期行为
- 用户选择后，如果 mode ≠ none，显示 AI 生图的预设 Prompt 草稿（来自 design-lock 风格关键词），供用户修改
- **`image_policy = ask-before-use` 的附加要求**：无论选择哪个 mode（包括 pre-v1 自动模式），Image Style Gate 必须展示每个 target 的 Prompt 草稿逐条供用户确认后，才能写入 `image-plan.json` 并触发生图。不允许"用户只选了模式，但没逐条审查 Prompt 就自动生成"。

### 3.4 Image Placement Gate 的展示内容

- **必须在 v1 preview artifact 就绪后才展示**（见 §5b 和 §3.2；PPTX：`v1/contact-sheet.png`；HTML：`v1/screenshots/*.png` 或 `v1/final.html`）
- 按 output_format 显示 v1 预览：PPTX 用 contact sheet 缩略图，HTML 用 screenshots 截图
- 每页旁边显示当前图片状态（已有/无图/plan 中要补图）
- 用户可以对每页标记：保留 / 删除 / 替换（提供新 Prompt）/ 添加
- 超出 `image_policy` 范围的操作在 UI 层灰化不可选

---

## 4. 新增数据文件 Schema

所有文件存放在 `PPTX/<task-slug>/` 下。

### 4.1 `image-plan.json` — 生图计划（Image Style Gate 后写入）

```json
{
  "task_slug": "my-deck",
  "image_policy": "cover-section",
  "image_generation_mode": "cover-section-auto",
  "planned_at": "2026-06-03T10:00:00",
  "targets": [
    {
      "page_role": "cover",
      "prompt_draft": "Abstract dark blue geometric texture...",
      "output_path": "assets/ai/cover-bg.png",
      "dimensions": "1920x1080"
    },
    {
      "page_role": "section-divider",
      "prompt_draft": "Abstract dark blue geometric texture, chapter marker...",
      "output_path": "assets/ai/section-bg.png",
      "dimensions": "1920x1080"
    }
  ]
}
```

### 4.2 `image-assets.json` — 生图执行记录

每个 target 有独立的 `attempts[]`（记录每次 API 调用，实现 Retry-2 的日志可追溯）和一个 `final_status`（guard 只检查这个字段）。

```json
{
  "task_slug": "my-deck",
  "assets": [
    {
      "id": "cover-bg-001",
      "page_role": "cover",
      "prompt": "Abstract dark blue geometric texture...",
      "output_path": "assets/ai/cover-bg.png",
      "final_status": "success",
      "attempts": [
        {
          "attempt": 1,
          "api": "dall-e-3",
          "at": "2026-06-03T10:05:00",
          "status": "failed",
          "error": "timeout"
        },
        {
          "attempt": 2,
          "api": "dall-e-3",
          "at": "2026-06-03T10:05:05",
          "status": "success",
          "size_bytes": 204800,
          "error": null
        }
      ]
    },
    {
      "id": "section-bg-001",
      "page_role": "section-divider",
      "prompt": "Abstract dark blue geometric texture, chapter...",
      "output_path": "assets/ai/section-bg.png",
      "final_status": "failed",
      "attempts": [
        { "attempt": 1, "status": "failed", "error": "rate limit", "at": "2026-06-03T10:05:10" },
        { "attempt": 2, "status": "failed", "error": "rate limit", "at": "2026-06-03T10:05:15" },
        { "attempt": 3, "status": "failed", "error": "rate limit", "at": "2026-06-03T10:05:20" }
      ]
    }
  ]
}
```

**关键设计**：

- `final_status` 由**生图层**（不是 guard）写入，写入规则：
  - 仅当 `output_path` 文件实际存在 **且** `size_bytes > 0` 时，才写 `final_status: "success"`
  - 否则即使 API 返回 200，也写 `final_status: "failed"`，`error` 标注 "file missing or empty"
- guard 只读 `final_status`，不做额外文件检查。这样 guard 简单，而"成功"的语义已经在生图层保证
- sha256 不做（无去重/防篡改需求，过度设计）
- `attempts[]` 仅用于调试和日志，guard 不读

### 4.3 `image-placement-request.json` — v1 后槽位确认（Image Placement Gate 后写入）

```json
{
  "task_slug": "my-deck",
  "output_format": "pptx",
  "base_version": "v1",
  "confirmed_at": "2026-06-03T11:00:00",
  "placements": [
    {
      "slide_index": 1,
      "slide_role": "cover",
      "action": "keep",
      "asset_id": "cover-bg-001",
      "placement_type": "full-bleed-background",
      "asset_kind": "abstract-texture",
      "overlay_opacity": 0.5,
      "notes": null
    },
    {
      "slide_index": 3,
      "slide_role": "section-divider",
      "action": "replace",
      "new_prompt": "Abstract indigo wave texture, more dynamic...",
      "placement_type": "full-bleed-background",
      "asset_kind": "abstract-texture",
      "overlay_opacity": 0.4,
      "notes": "章节一：想要更有活力的感觉"
    },
    {
      "slide_index": 5,
      "slide_role": "content",
      "action": "add",
      "new_prompt": "Minimal geometric pattern, supporting data visualization",
      "placement_type": "content-inset",
      "asset_kind": "concept-illustration",
      "overlay_opacity": null,
      "notes": "数据对比页，希望有低调背景纹理"
    }
  ]
}
```

**字段说明**：
- `slide_role`：`cover / section-divider / content / end`，用于 guard 验证 policy 允许范围
- `placement_type`：`full-bleed-background`（满铺 + 遮罩）/ `content-inset`（内容槽位，有边距）
- `asset_kind`：`abstract-texture`（`abstract-only` policy 下只允许此值）/ `concept-illustration`（需要 `cover-section` 或更宽松 policy）
- `overlay_opacity`：遮罩透明度（0–1），`null` 表示无遮罩（content-inset 不加遮罩）；确保文字可读性（封面建议 0.4–0.6）
- 不规定精确 `bbox`：full-bleed 按 slide 尺寸满铺，content-inset 由 targeted edit 按模板槽位确定

---

## 5. 状态文件

```
PPTX/<task-slug>/status/
  confirmed.ready          ← 已有
  revision.ready           ← 已有
  final-selected.ready     ← 已有
  images-style.ready       ← 新增：Image Style Gate 完成信号
  images-placement.ready   ← 新增：Image Placement Gate 完成信号
```

---

## 5b. HTML 输出路径规范（版本化决定）

**决定**：HTML 输出路径与 PPTX 对称，采用版本化目录，选定版本复制到 `final/`。

| 版本目录 | PPTX | HTML |
|---|---|---|
| v1/ | `v1/final.pptx` + `v1/contact-sheet.png` | `v1/final.html` + `v1/screenshots/*.png` |
| v2/ | `v2/final.pptx` + `v2/contact-sheet.png` | `v2/final.html` + `v2/screenshots/*.png` |
| final/ | `final/<task-slug>.pptx` | `final/<task-slug>.html` |

**`final/` 目录内容规则（output_format 决定）**：

| output_format | final/ 包含 |
|---|---|
| `pptx` | `<slug>.pptx` + `<slug>-companion.html`（只读 HTML Companion，由 PPTX 渲染图生成）|
| `html-revealjs` | `<slug>.html`（Reveal.js 完整 Deck） |
| `both` | `<slug>.pptx` + `<slug>.html`（Reveal.js Deck）；Companion **不单独生成**（HTML Deck 已覆盖分享需求） |

> HTML Deck（Reveal.js）和 HTML Companion 都以 `<slug>.html` 为文件名，但语义不同。`output_format=both` 时，`final/<slug>.html` 是 Reveal.js Deck，不是 Companion。`output_format=pptx` 时，`final/<slug>-companion.html` 是 Companion，与 Deck 文件名不冲突。

**需要同步修改的文件**：
- `CONTEXT.md` 第 167、215、240 行：从 `final/<deck>.html` 改为"HTML 版本化在 vN/final.html，选定后复制到 final/<slug>.html"
- `presentation_director.py` 第 2846 行：`html_output = task_dir / "final" / f"{task_dir.name}.html"` → 改为生成到 `vN/final.html`，final 路径在版本选定后再定

---

## 6. 图片存储路径规范

所有 AI 生成图片统一存放在：

```
PPTX/<task-slug>/assets/ai/
  cover-bg.png
  section-bg.png
  section-01-bg.png
  slot-slide-07.png
  ...
```

**规则**：
- 不存放到项目根 `assets/`，不存放到 `sources/`
- 文件名语义化，反映用途
- `.gitignore` 已有 `/PPTX/` 和 `assets/` 两条规则，无需额外添加

---

## 7. HTML 动效系统升级

### 7.1 当前状态

当前 HTML 动效通过 visual candidate 的 `html_animation` 字段控制，只有三档：
`rich / moderate / minimal`

粒度太粗，无法区分"有动画但内敛"和"有动画且有 Canvas FX"。

### 7.2 新两层系统

#### 层 1：`html_motion_level`（强度）

| 值 | 含义 |
|---|---|
| `none` | 无任何动画，静态 HTML |
| `subtle` | 仅 entry animation（fade-in、slide-up 等） |
| `expressive` | 标题、数字、图表、章节页有动效；无 Canvas FX |
| `cinematic` | 封面、章节页、结束页使用 CSS 动画强化版（无 WebGL）；Canvas FX（粒子/WebGL）为**未来能力**，当前不实现 |

#### 层 2：`html_motion_profile`（风格）

| 值 | 适用场景 | 典型动效偏好 |
|---|---|---|
| `presenter` | 面对面演讲 | 慢节奏，少干扰，章节过渡明确 |
| `academic` | 学术汇报 | 克制，数据可视化优先，无 Canvas FX |
| `tech` | 工程/技术分享 | 线条感，代码块高亮，Blueprint 风格 |
| `pitch` | 路演/融资 | 强冲击力，数字跳动，封面 cinematic |
| `product` | 产品发布 | 丝滑过渡，截图展示，subtle 为主 |
| `editorial` | 内容型/故事型 | 排版动效，图文交替，暖调 |

#### 组合规则

- `html_motion_level` 缺省时使用 `subtle`；`html_motion_profile` 由主题/视觉候选推导
- `html_motion_level = cinematic` 对封面/章节/结束页使用 CSS 动画强化版（spotlight、scale-in 等）；Canvas FX（粒子/WebGL）是未来能力，当前不实现
- `academic` profile 自动将 `cinematic` 降为 `expressive`（保守降级）
- PPTX 生成时完全忽略这两个字段

#### 向后兼容

已验证（grep `html_profile_for_candidate`）：现有 `html_animation` 字段的实际取值为 `"rich"` / `"moderate"` / `"minimal"`，与文档一致。映射关系：

| 旧值（已确认） | 新 motion_level | 新 motion_profile |
|---|---|---|
| `"rich"` | `expressive` | `pitch` / `product`（按 context 区分） |
| `"moderate"` | `subtle` | `tech` |
| `"minimal"` | `subtle` | `academic` / `presenter` |

> 旧字段保留在 visual candidate 数据结构中，新字段作为附加字段写入 `brief-confirmed.json` 的 `html_config` 子对象，不覆盖旧字段。

---

## 8. html-ppt-skill 内部化策略

**原则**：不安装、不导入、不直接调用 `lewislulu/html-ppt-skill` 的代码。只吸收其设计知识，内化为本项目的参考 catalog。

**理由**：
- 外部依赖引入维护成本和版本风险
- 本项目的 HTML 路径已有 Reveal.js 5.1.0，功能足够
- 知识内化后可根据本项目设计语言自由定制

### 8.1 新增内部 Catalog 文件

```
skills/deck-builder/references/
  html-theme-catalog.md      ← 主题风格知识库
  html-layout-catalog.md     ← 布局类型知识库
  html-animation-catalog.md  ← 动画类型知识库
```

### 8.2 `html-theme-catalog.md` 内容框架

记录每个主题的：设计语言、调色盘、字体组合、适用场景、HTML 实现要点（CSS 变量名、关键 class）。

主题清单（初版）：

| 主题 key | 名称 | 对应 design-lock |
|---|---|---|
| `swiss-modernist` | 瑞士国际主义 | swiss-klein-blue |
| `engineering-dark` | 工程暗色 | linear-dark |
| `editorial-warm` | 暖纸叙事 | editorial |
| `academic-indigo` | 靛蓝学术 | academic |
| `notion-minimal` | 暖白极简 | notion-warm |
| `tokyo-night` | Tokyo Night | — |
| `blueprint` | Blueprint 蓝图 | — |
| `pitch-deck-vc` | VC 路演 | — |
| `magazine-bold` | 杂志大胆 | — |
| `academic-paper` | 学术论文风 | — |

### 8.3 `html-layout-catalog.md` 内容框架

记录每种布局的：适用内容类型、Reveal.js section 结构、关键 CSS 类、与 PPTX layout 的映射关系。

布局清单（初版）：

| 布局 key | 用途 |
|---|---|
| `cover` | 封面 |
| `section-divider` | 章节切换页 |
| `title-body` | 标题 + 正文 |
| `three-column` | 三列对比 |
| `timeline` | 时间线 |
| `roadmap` | 路线图 |
| `kpi-grid` | 数字大字 / KPI |
| `arch-diagram` | 架构图 |
| `flow-diagram` | 流程图 |
| `image-hero` | 图片主视觉 |
| `quote-card` | 引言/金句 |
| `end-slide` | 结束页 / 致谢 |

### 8.4 `html-animation-catalog.md` 内容框架

记录每种动画的：触发方式、CSS/JS 实现方式、Reveal.js Fragment class、适用 motion_level。

动画清单（初版）：

| 动画 key | 触发 | 适用 level |
|---|---|---|
| `fade-up` | entry | subtle+ |
| `rise-in` | entry | subtle+ |
| `stagger-list` | entry，逐项显示 | subtle+ |
| `counter-up` | entry，数字滚动 | expressive+ |
| `path-draw` | entry，SVG 路径描绘 | expressive+ |
| `typewriter` | entry，打字机效果 | expressive+ |
| `css-spotlight` | 封面 CSS 径向光晕动画 | cinematic（仅封面/章节/结束）|
| `canvas-particles` | 持续，粒子场（WebGL）| ⏳ 未来能力，当前不实现 |
| `canvas-wave` | 持续，波浪场（WebGL）| ⏳ 未来能力，当前不实现 |

---

## 9. guard 和 prompt-templates 更新要点

> 本节列出需要更新的文件和核心规则，具体修改内容在阶段 3 执行。

### 9.1 `presentation_director.py` guard 逻辑

需要新增的检查项：

```python
# validate_generation_guard() 中新增：

# 旧 brief 迁移：absent image_generation_mode = 预日期，跳过所有图片门禁
image_generation_mode = brief.get("image_generation_mode")  # None if absent
if image_generation_mode is None:
    pass  # 旧 brief，不检查图片门禁
else:
    # Image Style Gate 对所有 mode 必须完成（包括 none 和 post-v1-slot-review）
    if not status_exists("images-style.ready"):
        raise GuardError("Image Style Gate not completed — run serve-wait --for images-style first")

    # 失败策略：Retry-2-then-stop（检查 final_status，不检查单次 attempt）
    if any_asset_final_status_failed():  # reads final_status field, ignores attempts[]
        raise GuardError(
            "Image generation failed after retries — see image-assets.json final_status. "
            "Fix the failure or change image_generation_mode to none before proceeding."
        )

    # post-v1 gate：仅当 v1 preview artifact 已存在时才强制检查
    if image_generation_mode in ("post-v1-slot-review", "hybrid"):
        if v1_preview_exists() and not status_exists("images-placement.ready"):
            raise GuardError("Image Placement Gate not completed — run serve-wait --for images-placement first")
```

> `v1_preview_exists()` 的实现取决于输出格式（见 §3.2）：PPTX 检查 `v1/contact-sheet.png`，HTML 检查 `v1/screenshots/` 或 `v1/final.html`。

### 9.1b PPTX prompt 对 html_config 的处理

`initial_prompt()` 当前（第 2830-2831 行）将整个 `brief-confirmed.json` 原样 `json.dumps` 写入 prompt。新字段（`html_motion_level`、`html_motion_profile`、`html_config`）会随之出现在 PPTX 生成指令里，造成污染。

**解决方案**：在 PPTX prompt 的 hard requirement / PPTX rules 段显式添加：

```
- Ignore the following fields from the confirmed brief: html_config, html_motion_level,
  html_motion_profile, html_animation, html_transition, html_gradient.
  These are HTML-only settings and must not affect PPTX layout, animation, or style.
```

（不过滤 JSON，而是用 prompt 规则覆盖，修改量最小，不影响 HTML 路径的 brief 完整性。）

---

### 9.1c `initial_prompt()` 必须同步修改（第 2923 行）

当前 `initial_prompt()` 在 PPTX 生成完 v1 后，直接在 prompt 里注明"run serve-wait --for revision"（style-review 路径）。新流程要求：

- 若 `image_generation_mode` 为 `post-v1-slot-review` 或 `hybrid`，v1 完成后必须先走 Image Placement Gate，再进入 Style Review
- 修改：在 PPTX prompt 的末尾（当前第 2923 行附近），根据 `image_generation_mode` 值插入条件分支：
  ```
  After v1 is complete:
  - If image_generation_mode in (post-v1-slot-review, hybrid):
      run: serve-wait --for images-placement --open-page image-placement
      then: execute post-v1 image generation and insertion (see image-placement-request.json)
      then: re-render v2 preview artifact（PPTX: v2/contact-sheet.png；HTML: v2/screenshots/*.png）
  - Then: run serve-wait --for revision --open-page style-review
  ```

---

### 9.2 `CONTEXT.md` 需新增术语

- `image_policy`：安全边界，Intake 阶段声明
- `image_generation_mode`：执行动作，Image Style Gate 声明
- `Image Style Gate`：Brief 确认后的图片模式选择门禁
- `Image Placement Gate`：v1 preview artifact（PPTX: contact sheet；HTML: screenshots）就绪后的逐页槽位确认门禁
- `image-plan.json`：生图计划文件
- `image-assets.json`：生图执行记录（含失败记录）
- `image-placement-request.json`：v1 后槽位确认结果
- `html_motion_level`：HTML 动效强度（subtle/expressive/cinematic）
- `html_motion_profile`：HTML 动效风格（presenter/academic/tech/pitch/product/editorial）

### 9.3 `prompt-templates.md` 需新增

Template A0 中，在 `serve-wait --for confirmed` 之后，补充：

```bash
# Image Style Gate（serve-wait 会同时启动 server 并打开页面等待用户操作）
python3 scripts/presentation_director.py serve-wait --task "slug" \
    --for images-style --open-page image-style

# 若 image_generation_mode != none，执行生图（读取 image-plan.json，写入 image-assets.json）
# 失败时重试 2 次，仍失败则停止，不降级为 CSS 渐变

# 生成 v1（含已生成图片的路径引用）
# ... Codex Presentations / guard → v1/final.pptx + v1/contact-sheet.png (pptx)
#                                   or v1/final.html (html-revealjs) ...

# Image Placement Gate
# 前提：v1 preview artifact 已就绪（output_format 决定检查物，见 §3.2）
# open-page image-placement 命令内部做 preview 存在性检查，不存在则报错
python3 scripts/presentation_director.py serve-wait --task "slug" \
    --for images-placement --open-page image-placement
# 执行 placement 生图 → 产出 v2（PPTX: targeted edit → v2/final.pptx；HTML: 重生成 → v2/final.html）
```

> **注意**：`open-page` 命令要求 server 已在运行；`serve-wait` 同时负责启动 server 和等待。新 Gate 的 `--open-page` 值（`image-style` / `image-placement`）和 `--for` 值（`images-style` / `images-placement`）需在代码中注册（`PAGE_PATHS` 和 `STATUS_FILES` 字典），这是阶段 1a/3a 的实现任务。

---

## 10. 审查问题自答

### Q1：`image_policy` 和 `image_generation_mode` 是否分得足够清楚？

**是的，但有一个初稿错误已修正**。

分离清晰：policy 在 Intake 阶段声明，是权限边界；mode 在 Image Style Gate 决定，是执行动作。

**初稿错误**：设计文档一开始写的 policy 枚举（`none/cover-section/background/more-ai-concept`）与代码实际值不符。代码实际枚举是 `none/abstract-only/cover-section/ask-before-use/custom`（已核实第 585 行）。文档已改为保持现有枚举不变，通过迁移映射表连接到新的 `image_generation_mode`。

`ask-before-use` 是本次重构的核心：它从一个含糊的"每张前询问"变成了清晰的 `post-v1-slot-review`（v1 preview artifact 就绪后才进行逐页确认，PPTX 路径是 contact sheet，HTML 路径是 screenshots）。

**Image Style Gate UI 要求**：必须显示当前 `image_policy` 值，让用户在选 mode 时看到自己之前设定的边界。兼容性约束在后端校验，guard 再验证一次。

---

### Q2：`post-v1-slot-review` 是否真的避免了"没看到 PPTX 就逐张确认"的问题？

**是的，前提是执行顺序有强制约束**。

`post-v1-slot-review` Gate 的触发条件是 **v1 preview artifact 已就绪**（不同 output_format 有不同检查物）：

| output_format | 检查物 |
|---|---|
| `pptx` | `v1/contact-sheet.png` 存在 |
| `html-revealjs` | `v1/final.html` 存在（可辅以 `v1/screenshots/` 截图） |
| `both` | `v1/contact-sheet.png` 存在（PPTX 为主） |

`open-page --page image-placement` 命令应硬编码检查对应 output_format 的 preview artifact，不存在时返回错误并提示"请先完成 v1 渲染"。不能只靠 prompt 约定。

---

### Q3：生图失败是否会被记录，而不是静默跳过？

**采用策略 B：Retry-2-then-stop**（guard 伪代码已按此更新）。

两条原始规定均需满足：
1. "记录失败" → 写入 `image-assets.json` attempts[]，并在重试完成后更新 final_status
2. "不能静默退化成 CSS 渐变" → 重试 2 次后仍失败则 guard 抛出错误，停止流程，不产生占位渐变

**执行细节**：
- 生图脚本层：每次调用 API 后立即写 `image-assets.json`，失败记 `status: "failed" + error_message`，不 `except: pass`
- 重试逻辑：最多 2 次重试（共 3 次调用），每次重试间隔 3–5 秒
- 2 次重试后仍 failed → guard 读到 failed 条目 → 抛出 GuardError → 流程停止，提示用户检查 API key / 网络 / 改用 mode=none
- 旧文档（`docs/ai-background-image.md`）没有失败处理说明，阶段 3 需要补充

---

### Q4：HTML 动效是否只影响 HTML 路径，不污染 PPTX 可编辑路径？

**设计上是隔离的，但需要在 schema 层明确声明**。

`html_motion_level` 和 `html_motion_profile` 两个字段：
- 只写入 `brief-confirmed.json` 中的 `html_config` 子对象
- PPTX 生成 prompt 模板（prompt-templates.md 的 Template A）不引用这两个字段
- HTML 生成 prompt 模板（Template C）引用这两个字段

**需要在 `CONTEXT.md` 中明确写明**：PPTX 路径不读取 `html_motion_level`；HTML 路径不承诺输出可编辑 `.pptx`。两条路径的产物是独立的。

**当前风险**：`initial_prompt()` 将整个 `brief-confirmed.json` 原样 dump 进 prompt（第 2831 行），包括 `html_config`、`html_animation` 等字段。选择的修复方式是"在 PPTX hard requirement / PPTX rules 段加显式 ignore 指令"（不过滤 JSON），因此这些字段**仍然会出现在 PPTX prompt 的 JSON 片段里**——隔离靠的是 prompt 规则层，不是数据层。验证方式不能是"检查 prompt 是否不含这些字段"，应改为"检查 PPTX prompt 包含 ignore rule"（见验证清单）。

---

### Q5：是否避免直接依赖外部 `html-ppt-skill`？

**设计上已经避免，catalog 方案是正确的**。

三个 catalog 文件（theme/layout/animation）将外部知识内化为本项目的参考文档，不引入任何外部代码依赖。Reveal.js 5.1.0 已是本项目的既有依赖，HTML 输出能力来自 Reveal.js，不来自 `html-ppt-skill`。

**需要注意的是**：catalog 文件只是参考，不是代码。HTML 生成 prompt 需要引用 catalog 中的具体值（theme key、layout key、animation key），这意味着 Template C 需要相应升级，能够根据 `html_motion_level` + `html_motion_profile` 组合选择合适的 theme/layout/animation 组合。这个映射逻辑需要在 Template C 中明确写出，否则 catalog 会变成死文档。

---

## 11. 代码修改目标文件说明

**`presentation_director.py` 有两个副本，但只有一个是源文件**（已通过 diff 验证）：

- `skills/deck-builder/scripts/presentation_director.py` — **源文件，3498 行，所有修改目标此处**
- `scripts/presentation_director.py` — **薄包装器（15 行）**，通过 `runpy.run_path()` 调用上面的源文件

因此：
- 所有代码修改针对 `skills/deck-builder/scripts/presentation_director.py`
- 调用方式（`python3 scripts/presentation_director.py`）不变，包装器自动转发
- 不需要运行 `install.sh` 来同步，两个文件不是副本关系

---

## 12. 实施顺序建议（供 Claude 审查后确认）

| 步骤 | 内容 | 文件 | 验证方式 |
|---|---|---|---|
| 0 | 本设计文档审查 | 本文件 | Claude 审查通过 |
| 1a | 新增 Image Style Gate HTML 页面 | `presentation_director.py` | `py_compile` + 浏览器打开 |
| 1b | 实现 `images-style.ready` 状态信号 | `presentation_director.py` | `wait --for images-style` 测试 |
| 1c | 实现 `image-plan.json` 写入 | `presentation_director.py` | 检查 JSON 结构 |
| 2 | 实现 pre-v1 生图 + `image-assets.json` 写入 | 新脚本或 director 子命令 | 生成测试图，检查 JSON |
| 3a | 新增 Image Placement Gate HTML 页面 | `presentation_director.py` | `py_compile` + 浏览器打开 |
| 3b | v1 preview artifact 存在性前置检查（按 output_format）| `presentation_director.py` | preview 未就绪时命令返回明确错误 |
| 3c | 实现 `image-placement-request.json` 写入 | `presentation_director.py` | 检查 JSON 结构 |
| 4 | 更新 guard 逻辑 | `presentation_director.py` | 缺少 ready 文件时 guard 失败 |
| 5 | 更新 CONTEXT.md 术语 | `CONTEXT.md` | 人工审查 |
| 6 | 更新 SKILL.md 流程描述 | `SKILL.md` | 人工审查 |
| 7 | 更新 prompt-templates.md | `prompt-templates.md` | 用测试 brief 跑完整流程 |
| 8 | 写三个 HTML catalog 文件 | `html-theme/layout/animation-catalog.md` | 人工审查 |
| 9 | 升级 HTML 输出 schema | `presentation_director.py` + Template C | HTML 动效测试（浏览器） |
| 10 | 全流程端到端测试 | 全部 | 见阶段 6 验证清单 |

---

## 13. 阶段 6 验证清单

- [ ] `python -m py_compile skills/deck-builder/scripts/presentation_director.py` 通过
- [ ] Image Style Gate 页面在本地浏览器可正常打开，选择后产生 `image-plan.json` 和 `images-style.ready`
- [ ] `image_generation_mode = global-background` 时，生成后存在 `image-assets.json`，含 attempts[] 与 final_status 字段
- [ ] 生图失败（3 次 attempt 全部失败）时，`image-assets.json` 中 `final_status = "failed"`，guard 抛出 GuardError；pre-v1 失败写 stderr / guard message，不依赖尚未存在的 `qa-summary.md`
- [ ] Image Placement Gate 在 v1 preview artifact 未就绪时打开失败，有明确错误提示（PPTX 检查 contact-sheet.png，HTML 检查 v1/final.html）
- [ ] Image Placement Gate 在 v1 preview artifact 就绪后正常打开，产生 `image-placement-request.json` 和 `images-placement.ready`
- [ ] post-v1 生图完成后产生 v2 输出（PPTX: v2/final.pptx + v2/contact-sheet.png；HTML: v2/final.html）
- [ ] `image_policy = none` 时，Image Style Gate 只显示 `mode = none` 选项
- [ ] `image_policy = ask-before-use` 时，Image Style Gate 默认推荐 `mode = post-v1-slot-review`
- [ ] Image Style Gate 对所有 mode（含 none、post-v1-slot-review）均产生 `images-style.ready`
- [ ] 图片生成失败 2 次重试后，guard 返回 GuardError，流程停止，无 CSS 渐变占位进入输出
- [ ] v2 contact sheet 在 post-v1 生图插入后重新渲染，Style Review 展示的是 v2
- [ ] PPTX 生成 prompt 的 PPTX rules 段包含显式 ignore 指令（覆盖 html_config、html_motion_level 等字段）
- [ ] HTML 生成 prompt 中 `html_motion_level = cinematic` 只对封面/章节/结束页启用 CSS 动画强化版，无 Canvas FX（WebGL）代码生成
- [ ] HTML 页面无内容溢出，speaker notes 正常显示
