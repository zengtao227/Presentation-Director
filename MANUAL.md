# Presentation Director 使用手册

> 版本对应：`codex/html-theme-image-wiring` 分支，2026-06

---

## 目录

1. [项目简介](#1-项目简介)
2. [安装与环境](#2-安装与环境)
3. [核心工作流程](#3-核心工作流程)
4. [Presentation Director CLI 参考](#4-presentation-director-cli-参考)
5. [AI 图片工作流](#5-ai-图片工作流)
6. [视觉方向系统](#6-视觉方向系统)
7. [质量门禁](#7-质量门禁)
8. [常见问题与故障排查](#8-常见问题与故障排查)

---

## 1. 项目简介

### 这个项目解决什么问题

直接让 AI 生成 PPT 的最大问题是：AI 在不知道"为什么做"的情况下拍板了"长什么样"。结果是一份有格式但没论点、有图表但没逻辑的幻灯片。

Presentation Director 在生成之前插入一个结构化的决策层：

- **Intake 收集**：听众、目标、内容语言、输出格式、AI 图片许可
- **Research Strategy**：选择资料来源策略（纯提供资料 / Codex 联网 / 外部 Deep Research）
- **Visual Inspiration**：根据主题自动推荐 3 个视觉候选，用户点选
- **Brief 确认**：所有决策写入 `brief-confirmed.json`，用户在浏览器点击确认
- **Image Gate**（可选）：AI 图片风格和主题的独立确认
- **生成路由**：根据 `output_format` 路由到正确的生成引擎

这个流程不生成幻灯片本身，它是生成之前的"设计合同"。

### 三种输出模式

| 模式 | 引擎 | 适合场景 |
|------|------|----------|
| `pptx` | Codex Presentations（artifact-tool） | 需要在 PowerPoint 中继续编辑 |
| `html-revealjs` | Reveal.js 5.1.0 直写 | 浏览器演示、动画过渡、presenter mode、`?print-pdf` 导出 |
| `both` | 两者并行 | 同时交付可编辑 PPTX 和浏览器版本 |

PPTX 模式**必须**在 Codex 环境下使用 Presentations 插件，不支持 python-pptx 或 pptxgenjs 降级。HTML 模式在任何有 Python 的环境下均可运行。

---

## 2. 安装与环境

### 前提条件

- Python 3.10+
- Node.js（用于 PPTX 生成路径的 `build_artifact_deck.mjs`）
- Codex Desktop（PPTX 路径）或普通终端（HTML 路径）

### 本地安装

```bash
# 从仓库根目录运行
bash install.sh
```

这会把 `skills/deck-builder` 和 `skills/ui-ux-pro-max` 复制到：
- `~/.claude/skills/`（Claude Code 全局）
- `~/.codex/skills/`（Codex，如果目录存在）

安装后，Claude Code 和 Codex 可以识别 `deck-builder` skill。

### 同步到远程 VPS

```bash
bash install.sh --remote
```

默认同步到 `frank` 主机（需要 SSH 免密配置）。修改 `install.sh` 中的 `REMOTE_HOSTS` 可以增加目标。

### AI 图片后端（可选）

| 后端 | 环境变量 | 费用 |
|------|----------|------|
| HuggingFace FLUX.1-schnell | `HF_TOKEN` | 免费（需注册） |
| OpenAI DALL-E 3 | `OPENAI_API_KEY` | ~$0.04/张 |
| fal.ai Flux | `FAL_KEY` | ~$0.003/张 |
| stub（纯色 PNG） | 无 | 免费，仅测试用 |

```bash
export HF_TOKEN=hf_your_token_here
```

---

## 3. 核心工作流程

### 完整流程图

```
用户提出 PPT 需求
        │
        ▼
┌─────────────────┐
│  1. init        │  创建 PPTX/<task-slug>/ 工作区
│                 │  生成 intake HTML 页面
│                 │  自动打开浏览器
└────────┬────────┘
         │ 用户在浏览器填写 intake
         ▼
┌─────────────────┐
│  2. serve-wait  │  启动本地服务器
│  --then-guard   │  等待用户点击「确认」
│                 │  guard 通过后写入 guard-passed.ready
└────────┬────────┘
         │ 用户完成 Visual Inspiration 选择 + 点击确认
         ▼
┌─────────────────┐
│  3. guard       │  验证 brief-confirmed.json
│                 │  检查 output_format、topic 等必填项
│                 │  通过后给出生成信号
└────────┬────────┘
         │ guard 通过
         ▼
  ┌──────┴──────┐
  │             │
  ▼             ▼
image_policy   image_policy
= none         需要 AI 图片
  │             │
  │             ▼
  │    ┌─────────────────┐
  │    │ 4. image-style  │  图片风格+HTML主题选择
  │    │  serve-wait     │  --for images-style
  │    └────────┬────────┘
  │             │
  └──────┬──────┘
         ▼
┌─────────────────┐
│  5. 生成        │  根据 output_format 路由：
│                 │  html → Reveal.js 直写
│                 │  pptx → Codex Presentations
│                 │  both → 两路并行
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  6. guard       │  生成后再次运行 guard
│  + QA           │  验证图片注册、prompt 匹配
└─────────────────┘
```

### 每个阶段的 HTML 页面

| 阶段 | 页面路径 | 等待信号 | 写入内容 |
|------|----------|----------|----------|
| Intake + Visual | `/` (intake) | — | 不等，用户填完进入确认 |
| Visual Inspiration | `/visual-inspiration` | — | 候选选择写入 brief |
| Brief 确认 | `/confirm` | `confirmed.ready` | `brief-confirmed.json` |
| Guard 通过 | `serve-wait --then-guard` | `guard-passed.ready` | `GUARD_PASSED` + generation prompt |
| 图片风格 + HTML 主题 | `/image-style` | `images-style.ready` | `html_theme_key`、`image_generation_mode` |
| 修订选择 | `/compare` | `images-style.ready` | 用户选择 v1/v2 继续 |

**重要**：agent 不能替用户点击确认。只有用户在浏览器点击后，`confirmed.ready` 才会写入；只有 guard 通过并写入 `guard-passed.ready` 后，agent 才能开始生成。

### 典型命令序列（HTML 输出）

```bash
PD="python3 skills/deck-builder/scripts/presentation_director.py"
BASE="."
TASK="my-deck"

# Step 1: 初始化工作区
$PD --base-dir "$BASE" init \
  --task "$TASK" \
  --topic "量化策略年终回顾" \
  --conversation-text "帮我做一个 PPT"

# Step 2: 等待用户在浏览器确认，并自动运行 guard
$PD --base-dir "$BASE" serve-wait \
  --task "$TASK" \
  --for confirmed \
  --then-guard

# Step 4: （如需 AI 图片）等待图片风格确认
$PD --base-dir "$BASE" serve-wait \
  --task "$TASK" \
  --for images-style

# Step 5: 获取生成 prompt
$PD --base-dir "$BASE" prompt \
  --task "$TASK" \
  --kind initial
```

---

## 4. Presentation Director CLI 参考

所有命令共用全局参数：

```bash
python3 presentation_director.py --base-dir <仓库根> <subcommand> --task <slug> [...]
```

`--base-dir` 默认为 `.`（当前目录）。任务工作区固定在 `<base-dir>/PPTX/<task-slug>/`。

---

### `init`

创建任务工作区，生成 intake HTML 页面，并在浏览器中打开。

```bash
python3 presentation_director.py --base-dir . init \
  --task "my-deck" \
  --topic "主题（可选）" \
  --source "docs/report.md" \
  --source "https://example.com/article" \
  --conversation-text "用户最近说的话（用于 UI 语言自动检测）" \
  --no-open    # 可选，不自动打开浏览器
```

| 参数 | 说明 |
|------|------|
| `--task` | 任务标识符，会作为目录名 `PPTX/<task>/` |
| `--topic` | 可选的初始主题，写入 brief |
| `--source` | 可重复，资料路径或 URL |
| `--conversation-text` | 用于自动检测 UI 语言（中/英） |
| `--no-open` | 只生成 HTML，不打开浏览器 |

---

### `serve` / `serve-wait`

`serve` 启动本地 HTTP 服务器（默认 `127.0.0.1:8765`）。  
`serve-wait` 在 `serve` 基础上等待指定状态文件出现后退出。

```bash
# 等待 brief 确认
python3 presentation_director.py --base-dir . serve-wait \
  --task "my-deck" \
  --for confirmed \
  --then-guard \
  --timeout 600

# 等待图片风格门禁确认
python3 presentation_director.py --base-dir . serve-wait \
  --task "my-deck" \
  --for images-style
```

| `--for` 值 | 等待文件 | 触发时机 |
|------------|----------|----------|
| `confirmed` | `confirmed.ready` | 用户点击 Brief 确认页的「确认」 |
| `guard-passed` | `guard-passed.ready` | `serve-wait --then-guard` 验证通过，可以开始生成 |
| `images-style` | `images-style.ready` | 用户点击图片风格门禁的「保存」 |

---

### `wait`

纯等待，不启动服务器（适合服务器已在其他进程运行的情况）。

```bash
python3 presentation_director.py --base-dir . wait \
  --task "my-deck" \
  --for confirmed \
  --interval 2
```

---

### `guard`

验证任务是否可以进行生成。失败时返回码 `2`，打印具体错误到 stderr。

```bash
python3 presentation_director.py --base-dir . guard --task "my-deck"
# 返回码 0 = 通过
# 返回码 2 = 失败（brief 未确认 / prompt 已变更等）
```

guard 检查内容：
- `brief-confirmed.json` 存在且包含必填字段
- `confirmed.ready` 存在（用户点击确认）
- 当 `image_generation_mode` 为 pre-v1 时，`image-plan.json` 中所有 active 目标已 `final_status: success`
- 图片 prompt 与 plan 中的 `prompt_draft` 匹配（若已生成）

交互式自动流程应优先使用 `serve-wait --for confirmed --then-guard`。该命令在 guard 通过后写入 `status/guard-passed.ready` 并 flush `GUARD_PASSED`；跨 AI 工具应把这个文件视为“开始生成”的权威信号。

---

### `prompt`

打印交给生成引擎的 handoff prompt。agent 应先 guard 通过，再调用此命令获取 prompt。

```bash
python3 presentation_director.py --base-dir . prompt \
  --task "my-deck" \
  --kind initial    # 或 revision
```

输出是一段完整的指令文本，包含：output_format、视觉配置、图片要求、Reveal.js CSS token 合约、speaker notes 要求等。

---

### `render`

重新从当前 JSON 状态生成 HTML 页面（不需要重跑 init）。

```bash
python3 presentation_director.py --base-dir . render \
  --task "my-deck" \
  --open-page confirm    # 可选，生成后直接打开指定页面
```

可用 `--open-page` 值：`intake`、`visual-inspiration`、`confirm`、`image-style`、`compare`

---

### `open-page`

在已运行的服务器上打开指定页面。

```bash
python3 presentation_director.py --base-dir . open-page \
  --task "my-deck" \
  --page confirm
```

---

### `image-asset`

记录一次 AI 图片生成结果到 `image-assets.json`。通常由 `generate_images.py` 内部调用，不需要手动执行。

```bash
python3 presentation_director.py --base-dir . image-asset \
  --task "my-deck" \
  --target-id "cover-background" \
  --prompt "Abstract dark blue texture..." \
  --output-path "PPTX/my-deck/assets/images/cover-background.png" \
  --status success
```

---

### `share-html`

把 per-slide PNG 预览拼成一个静态 HTML 伴随文件（view-only，不需要 Reveal.js）。

```bash
python3 presentation_director.py --base-dir . share-html \
  --task "my-deck" \
  --version v1 \
  --title "年终回顾"
# 输出到 PPTX/my-deck/final/年终回顾.html
```

---

## 5. AI 图片工作流

`generate_images.py` 负责 AI 图片的生成和注册。它读取 `PPTX/<task>/image-plan.json` 中的 `pre-v1` 目标，生成或注册图片，再通过 `image-asset` 子命令记录到 Director。

### 自动后端

```bash
GI="python3 skills/deck-builder/scripts/generate_images.py"
TASK_DIR="PPTX/my-deck"

# Hugging Face FLUX（免费，需 HF_TOKEN）
$GI --task-dir "$TASK_DIR" --api hf

# OpenAI DALL-E 3（需 OPENAI_API_KEY）
$GI --task-dir "$TASK_DIR" --api dall-e-3

# fal.ai Flux（需 FAL_KEY）
$GI --task-dir "$TASK_DIR" --api flux

# 纯色 PNG，用于测试流程
$GI --task-dir "$TASK_DIR" --api stub
```

生成失败时最多重试 3 次，全部失败后以退出码 1 退出。

### 手动工作流（推荐零成本方案）

适合不想配置 API key 的情况。

**Step 1：展示 prompt**

```bash
$GI --task-dir "$TASK_DIR" show
```

输出每个目标的提示词、目标 ID 和保存路径，方便复制到免费工具。

**Step 2：用免费工具生成图片**

| 工具 | 地址 | 特点 |
|------|------|------|
| Microsoft Copilot | copilot.microsoft.com | DALL-E 3，免费额度大 |
| Google ImageFX | aitestkitchen.withgoogle.com/tools/image-fx | 免注册 |
| Adobe Firefly | firefly.adobe.com | 25 免费积分/月 |
| Ideogram | ideogram.ai | 免费层质量好 |
| Leonardo.ai | leonardo.ai | 每日免费积分 |

**Step 3：注册图片**

```bash
# 方式 A：注册单张图片
$GI --task-dir "$TASK_DIR" place \
  --source ~/Downloads/cover.png \
  --target-id cover-background

# 方式 B：批量注册
$GI --task-dir "$TASK_DIR" place \
  --sources '{"cover-background":"~/Downloads/cover.png","section-bg":"~/Downloads/section.png"}'

# 方式 C：扫描（图片已按计划路径放好）
$GI --task-dir "$TASK_DIR" place
```

**注意**：`--source` 和 `--sources` 不能同时使用。

**Step 4：Guard 验证**

```bash
python3 presentation_director.py --base-dir . guard --task "my-deck"
```

Guard 会检查所有 active 目标的 `final_status: success`。通过后才能继续生成。

### `--api prompt-only`：导出 prompt 文件

```bash
$GI --task-dir "$TASK_DIR" --api prompt-only
# 写入 PPTX/my-deck/image-prompts.md
```

---

## 6. 视觉方向系统

### HTML 主题（15 个）

在 Image Style Gate 中选择，写入 `brief-confirmed.json` 的 `html_config.theme_key`。

| `theme_key` | 适用场景 |
|-------------|----------|
| `auto` | 跟随 Visual Inspiration 自动推断（推荐） |
| `minimal-white` | 产品内部、安静商业 deck |
| `editorial-serif` | 叙事、文化、长篇解说 |
| `swiss-grid` | 结构化报告、运营、精确对比 |
| `corporate-clean` | 董事会、咨询、高管汇报 |
| `academic-paper` | 研究、临床、医学、循证型 deck |
| `blueprint` | 架构、系统、技术解说 |
| `engineering-whiteprint` | 工程方案，更轻的技术底色 |
| `terminal-green` | 开发者、安全、CLI、基础设施叙事 |
| `pitch-deck-vc` | 投资人、融资、市场规模、路演 |
| `news-broadcast` | 实时简报、体育/新闻分析、快速事实 |
| `magazine-bold` | 编辑发布、品牌故事、大开篇 |
| `aurora` | 科学、能源、AI、前沿技术叙事 |
| `glassmorphism` | 产品、工作室、高端品牌、软深度 |
| `cyberpunk-neon` | 未来感 demo、高能概念 |

主题实现为 CSS custom properties，agent 在 `<style>` 中定义：

```css
:root {
  --deck-bg: /* 主背景 */;
  --deck-ink: /* 正文颜色 */;
  --deck-muted: /* 次要文字 */;
  --deck-accent: /* 强调色 */;
  --deck-accent-2: /* 第二强调色 */;
  --deck-line: /* 分割线颜色 */;
}
```

### CSS 安全区合约（HTML 输出）

每张幻灯片必须遵守：

```css
/* 普通内容区 */
.slide-safe {
  position: absolute;
  left: 54px; top: 70px;
  width: 1172px; height: 590px;
}

/* 全出血背景 */
.bleed {
  position: absolute;
  inset: 0;
}
```

**规则**：所有文字、图表、表格、截图、代码块必须在 `.slide-safe` 内。AI 生成的背景图片用 `.bleed`。不得出现内容溢出 `.slide-safe` 的情况。

### Design Lock 系统（PPTX 路径）

设计档案保存在 `design-locks/`，提供稳定的颜色、字体和版式约束：

| 文件 | 风格 | 适合场景 |
|------|------|----------|
| `swiss-klein-blue.md` | 瑞士国际主义，Klein Blue | 商业计划、产品路线、竞赛答辩 |
| `linear-dark.md` | Linear 暗色，工程精准感 | SaaS、技术平台、投资人 deck |
| `academic.md` | 靛蓝学术，冷调研究感 | 技术方案、数据报告、AI 产品 |
| `editorial.md` | 暖纸叙事，编辑感 | 路演、课程汇报、观点型叙事 |
| `notion-warm.md` | Notion 暖白，亲和极简 | 内部文档、文化类、轻量展示 |

install.sh 会把 `design-locks/` 一起复制到技能目录，agent 可以在 `deck-builder` skill 中直接引用。

### Layout Families（根据 Deck 类型自动选择）

`html_config.layout_families` 由 deck 的主题和类型自动推导：

| Deck 类型 | 推荐 Layout 序列 |
|-----------|-----------------|
| pitch（投融资） | cover-hero → stat-highlight → kpi-grid → claim-bullets → cta-close |
| engineering（工程） | cover-hero → architecture-map → flow-diagram → code-terminal → timeline |
| research（研究） | cover-hero → claim-bullets → evidence-table → chart-bar-line → big-quote |
| product（产品） | cover-hero → process-steps → diff-before-after → kpi-grid → cta-close |
| default（通用） | cover-hero → claim-bullets → two-column-proof → chart-bar-line → cta-close |

同一 layout family 不得连续出现 3 张及以上。

---

## 7. 质量门禁

### Gate 1 — Content Gate（内容门禁）

在 `deck.md` 写完后、生成前检查：

- 每张幻灯片标题是结论句，不是主题标签
- 每张幻灯片有且只有一个 proof object（图表/数字/案例/引用）
- 每个数字有来源，或标注为 `[missing]`
- 无编造数据

### Gate 2 — Design Gate（设计门禁）

生成后、Render QA 前检查：

- `deck.md` 中有 `## Design Contract` 块，注明选用的 design lock
- 所有颜色在 lock 的色板范围内
- 字体和层级符合 lock 约束
- 无 3 张及以上连续相同版式

### Gate 3 — Render Gate

生成后必须检查：

**PPTX**：每张幻灯片有 PNG 预览；contact sheet 存在；内容在安全区内。  
**HTML**：浏览器打开无 JS 报错；16:9 无溢出；按 `S` 可打开 Speaker Notes 面板；`?print-pdf` 输出可用。

### Guard 命令返回码

```bash
python3 presentation_director.py --base-dir . guard --task "my-deck"
# 返回 0：所有检查通过，可以生成
# 返回 2：失败，stderr 有具体错误列表
```

Guard 失败的常见原因：
- `brief-confirmed.json` 不存在 → 需要先完成 init + serve-wait
- `confirmed.ready` 不存在 → 用户还未点击浏览器确认
- AI 图片 target 未全部 `success` → 先完成图片注册再运行 guard
- 图片 prompt 与 plan 不匹配 → 重新生成图片

---

## 8. 常见问题与故障排查

### Q：Codex 里找不到 Presentations 插件

先检查 bundled runtime：

```bash
ls $HOME/.codex/plugins/cache/openai-primary-runtime/presentations/*/skills/presentations
```

如果路径存在，设置 `SKILL_DIR` 指向它，然后运行：

```bash
node "$SKILL_DIR/scripts/check_presentation_runtime.mjs" --workspace "$WORKSPACE"
```

只有 UI 不可见不代表 Presentations 不存在。只有 `check_presentation_runtime.mjs` 报告缺失，才允许停止并告知用户。**不要降级到 python-pptx、pptxgenjs 或 Google Slides。**

### Q：没有 HF_TOKEN，也不想付费

使用手动工作流：

```bash
# 展示 prompt
python3 generate_images.py --task-dir PPTX/my-deck show

# 把 prompt 粘贴到 Copilot / Ideogram / Firefly 生成图片
# 下载后注册
python3 generate_images.py --task-dir PPTX/my-deck place \
  --source ~/Downloads/image.png \
  --target-id cover-background
```

或者导出为 prompt 文件：

```bash
python3 generate_images.py --task-dir PPTX/my-deck --api prompt-only
# 写入 PPTX/my-deck/image-prompts.md
```

### Q：guard 报 "prompt changed — regenerate"

`image-plan.json` 中的 `prompt_draft` 被修改过，但已注册的图片是用旧 prompt 生成的。
解决方法：删除旧图片，重新生成或重新注册：

```bash
rm PPTX/my-deck/assets/images/cover-background.png
python3 generate_images.py --task-dir PPTX/my-deck place \
  --source ~/Downloads/new-image.png \
  --target-id cover-background
python3 presentation_director.py --base-dir . guard --task my-deck
```

### Q：`--sources` 和 `--source` 同时使用报错

这两个参数互斥。批量注册用 `--sources`，单张注册用 `--source + --target-id`：

```bash
# 错误用法
place --sources '{"a":"a.png"}' --source b.png --target-id b  # ✗

# 正确用法
place --sources '{"a":"a.png","b":"b.png"}'   # 批量 ✓
place --source a.png --target-id a            # 单张 ✓
```

### Q：图片已放到 assets/images/ 但 guard 不认

需要先 `place` 注册，guard 检查的是 `image-assets.json` 中的记录，不是文件系统：

```bash
python3 generate_images.py --task-dir PPTX/my-deck place
# 扫描所有 pre-v1 目标，发现文件则注册
```

### Q：修改了 brief 后，generate 报 guard 未通过

每次修改 brief（重新 init 或 serve-wait 后）需要重新运行 guard：

```bash
python3 presentation_director.py --base-dir . guard --task my-deck
```

### Q：HTML deck 在 PDF 导出时排版错乱

在 Chrome 或 Edge 中打开 `?print-pdf` 参数版本：

```
http://127.0.0.1:5500/PPTX/my-deck/v1/final.html?print-pdf
```

打印设置：
- 纸张：A4 横向
- 页眉页脚：关闭
- 背景图形：开启

### Q：UI 语言显示英文，但我想要中文

在 `init` 时传入 `--conversation-text` 参数，包含中文内容，Director 会自动检测语言：

```bash
python3 presentation_director.py --base-dir . init \
  --task my-deck \
  --conversation-text "帮我做一个关于量化策略的年终回顾 PPT"
```

---

## 附录：工作区目录结构

```
PPTX/<task-slug>/
├── brief-confirmed.json      # 用户确认的 brief（勿手动编辑）
├── status/
│   ├── confirmed.ready        # 用户点击确认后生成
│   ├── guard-passed.ready     # guard 通过后生成；agent 开始生成的权威信号
│   └── images-style.ready     # 用户完成图片风格门禁后生成
├── image-plan.json            # AI 图片生成计划
├── image-assets.json          # AI 图片注册记录
├── image-prompts.md           # prompt-only 导出（可选）
├── assets/
│   └── images/               # AI 生成或手动放置的图片
├── v1/
│   ├── final.html            # Reveal.js HTML 输出
│   ├── final.pptx            # PPTX 输出
│   ├── slides/               # per-slide PNG 预览
│   ├── contact-sheet.png     # 缩略图总览
│   └── qa-summary.md         # QA 记录
└── final/
    ├── <task-slug>.pptx      # 最终选定的 PPTX
    └── <task-slug>.html      # 最终选定的 HTML
```
