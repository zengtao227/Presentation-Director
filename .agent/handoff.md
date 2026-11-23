# Handoff

## 首轮产品化（2026-11-23 起，当前主线）

### Completed
- 方案审查与 Codex 复审完成，结论见 `docs/distribution/2026-11-23-engine-plan-review-brief.md` 第 7 节。
- 已删除专有的 `skills/pptx/`；自有代码改为保留所有权利（`LICENSE`）；官网去掉「开源」字样。
- 工作计划：`docs/distribution/2026-11-23-work-plan.md`；试用环境已远程核实（Win11 x64、WorkBuddy 5.11.3、WPS、无 PowerPoint）。

### Current State
- owner 2026-11-23 采纳全部建议：LibreOffice 渲染、首轮不签名、试用者两次桌前配合、Mac 已装 LibreOffice。
- 顺序 1 完成：`engine/deck_spec.py`（deck-spec v1）、`schemas/deck-spec-v1.schema.json`、`engine/generator/`（pptxgenjs 4.0.1 固定）、样例 `engine/samples/weekly-report.json`。
- 检查点通过（2026-11-23）：试用机 WPS 12.1 经 COM 改图表数据 62→70、表格单元格、标题文字后保存，回读文件图表缓存与内嵌数据表均为 70，6 页与备注保留。测试文件在试用机 `C:\PD-Test\`。
- 已知：本机 LibreOffice 26.8 在 macOS 27 上丢失所有非粗体中文（与文件无关，空白文档同样复现）；Mac 版面检查暂用 PowerPoint 导出 PDF（在 PowerPoint 容器目录内操作，无授权弹窗）。Windows 上的 LibreOffice 渲染待顺序 2/4 验证。
- 观察：pptxgenjs 依赖 image-size 有高危提示，仅解析图片时触发，首轮不传图片。

- 顺序 2 完成（2026-11-23）：`engine/render_check.py`（LibreOffice→PDF→pypdfium2 出图、总览图、python-pptx 结构检查）、`engine/core.py`（共用步骤）、`engine/cli.py`、`engine/mcp_server.py`（MCP SDK 2.3.0，stdio，6 个工具；引擎拒绝原因经 ToolError 原样给到模型；协议输出外的打印转到 stderr）。新任务默认 PPTX、不用 AI 生图（否则守卫要求额外的生图设置页）。依赖在 pyproject 的 `engine` 附加项（pillow 用 12.3.0 以兼容 3.10）。
- 验证：本机命令行全流程（确认前拒绝→三步确认页→v1→检查前拒绝导出→检查 6 页通过→v2→导出 v1）；真实 MCP 客户端经 stdio 列出 6 个工具并收到中文拒绝原因；全部 154 项测试通过。

- 顺序 3 完成（远程，无需试用者）：WorkBuddy 自身界面文字写明用户级连接器配置是 `~/.workbuddy/mcp.json`，技能目录 `~/.workbuddy/skills/`；安装时 WorkBuddy 的技能监视器即时察觉新技能。连接器似乎在新建任务时才加载，日志里还没有连接记录——留到试用者实测时确认。
- 顺序 4 完成：`packaging/windows/`（build.sh 在 Mac 上出 ZIP：Python 3.12.10 嵌入版 + 依赖按 uv.lock + Node 22.23.4 + 引擎 + 确认页 + 许可/第三方声明；install.ps1 按用户安装、LibreOffice 26.2.7 官方 MSI 校验后安装、自动接入 WorkBuddy/Codex/Claude 桌面版/Claude Code、自检；uninstall.ps1 反向清理）。用户入口 = 解压后双击 `Setup.cmd`。没做 Inno Setup：没有 Windows 构建机，且与“下载→解压→双击”的测试者流程一致。
- 试用机实测（2026-11-23）：首装约 11 分钟（主要是下载 LibreOffice）、覆盖重装约数秒；自检 6 页通过，Windows 上 LibreOffice 中文渲染正确；按 mcp.json 的启动方式用真实连接器客户端连通，6 个工具、新建任务正常；Codex/Claude 桌面版接入用假用户目录测试：替换旧条目、保留其他配置、备份原文件、TOML 可解析，卸载后清理干净。
- 确认页的上游设计库名字已从可见文案中去掉；未写 theme 时自动用确认页所选配色。

- 顺序 5 完成（2026-11-23）：官网上线不公开的测试下载页（noindex、未从任何页面链接），公网完整下载后校验值一致。页面地址、服务器版本目录与回滚方法记在 Necto 私有仓库 `.agent/handoff.md`，不写进本公开仓库。
- 试用机已装好且不再卸载，试用者直接使用。
- 11-23 晚三处修复，已重装到试用机并更新测试下载：① 确认后自动继续（新工具 `wait_for_confirmation`，每次约 45 秒，用户不需回到对话报告）；② 安装 LibreOffice 加 `REGISTER_NO_MSO_TYPES=1`，不抢 Office/WPS 默认打开；③ pptxgenjs 内嵌图表表格有格式错误，Excel 打开会“修复”并与图表断开——生成后自动修正，并改用 strRef 分类。owner 已在 Mac PowerPoint 实测「编辑数据」后图表随之变化；WPS 同步复测通过。

- 11-23 夜：HTML 输出已加入引擎（单文件、离线放映、pakco 主题、内嵌 SVG 图表）；按确认页的输出格式生成 PPTX / HTML / 两者；HTML 检查用本机 Edge/Chrome 无界面打印成 PDF 出图 + 页内脚本量溢出。试用机自检两种格式都通过（LibreOffice + Edge）。官网正式产品页已放下载按钮。

### Next Steps
- 顺序 6：试用者桌前实测（W8），顺带确认 WorkBuddy 新建任务时能连上连接器、点「信任」的流程。
- 之后：Mac 安装包；再考虑插件市场（Claude Code / Codex 插件、Claude 桌面扩展 .mcpb）——发布前查官方提交规则。网页版需另做在线服务或经 Necto，未定。

### Key Decisions
- 首轮只做 Windows x64 + WorkBuddy stdio + PPTX + A/D 检查；HTTP、豆包、Necto、第二个系统推迟。

### Review 时间
- 无

### 验收标准
- 见工作计划 W8。

---

## 历史：PresentationDirectorPlanV1 Freeze Candidate

## Completed
- Closed the governed-expression, deterministic producer, and locked-CI implementation blockers on Draft PR #12.
- Added strict production input and Plan schemas, regenerated the six-slide RFC 8785 golden Plan, and recorded negative tests for legacy/malformed input.
- Removed the ungoverned dataset namespace, closed image/screenshot inputs to approved assets, and defined object-level font-family assignment semantics.
- Kept Playwright out of the contract wheel's default runtime and added exact Python 3.10/3.11 contract compatibility jobs beside the primary 3.12 verification.

## Current State
- Branch: `codex/presentation-plan-v1-freeze`.
- The candidate remains Draft pending GitHub CI and independent cross-repository freeze review.
- Eligibility, Provider routing, GenerationRequest, and PPTX generation remain out of scope and unimplemented.

## Next Steps
- Review the pushed diff and GitHub CI evidence.
- If the candidate receives GO, freeze the exact Plan/capability versions and begin BPS compatibility work before Eligibility.

## Key Decisions
- `brief-confirmed.json` remains a mutable standalone workflow input and cannot be a governed producer source.
- Capability vocabulary comes from business/file-format semantics, not restricted `skills/pptx` implementation details.
- Ruff/format gates cover the new contract surface; legacy UI/state lint debt remains separate while full tests and compileall cover the repository.
