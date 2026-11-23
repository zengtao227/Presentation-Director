# Presentation Director 可分发引擎方案 · Codex 审查说明

- 日期：2026-11-23
- 基线：`main` @ `437f211`
- 审查性质：**只读**。不改代码、不提交、不安装依赖、不运行会写入 `Decks/` 的命令。
- 交回格式：逐条回复 R1–R12，每条给「同意 / 不同意 / 需补充」+ 证据（文件:行、官方文档原文或链接）。发现方案外的阻塞问题，编号为 N1、N2…

---

## 1. 目标

把 Presentation Director 从「只能在 owner 本机、依赖 Codex 运行时跑」变成**普通用户下载即可用的工具**，可被多种 AI 工具调用：Codex、Claude（Code / Desktop）、WorkBuddy、豆包电脑版，以及通过 Necto 接入的网页端 AI。

首轮交付范围：一个中文样例、一份可编辑 `.pptx`、首位试用者正在用的 WorkBuddy 桌面环境。

## 2. 已定决策（owner 已确认，不重审方向，只审实现是否成立）

| # | 决策 |
|---|---|
| D1 | 结构采用「**本机引擎 + 各宿主薄接入层**」，不做成单一技能包。 |
| D2 | 设计资料只从当前使用的开源设计库中**抽取本产品用到的部分**，改为本产品自有名称和格式；以后随本产品版本更新重新抽取。产品界面、说明和技能文字里不出现上游项目名。 |
| D3 | 确认页「停下来等用户点确认」在本机已可用（`437f211` 的后台等待）；WorkBuddy 实机测试等引擎做完后，交首位试用者实测，不在开发阶段假设结果。 |
| D4 | 生成层不依赖任何不能分发的运行时或说明文件（见 §3.1）。 |

## 3. 已查实的事实（审查时请复核）

### 3.1 不能随包分发的部分

| 对象 | 证据 | 结论 |
|---|---|---|
| `skills/pptx/` 全目录 | `skills/pptx/LICENSE.txt` 第 1–3 行：「© 2025 Anthropic, PBC. All rights reserved. … governed by your agreement with Anthropic」 | 专有授权。删除版权行不改变归属，反而构成移除版权声明。**不能进分发包**，需自写替代。 |
| Codex Presentations 运行时（`@oai/artifact-tool`，本机约 1.6 GB） | `skills/deck-builder/SKILL.md:97`；`presentation_director.py:5585–5749` 的生成提示文字指向它 | OpenAI 的程序，不是文件头的问题。分发包里不能带，也不能假设用户机器上有。 |

引擎核心 `skills/deck-builder/scripts/presentation_director.py`（6850 行：问询、确认页服务、守卫、预览/对比页）**没有导入** `skills/pptx` 的任何脚本（`grep skills/pptx|soffice|thumbnail.py` 无结果），属于本项目自有代码。

### 3.2 可以随包分发的部分

| 对象 | 授权 | 分发条件 |
|---|---|---|
| `pptxgenjs`（生成 PPTX 的 JS 库） | MIT | 附许可文本 |
| `skills/html-deck/pakco-html/` | MIT（`LICENSE` 第 1–3 行） | 附许可文本 |
| 设计资料库（上游 `ui-ux-pro-max-skill`，owner 自有 fork） | MIT（fork 根目录 `LICENSE`：Copyright (c) 2024 Next Level Builder） | MIT 唯一硬性条件：副本中保留版权声明和许可文本。放进包内 `THIRD_PARTY_NOTICES` 即可，**不要求写版本号，不要求在界面或说明中出现名字**。数据中含 Google Fonts 等条目，字体本身另有 OFL 授权，抽取时需带上对应声明。 |
| LibreOffice | MPL-2.0 | 可以由安装器下载安装或随附；问题在体积（几百 MB），不在授权或费用。 |

### 3.3 宿主接入能力

| 宿主 | 本机 MCP（进程方式 stdio） | 本机 HTTP MCP | 上传技能 | 证据等级 |
|---|---|---|---|---|
| Codex / Claude Code / Claude Desktop | 支持 | 支持 | 支持 | 官方，已知 |
| WorkBuddy 桌面端 | 支持：`"type":"stdio"` + `command`/`args`，写入用户目录 `.workbuddy-ai/mcp.json`，首次连接需点「信任」；网页版无自定义连接器 | 未写明 | 支持（「添加技能 > 上传技能」） | 官方只确认「自定义连接器」入口；stdio 细节来自第三方实测（WorkBuddy 5.9.4） |
| 豆包电脑版 / 豆包工作 | **未见证据** | 支持：「新建自定义连接器」选 HTTP 传输、填服务器 URL 和 Header；仅限本地电脑 | 支持（「新建 > 上传技能」） | 新闻报道 + 第三方接入教程，未找到字节官方文档 |
| 网页端 AI（ChatGPT、DeepSeek、豆包网页等） | 不适用 | 不适用 | 不适用 | 经 Necto 桥接（`necto-trial-1` 已在 Necto 侧边栏跑通 8 页中文 PPTX） |

来源：
- WorkBuddy 连接器官方文档：https://cloud.tencent.com/document/product/1831/134525
- WorkBuddy 技能官方文档：https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market
- WorkBuddy stdio 实测（第三方）：https://www.atlascloud.ai/zh/blog/tips/workbuddy-mcp
- 豆包技能·连接器上线报道：https://www.ithome.com/0/992/607.htm
- 豆包自定义连接器接入（第三方）：https://cli.im/open-api/agent/open-platform-mcp/doubao-work.html 、https://open.zhihuiya.com/devportal/integrations/doubao

### 3.4 渲染与检查依赖

- 当前 PPTX 逐页出图：LibreOffice（`soffice`）转 PDF → poppler（`pdftoppm`）转图片，写在 `skills/pptx/SKILL.md:212–232`（专有文件内）。
- HTML 页面检查已用 Playwright：`presentation_director.py:2601 playwright_visual_qa`。

## 4. 修改后的方案

### 4.1 结构

```text
本机引擎（安装包：自带 Python、Node、pptxgenjs、确认页服务、渲染器）
  ├─ 命令行入口（供技能/脚本直接调用，也供测试）
  └─ MCP 服务，两种通道同一套工具：
       ├─ stdio：Codex、Claude、WorkBuddy
       └─ 本机 HTTP（仅监听 127.0.0.1，带随机令牌）：豆包等只支持 URL 的宿主
各宿主薄接入层：一份短技能说明（何时调用、流程顺序），不承载规则本身
网页端 AI：经 Necto 调用同一引擎
```

### 4.2 MCP 工具（初稿）

| 工具 | 作用 | 硬规则 |
|---|---|---|
| `start_task` | 新建任务，接收资料路径/文本、对话原文（用于界面语言） | — |
| `open_confirmation` | 打开问询 + 视觉方向 + 确认页，立即返回页面地址 | 不阻塞宿主 |
| `get_status` | 查询任务状态（待确认 / 已确认 / 生成中 / 完成 / 失败） | 宿主轮询或用户回来再问 |
| `generate` | 按已确认方案生成 PPTX | **未通过守卫直接拒绝**（把「先确认后生成」从文字规则移进工具） |
| `render_check` | 逐页出图 + 结构检查，返回问题列表和总览图 | 渲染器缺失时返回明确等级（见 4.4），不得假装通过 |
| `export` | 返回最终文件路径 | 只交通过检查的版本 |

### 4.3 生成层（替代专有部分）

- 自写基于 `pptxgenjs` 的生成器：读取已确认的方案（`deck.md` / plan v1 合同 + 视觉合同），按版式族输出可编辑形状、文本、原生图表、表格。
- 版式规则、字号层级、安全区等由本项目已有的 `design-locks/`、`docs/quality-gates.md`、`check_presentation_safe_area.py` 提供；不复用 `skills/pptx/` 的任何文字或脚本。
- Codex 主机上仍可选用 Codex Presentations（本机已装时），但只作为可选增强，不是分发包的依赖。

### 4.4 渲染检查分级

| 等级 | 条件 | 做法 | 能否标「已渲染检查」 |
|---|---|---|---|
| A 真实渲染 | 有 LibreOffice | 安装器首次运行时从官方源安装（或附便携版）；PPTX → PDF → 逐页图 | 能 |
| B 本机 Office | 检测到 PowerPoint | Windows 用 COM 导出图片；macOS 需启动已有的授权弹窗处理脚本 | 能 |
| C 近似预览 | 两者都没有 | 用同一份版面数据在 Playwright 内置浏览器画 HTML 预览截图 | **不能**，标「近似预览」 |
| D 结构检查 | 始终执行 | 解析 PPTX：越界、文本估算溢出、字体缺失、空占位符 | 只作附加 |

默认目标是 A；首位试用者的安装包必须做到 A 或 B。

### 4.5 设计资料抽取

- 新增一个**构建期**抽取脚本：从上游 fork 读取本产品实际用到的数据表和字段，输出到 `engine/design-data/`（本产品命名），生成 `THIRD_PARTY_NOTICES`。
- 运行时不再调用全局 `ui-ux-pro-max` 脚本；仓库内 21 个文件中的上游名字，分发包内全部不出现（仓库开发文档可保留来源说明）。
- 上游更新时：重跑抽取脚本 → 对比差异 → 随本产品新版本发布。

### 4.6 阶段

| 阶段 | 内容 | 通过标准 |
|---|---|---|
| 0 去依赖 | 4.3 生成器、4.5 抽取脚本、分发清单（白名单方式列出进包文件） | 分发清单内无专有文件；在没有 Codex 运行时的环境（用 `HOME` 指向空目录模拟）做出 6 页中文 PPTX，含一张原生图表和一个小表格 |
| 1 引擎 + MCP | 4.1 两种通道、4.2 工具、4.4 A/D 级 | Claude Code 和 Codex 各走通一次：确认页打开 → 隔几分钟点确认 → 生成 → A 级渲染图 |
| 2 安装包 | Windows + macOS 安装器，自带运行时；WorkBuddy、豆包接入说明 | 干净机器从下载到成品不用终端；首位试用者在 WorkBuddy 独立完成一次，记录耗时和需要介入的地方 |
| 3 正式下载 | 修试用阻塞；官网产品页放下载、三步图文、样例成品 | 从公开页面重新下载同一版本走完全程；页面标明已验证的系统和宿主版本 |

## 5. 审查项

- **R1 授权判断**：§3.1、§3.2 的授权结论是否成立？特别是：MIT 数据抽取改名后只放 `THIRD_PARTY_NOTICES` 是否满足条件；LibreOffice 由安装器下载安装或随附各自的义务。
- **R2 现有公开仓库**：本仓库为公开仓库且包含 `skills/pptx/`（专有授权）。是否应从仓库移除并改为说明「需用户自行安装」？给出建议，不执行。
- **R3 引擎边界**：`presentation_director.py`（6850 行）中哪些部分可以直接成为引擎核心，哪些与 Codex 绑定（如 5585–5749 行的生成提示）需要拆出？给出拆分清单（函数级）。
- **R4 生成层可行性**：仅用 `pptxgenjs` 能否达到 `necto-trial-1` 的质量要求（原生图表、表格、中文字体、可编辑性）？列出已知短板。
- **R5 守卫进工具**：§4.2 把「未确认拒绝生成」放进 `generate` 是否足以替代 `SKILL.md` 里的文字规则？是否还有可被宿主模型绕过的路径（例如直接调用命令行、直接写状态文件）？只列有实际触发路径的，理论缺口标「观察」。
- **R6 长等待**：确认页「立即返回 + `get_status` 查询」在 stdio 和 HTTP 两种通道下是否都成立？引擎进程生命周期由谁管理（宿主关闭 MCP 时确认页服务是否随之退出）？
- **R7 本机 HTTP 通道安全**：仅监听 127.0.0.1 + 随机令牌是否够用？令牌如何交给豆包的连接器配置而不出现在日志或进程参数中？
- **R8 渲染分级**：§4.4 的 A–D 分级是否合理？C 级是否有必要保留，还是应直接要求 A/B？
- **R9 Windows 风险**：自带 Python/Node、LibreOffice 安装、中文路径、杀毒软件误报（参照 Necto 曾被 Defender 隔离的经历）——哪些需要在阶段 2 之前处理？
- **R10 设计资料抽取**：§4.5 的「构建期抽取、运行时不调用上游」是否会丢失当前流程依赖的能力（例如 `--design-system` 聚合推理）？列出受影响的调用点。
- **R11 阶段 0 验收方法**：用空 `HOME` 模拟「无 Codex 运行时」是否可靠？是否还有其他隐性依赖（全局技能、全局 npm、系统字体）需要一并屏蔽？
- **R12 过度设计检查**：§4 中是否有当前首轮（一个宿主、一个样例、一份 PPTX）用不到、可以推迟的机制？

## 6. 只读约束

- 不修改任何文件，不提交，不推送。
- 不安装依赖，不启动确认页服务，不生成 PPTX。
- 需要验证外部平台行为时，引用官方文档原文；没有官方依据的写「未证实」。

---

## 7. 审查结论处理（2026-11-23，Claude 核对后 owner 采纳）

判断原则：确认门是「用户自己的 AI 代理按流程办事」的流程保证，不是安全边界——宿主与引擎以同一用户身份运行，宿主本来就能读写用户文件。因此不为「宿主模型伪造确认」「证明是人点击」之类没有实际触发路径的情况加防护。

| 项 | 决定 | 落地内容 |
|---|---|---|
| R1 | 采纳 | 包内放 `THIRD_PARTY_NOTICES`（设计资料、pakco-html、pptxgenjs）。LibreOffice 只由安装器从官方源下载未改动的官方包，不镜像、不重打包。首轮不随包带字体文件。 |
| R2 | 已执行 | `skills/pptx/` 已从仓库删除，操作文档改指官方 `pptx` 技能（Claude Code 内置，其他环境从 anthropics/skills 安装）。不改写 Git 历史：同样的文件由 Anthropic 在其公开仓库发布，历史副本不增加暴露，强推改写历史的破坏性大于收益。 |
| R3 | 部分采纳 | 只作为建引擎时的拆分参考；动手时把 Codex 专用提示文字（`initial_prompt`/`revision_prompt` 的 PPTX 分支、`generation_strategy_text`）移到适配层。不提前做整体重构。 |
| R4 | 采纳 | 固定 pptxgenjs 版本；验收在 Office 里改一处文字、一个表格单元格、一项图表数据。 |
| R5 | 部分采纳 | 采纳：命令行和 MCP 共用同一个生成入口，入口内调用现有 `validate_generation_guard`。不采纳：确认记录与方案内容做哈希绑定、证明由人点击——无实际触发路径，标「观察」。 |
| R6 | 采纳（简化） | stdio 引擎进程负责确认页的启停；`get_status` 直接返回现有状态文件（已确认 / 守卫通过）。 |
| R7 | 推迟 | 随 HTTP 通道一起推迟（R12）。日后做 HTTP 时按 MCP 规范校验 `Origin` 和 `Authorization`。豆包本机接入没有官方依据，从首轮承诺中移除。 |
| R8 | 采纳 | 首轮只做 A + D。`export` 只交出本版本目录里渲染检查已通过的文件。B、C 推迟。 |
| R9 | 部分采纳 | 只收两项有实际触发路径的：① Windows 无 `setsid`，`start_new_session=True`（`presentation_director.py:6556`）的后台等待需要 Windows 写法；② 用含空格和中文的路径跑一次真实渲染。Defender/SmartScreen 在阶段 2 用真实安装包测，不预设对策。 |
| R10 | 采纳 | 首轮用 Python 内已有的内置候选（`build_visual_candidates`）+ 构建期为支持场景预先固化的设计建议；移植上游聚合推理推迟。 |
| R11 | 部分采纳 | 阶段 0 改为：从打包产物启动，在干净沙箱或新建系统用户里跑。不做网络、区域设置、字体的组合矩阵。 |
| R12 | 采纳 | 首轮 = 引擎命令行 + WorkBuddy stdio 一条接入 + PPTX + A/D 检查 + 一次预览与导出，只做首位试用者所用系统。HTTP、豆包、Necto、第二个系统、B/C 推迟。 |
| N1 | 部分采纳 | 采纳：定义一份最小的逐页输入格式（每页标题、要点、图表数据、表格单元格），由宿主模型按资料写出、引擎读取。不采纳：再加一道「确认逐页方案」的门——现有流程是确认方向 → 生成 → 预览审阅，预览审阅就是用户的接受点。 |
| N2 | 不采纳 | 现有 `vN/` 版本目录已把文件、渲染图和终选放在一起；`export` 交出用户终选的那个 `vN`，检查报告放同一目录即可，不另做绑定。 |
| N3 | 不采纳（观察） | 引擎与宿主同一用户身份，路径由用户自己的代理传入，没有越权边界。做 HTTP 通道时再评估。 |
| N4 | 采纳，待 owner 决定 | 正式下载前为自有代码选定发行许可。 |
