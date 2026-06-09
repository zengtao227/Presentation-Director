# Presentation Director 视频导出方向可行性记录

> 状态：探索性路线图（Roadmap / Feasibility Note）  
> 更新时间：2026-06-09  
> 目的：记录 Presentation Director 未来是否以及如何扩展到 HTML→MP4 视频导出能力，尤其评估 `html-video` / HyperFrames 这类工具对本项目的价值。

---

## 1. 结论摘要

`html-video` / HyperFrames 代表了一个值得持续关注的方向：**把 HTML/CSS/JS 动效内容本地渲染成 MP4**。这与 Presentation Director 的长期方向有较高契合度，因为当前项目已经在从“只生成 PPTX”扩展到“PPTX + Reveal.js HTML + HTML 动效 + 图片门禁 + QA 审查”的多格式演示内容生成系统。

但是，当前不建议把 `html-video` 直接接入 Presentation Director 的核心生成链路，也不建议让 PPTX/HTML 主流程强依赖它。更稳妥的策略是：

1. **先作为可选的实验性视频导出能力进入项目**；
2. **先跑通 final.html / deck.md → MP4 的独立路径**；
3. **等渲染质量、中文字体、依赖安装、性能、错误处理都稳定后，再考虑增加 Video Export Gate**；
4. **长期目标是让 Presentation Director 输出三类成果：可编辑 PPTX、可浏览 HTML deck、可传播 MP4 视频摘要。**

一句话定位：

> Presentation Director 负责生成可审查、可修改、可演示的 deck；视频导出模块负责把最终 deck 或其内容摘要转换成可传播的 MP4。

---

## 2. 背景：为什么这个方向值得记录

Presentation Director 的核心价值一直不是简单“生成几页幻灯片”，而是建立一条更可靠的演示内容生产流程：

- Intake 收集需求；
- Visual Inspiration / Brief Confirmation 锁定方向；
- PPTX 或 Reveal.js HTML 生成；
- Preview / Style Review / Compare 等门禁让用户可审查、可修改；
- QA 保证文字不溢出、版面安全、内容边界清晰；
- 最终交付可编辑或可浏览的演示成果。

随着 HTML 输出路径逐步增强，Presentation Director 已经具备了生成更强视觉表现的基础：Reveal.js、HTML theme catalog、HTML layout catalog、HTML animation catalog、AI image gate、safe-area 规则等都可以为视频化输出提供素材。

因此，“视频导出”不是另起炉灶，而是自然延伸：

```text
Brief / deck.md / final.html
        ↓
Presentation Director 生成审查后的演示内容
        ↓
Video Export Adapter 读取已确认内容
        ↓
storyboard / frames / HTML animations
        ↓
local render engine
        ↓
final.mp4
```

---

## 3. 上游工具观察：html-video 与 HyperFrames

### 3.1 html-video 的可用价值

`html-video` 是 Open Design 团队相关的 HTML-to-video 项目，公开定位是让本地 coding agent 根据 prompt、文章链接或 GitHub repo 生成多帧 storyboard，再把每一帧变成 animated HTML，最后通过本地渲染引擎输出 MP4。

对 Presentation Director 有价值的点：

- 用 HTML/CSS/JS 表达动画，和现有 Reveal.js HTML 路径技术栈接近；
- 本地渲染 MP4，不需要云端按次收费；
- 有 template gallery，可以借鉴其视频模板组织方式；
- 支持多 frame storyboard，这和 deck 的 slide sequence 有天然映射关系；
- 适合把文章、repo、课程内容、产品说明转成短视频解读。

### 3.2 HyperFrames 的可用价值

HyperFrames 是更底层的 HTML/CSS/media → video 渲染框架。它的定位更像“渲染引擎”，而 `html-video` 更像“agent + storyboard + template + engine adapter 的上层工作流”。

对 Presentation Director 来说，不能只关注 `html-video`，也应该评估直接接 HyperFrames 的可能性。原因是：

- Presentation Director 已经有自己的 intake、brief、deck.md、visual contract、review gates；
- 如果接入整个 `html-video`，可能会重复它的 source fetch、agent loop、storyboard planning；
- 如果只接 HyperFrames 或类似渲染层，Presentation Director 可以保留自己的 planning / QA / review 体系；
- 长期最好做 adapter，而不是绑定某一个外部项目。

---

## 4. 产品定位建议

视频导出不应取代 PPTX / HTML deck，而应作为可选增强功能。

### 4.1 不推荐的定位

不建议这样做：

```text
用户要 presentation
→ 直接走 html-video
→ 只输出 MP4
```

原因：

- Presentation Director 的核心承诺是“可编辑、可审查、可迭代”；
- MP4 是最终传播格式，不适合承载所有中间修改；
- 直接视频化容易绕过现有的 brief confirmation、style review、QA gates；
- 外部工具更新快，直接绑定会增加维护风险。

### 4.2 推荐的定位

推荐这样做：

```text
用户要 presentation
→ Presentation Director 正常生成 PPTX / HTML deck
→ 用户确认 final deck
→ 可选 Export Video
→ 生成 MP4 companion
```

也就是说，视频是 companion artifact：

- PPTX：主编辑格式；
- Reveal.js HTML：浏览 / 动效演示格式；
- MP4：传播 / 自动播放 / 社交媒体 / 课程宣传格式。

### 4.3 典型使用场景

1. **课程介绍视频**  
   从一份教学 PPT 或课程大纲生成 30–90 秒课程导览视频。

2. **项目路演短片**  
   从 deck.md / final.html 提炼核心卖点，生成社交平台或会议前播放的短片。

3. **培训材料自动播放版**  
   把普通培训 deck 转成带字幕、旁白、过渡动画的 MP4。

4. **产品功能解释视频**  
   读取 GitHub repo 或技术文档，生成 5–8 个 frame 的解释型短视频。

5. **会议展示备用方案**  
   当现场不能打开 PPTX 或 HTML 时，用 MP4 作为兜底播放文件。

---

## 5. 分阶段实施路线

### Phase 0 — 调研与本地试跑，不动主流程

目标：验证 `html-video` / HyperFrames 是否适合 Presentation Director 的技术栈。

建议任务：

1. 克隆并本地运行 `html-video`；
2. 确认 Node.js、pnpm、ffmpeg、Playwright/Chromium 等依赖；
3. 用一个 Presentation Director 已生成的 `final.html` 或 `deck.md` 作为输入；
4. 测试三种路径：
   - prompt → MP4；
   - deck.md → storyboard → MP4；
   - final.html / slide screenshots → MP4；
5. 记录中文字体、字号、换行、字幕、画面比例、渲染时间、失败日志；
6. 不修改 Presentation Director 主流程，只在本地实验目录中保留结果。

Phase 0 的成功标准：

- 可以稳定导出一个 16:9 MP4；
- 中文字体不乱码；
- 文字不明显溢出；
- 本地 Mac 可以跑通；
- 失败时能看到明确错误，而不是静默失败。

---

### Phase 1 — 增加独立的实验性 export-video 命令

目标：让视频导出成为 Presentation Director 的可选后处理步骤，而不是主流程依赖。

建议命令：

```bash
python3 scripts/presentation_director.py export-video --task "<task-slug>"
```

建议输出目录：

```text
Decks/<task-slug>/video/
  video-brief.json
  storyboard.json
  frames/
    frame-001.html
    frame-002.html
    frame-003.html
  renders/
    frame-001.webm
    frame-002.webm
  final.mp4
  render.log
  qa-video-summary.md
```

Phase 1 只做最小功能：

- 输入：读取 `brief-confirmed.json`、`deck.md`、`v1/final.html` 或 `final/<task-slug>.html`；
- 输出：一个 `final.mp4`；
- 不改变 PPTX / HTML final 文件；
- 不影响 style-review / compare；
- 失败时只报告视频导出失败，不让整个 deck 生成失败。

建议先支持两种视频模式：

| 模式 | 说明 |
|---|---|
| `deck-recording` | 逐页录制已有 HTML deck，类似自动播放版演示 |
| `summary-video` | 从 deck 内容提炼 5–8 个 frame，生成短视频摘要 |

Phase 1 的成功标准：

- `export-video` 可手动触发；
- 成功产出 MP4；
- 所有中间文件集中在 `Decks/<task-slug>/video/`；
- 不污染主流程；
- 可以在最终报告里列出视频路径。

---

### Phase 2 — 引入 Video Export Gate

目标：让用户在最终 deck 确认后选择是否生成视频，并控制视频参数。

建议新增页面：

```text
video-export.html
```

建议新增状态文件：

```text
status/video-export.ready
video-export-request.json
```

Video Export Gate 建议字段：

```json
{
  "enabled": true,
  "video_mode": "summary-video",
  "aspect_ratio": "16:9",
  "duration_seconds": 60,
  "target_platform": "general",
  "narration": "none",
  "subtitles": true,
  "music": "none",
  "source_version": "final"
}
```

用户可选项：

| 字段 | 可选值 | 说明 |
|---|---|---|
| `video_mode` | `deck-recording` / `summary-video` / `promo-video` | 决定是逐页演示、摘要、还是宣传片 |
| `aspect_ratio` | `16:9` / `9:16` / `1:1` | 横屏演示、竖屏短视频、方形社媒 |
| `duration_seconds` | 30 / 60 / 90 / custom | 控制节奏 |
| `narration` | `none` / `script-only` / `tts` | 先支持脚本，TTS 后做 |
| `subtitles` | true / false | 是否烧录字幕 |
| `music` | `none` / `local` / `generated` | 先不默认开启 AI 音乐 |

Phase 2 的成功标准：

- 用户必须显式选择是否生成视频；
- 视频请求写入 JSON，可复现；
- 视频导出有单独 QA summary；
- 视频失败不影响 PPTX/HTML final。

---

### Phase 3 — 视频 QA 与多版本比较

目标：把视频导出纳入 Presentation Director 的质量文化，但仍保持可选。

建议增加视频 QA 项：

- 输出文件存在且大小 > 0；
- 分辨率符合请求比例；
- 时长误差在允许范围内；
- 中文字体可读；
- 字幕不超出 safe area；
- 关键帧无明显黑屏或空白；
- 音频轨存在性符合请求；
- ffmpeg exit code 为 0；
- 生成日志保留。

未来可以增加：

- 视频 contact sheet；
- frame preview grid；
- compare two video versions；
- 自动抽帧检测文字溢出；
- shot timing review。

Phase 3 的成功标准：

- 每个 MP4 都有 `qa-video-summary.md`；
- 用户可以比较不同风格或不同时长的视频版本；
- 失败原因可定位、可修复。

---

### Phase 4 — 深度产品化

目标：当 Phase 1–3 证明稳定后，把视频导出变成 Presentation Director 的正式输出类型。

可考虑新增 output_format：

```json
{
  "output_format": "pptx+html+video"
}
```

或保持更清晰的结构：

```json
{
  "output_format": "both",
  "video_export": {
    "enabled": true,
    "mode": "summary-video"
  }
}
```

不建议一开始就把 `video` 放进核心 `output_format`，因为视频是传播格式，不是编辑主格式。长期可以根据稳定性再决定。

---

## 6. 技术路线建议

### 6.1 Adapter 结构

不要在核心代码中直接绑定 `html-video`。建议抽象为 video renderer adapter：

```text
scripts/
  video_export.py
  video_renderers/
    base.py
    hyperframes_adapter.py
    html_video_adapter.py
    browser_recording_adapter.py
```

接口示例：

```python
class VideoRenderer:
    def render(self, request: VideoExportRequest, ctx: VideoExportContext) -> VideoExportResult:
        ...
```

这样未来可以替换渲染引擎：

| Adapter | 用途 |
|---|---|
| `hyperframes_adapter` | 直接用 HTML frame 渲染 MP4 |
| `html_video_adapter` | 调用 html-video 的 CLI / studio pipeline |
| `browser_recording_adapter` | 直接录制现有 Reveal.js deck |
| `remotion_adapter` | 未来可选，若需要 React 视频能力 |

### 6.2 数据结构建议

建议先定义内部 IR，而不是直接采用外部项目格式。

```json
{
  "version": 1,
  "task_slug": "example-task",
  "source": {
    "type": "deck",
    "path": "Decks/example-task/final/example-task.html"
  },
  "video": {
    "mode": "summary-video",
    "aspect_ratio": "16:9",
    "duration_seconds": 60,
    "fps": 30
  },
  "frames": [
    {
      "id": "frame-001",
      "source_slide_ids": [1],
      "duration_seconds": 6,
      "headline": "Opening idea",
      "body": "Short explanation",
      "visual_style": "editorial-motion",
      "html_path": "frames/frame-001.html"
    }
  ]
}
```

这样可以避免被 `html-video` 的内部格式锁定。

### 6.3 依赖管理建议

视频导出依赖较重，应做成 optional dependency。

建议 guard：

```bash
node --version
pnpm --version
ffmpeg -version
npx playwright --version
```

失败时提示：

```text
Video export dependencies are missing.
PPTX/HTML generation is complete; MP4 export was skipped.
```

不要因为缺少 ffmpeg 或 Chromium 阻断普通 deck 生成。

### 6.4 字体与中文支持

中文输出是必须重点验证的地方。

建议：

- 在 video QA 中增加中文 smoke test；
- 明确 fallback font stack；
- 在 Mac、Linux 两种环境上测试；
- 不要假设浏览器环境一定有中文字体；
- 竖屏短视频更容易文字溢出，需要单独 safe-area。

建议 CSS font stack：

```css
font-family: "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", "Source Han Sans SC", sans-serif;
```

### 6.5 与现有 HTML deck 的关系

有两条可选路线：

#### 路线 A：录制 existing Reveal.js deck

```text
final.html → browser automation → mp4
```

优点：

- 最容易实现；
- 最大程度复用现有 HTML deck；
- 适合 “deck-recording”。

缺点：

- 画面像录屏，不一定像真正短视频；
- 节奏可能不够短视频化；
- slide layout 不一定适合 9:16。

#### 路线 B：基于 deck 内容重新生成 video storyboard

```text
deck.md / brief-confirmed.json → storyboard → frame HTML → mp4
```

优点：

- 更像真正的视频；
- 可以做 9:16、1:1；
- 可以做字幕、旁白、动效；
- 更适合社交媒体传播。

缺点：

- 需要新的 QA；
- 需要处理内容摘要与忠实性；
- 实现复杂度更高。

建议顺序：

1. 先做路线 A；
2. 再做路线 B；
3. 最后支持二者并存。

---

## 7. 与 Presentation Director 现有原则的关系

视频导出必须遵守现有项目原则：

1. **Gate first**  
   用户需要确认视频方向，不能自动生成不可控 MP4。

2. **Artifacts are versioned**  
   每个视频版本必须存放在任务目录下，不能散落在根目录。

3. **No silent fallback**  
   如果视频渲染失败，必须记录失败原因，不能偷偷输出低质量替代物。

4. **Deck remains source of record**  
   PPTX / HTML deck 仍是主成果，MP4 是 companion。

5. **QA before final**  
   只要给用户最终 MP4，就必须有最小 QA 记录。

6. **Optional means optional**  
   视频依赖缺失时，不应该阻断普通 Presentation Director 工作流。

---

## 8. 风险与注意事项

| 风险 | 说明 | 建议 |
|---|---|---|
| 上游项目变化快 | `html-video` 还比较新，API 可能变动 | 只通过 adapter 调用，不深度耦合 |
| 依赖较重 | Node/pnpm/ffmpeg/Chromium 都可能失败 | optional dependency + doctor command |
| 中文字体问题 | MP4 渲染时可能乱码或 fallback 错误 | 加中文 smoke test 和 font stack |
| 视频 QA 难度高 | 不能只看文件存在 | 抽帧、时长、分辨率、字幕 safe-area 检查 |
| 生成时间较长 | 视频渲染比 HTML/PPTX 慢 | 后处理异步化，日志清晰 |
| 用户预期膨胀 | 视频不是剪辑软件替代品 | 定位为 companion / summary video |
| 版权与素材 | 背景音乐、图片、字体可能有授权问题 | 默认不加音乐；素材来源记录进 manifest |

---

## 9. 最小可行版本（MVP）建议

MVP 不要太大。建议只实现：

```text
Input: Decks/<task-slug>/final/<task-slug>.html
Mode: deck-recording
Aspect ratio: 16:9
Audio: none
Subtitles: none
Output: Decks/<task-slug>/video/final.mp4
QA: file exists + duration + resolution + render log
```

MVP 暂时不做：

- AI 旁白；
- AI 音乐；
- 竖屏短视频；
- 多模板选择；
- 用户逐 frame 编辑；
- 自动上传平台；
- 替代 PPTX 主流程。

这个 MVP 的目标不是“做剪映”，而是证明 Presentation Director 可以从 HTML deck 可靠地导出 MP4。

---

## 10. 推荐的下一步任务清单

### 短期任务

- [ ] 建立 `docs/video-export-roadmap.md` 记录本路线图；
- [ ] 本地试跑 `html-video`；
- [ ] 本地试跑 HyperFrames；
- [ ] 选择一个 Presentation Director 已生成的 HTML deck 做输入；
- [ ] 记录中文字体与渲染结果；
- [ ] 写一份 `docs/video-export-experiment-notes.md` 记录实验结果。

### 中期任务

- [ ] 新增 `scripts/video_export.py`；
- [ ] 新增 `video_renderers/` adapter 目录；
- [ ] 新增 `export-video` CLI；
- [ ] 新增 `video-brief.json` / `storyboard.json`；
- [ ] 输出 `qa-video-summary.md`；
- [ ] 将 video output path 写入 final report。

### 长期任务

- [ ] 增加 `video-export.html` gate；
- [ ] 支持 `summary-video`；
- [ ] 支持 9:16 / 1:1；
- [ ] 支持字幕；
- [ ] 支持旁白脚本；
- [ ] 支持视频版本比较；
- [ ] 形成稳定的 `video_export` product mode。

---

## 11. 当前建议

当前建议是：

```text
Do:
  - 记录方向
  - 本地试跑
  - 做独立 export-video 实验分支
  - 把 MP4 作为 companion artifact

Do not:
  - 让主流程强依赖 html-video
  - 直接把 html-video 当成 Presentation Director 的替代生成器
  - 在没有 QA 的情况下输出 final.mp4
  - 因视频依赖缺失而阻断 PPTX/HTML 生成
```

最终判断：

> 视频导出是 Presentation Director 值得发展的下一阶段能力，但应该以“可选、后处理、adapter 化、可 QA”的方式推进。先证明本地 HTML→MP4 的稳定性，再逐步产品化。
