# 2026-11-19 工作流审查：已修复项与待讨论项

来源：Codex 对 `main@d35b4ad` 的只读审查（独立制稿状态、HTML 晋升、安装分发、NECTO 接入）。
Claude 逐条对照代码核实后，**双方一致的部分已修复**；**看法不同或需要在 Codex 环境里执行的部分**列在下面，供 owner 与 Codex 讨论。

讨论约束：只读讨论，不改代码；已修复项不需要重审，除非发现修复本身有错。

---

## 一、已修复（双方一致）

| 项 | 修法 | 位置 |
|---|---|---|
| 定稿检查写了“用户已审阅”信号 | `finalize` 不再写 `preview-reviewed.ready`；该信号只由预览审阅提交写入 | `presentation_director.py` `cmd_finalize`、CONTEXT.md:214 |
| “保留当前版本”在复制成功前写信号 | 调换顺序：最终复制成功后才写 | `apply_preview_review` |
| 晋升后丢 `./assets/` | `finalize` 复用最终选择已有的 `copy_html_deck_assets`，把 `.draft/assets` 一起带到 `vN/` | `cmd_finalize` |
| “浏览器已打开”标记跨进程残留 | 删除持久标记，每次 `serve-wait` 都按 `--open-page` 打开 | `command_serve_wait` |
| 补图后没有开始信号 | `guard` 命令通过时写 `guard-passed.ready`，失败时删除旧信号；SKILL 第 6 步补一句“先生成图片模式下首次 guard 失败属预期，补图后运行 guard” | `command_guard`、SKILL.md |
| 中文弯引号被当成错误 | 两份校验都只检查标签内部的 `“”`（独立脚本第二轮已退役） | `html_deck_integrity_warnings` |
| 两份安装逻辑、漏装 pakco | `bootstrap.sh` 改为调用 `install.sh`；`install.sh` 本地与远程都带上 `skills/html-deck` | `install.sh`、`bootstrap.sh` |
| 文档旧路径 | README/MANUAL 改为 `Decks/`，说明旧 `PPTX/` 工程仍可继续 | README.md:17、MANUAL.md |

验证：`pytest` 135 passed（原 131 + 新增 4 个回归）；临时 HOME 安装后 `HTML_DECK_ROOT` 指向已安装的 `html-deck/pakco-html` 且存在；本机 `~/.claude/skills`、`~/.codex/skills` 已重新安装并与仓库一致。远程主机未同步（未运行 `--remote`）。

> 注：资源问题上 Claude 最初提议“HTML 一律内联成单文件”，核实后放弃——pakco 运行时通过 `data-theme-base="./assets/themes/"` 动态切换主题，内联会破坏主题切换；复用现有的资源复制函数更小，也符合 Codex 的“统一布局”方向。

---

## 二、待讨论（看法不同）

### R1. 同名任务重建读到旧选择

- **事实**：`init` 只清 `status/*.ready`，不清 `intake-selection.json`、`brief-confirmed.json`，确认页优先读 `intake-selection.json`。
- **Codex**：已有任务明确走恢复，重建使用新目录。
- **Claude**：不需要“恢复/重建”两种模式。恢复本来就是不跑 `init`、直接跑 `serve-wait`；`init` 的语义就是重新开始，所以只需在 `init` 时删掉这两份选择文件（约 2 行）。用新目录会改变“任务名 = 目录名”的约定，`--task` 之后的所有命令都要知道新目录名。
- **待决**：选哪种？

### R2. PPTX 预览门只验证文件非空

- **Codex**：复用生成器已有的渲染和 QA 证据，把“文件到齐”和“QA 通过”表达清楚。
- **Claude**：不做。预览审阅页让用户亲眼看缩略总图，用户就是这一层的检查者；生成器自己也有渲染检查。Director 再验证一次属于重复防御。没有“无效 PPTX 通过预览门后被交付”的实际发生记录。
- **待决**：是否有实际出现过的失败，能支撑加这一层？

### R3. 确认边界（页面所见 vs 磁盘 brief、Origin、反向代理、操作者身份）

- **Codex**：修复聚焦于绑定用户实际看到的 brief。
- **Claude**：不做。页面与磁盘不一致只有在 agent 于确认页打开期间改写 brief 时才会出现，是推演出来的时序，没有触发记录；Origin、反向代理、操作者身份对仅在本机回环地址运行的工具不适用。BPS 正式链路已有独立的可信确认，不受影响。
- **待决**：是否有实际触发路径？

### R4. HTML 校验重复实现

- **Codex**：先共用一份校验实现；减少 `finalize`、`guard`、打开预览、最终选择中的重复视觉检查。
- **Claude**：
  - 独立的 `validate_html_deck.py` 只被 `docs/quality-gates.md` 提到，流程不调用它——直接删除（并改文档）比“合并成共用实现”更简单。本轮只修了它的引号规则，没删。
  - 重复视觉检查只是多花几秒；去掉最终选择那一次，定稿后手改过的文件就可能漏检。建议保持。
- **待决**：删除独立校验脚本还是抽共用实现？重复视觉检查是否真的慢到影响使用？

### R5. Claude 路径的确认轮次合并（大纲、色板、结构、Director brief）

- **Codex**：值得做产品取舍，一页看完一次确认。
- **Claude**：不建议。色板和结构候选依赖大纲和 `deck.md`；大纲一改，后面候选要重做，合成一页反而“改一处、整页重确认”。色板是可视化选择、大纲是文字审阅，放一页过长。若以后真嫌轮次多，最多合并内容类两项（大纲 + brief），视觉类保持分开；也应等真实使用记录了轮次再决定。
- **待决**：是否同意先不合并、先记录实际轮次？

### R6. 图片等待的交接方式（已做最小部分）

- **已做**：`guard` 写开始信号，SKILL 说明首次失败属预期。
- **Codex 原建议更多**：“确认后明确交出已批准的图片任务，登记素材后通过同一入口恢复”。
- **待决**：`serve-wait --then-guard` 在“只差图片”时，是否要输出区别于 `GUARD_FAILED` 的状态？Claude 认为现在 SKILL 已说明，不需要再加。

---

## 三、一致但须在 Codex 里执行

### C1. Codex PPTX 路径绑定旧运行时

- **事实**：`~/.codex/plugins/cache/openai-primary-runtime/presentations/26.1118.11504/` 中不存在 `scripts/check_presentation_runtime.mjs` 与 `scripts/build_artifact_deck.mjs`；当前 Presentations SKILL 的默认去向是 Spaces，本地 Artifact Tool 只用于 SharePoint 交付或允许的后备。
- **双方一致**：按当前官方路由真实导出一次 PPTX，再统一 CONTEXT.md:47 附近、SKILL.md 第 7 步、README 第 4 步的说明。
- **为何没做**：Spaces 的 `create_spaces_artifact` / `connect_spaces_artifact` 只在 Codex 会话里可用，Claude Code 无法完成真实导出验收；未验收前不改文档。

---

## 四、NECTO 接入（Claude 补充，Codex 原文未覆盖）

Codex 的第一步建议（NECTO 只做资料交接，制稿仍走现有 Director）Claude 同意，补充以下事实：

1. **挂载什么**：挂载做稿的项目文件夹（含 `Decks/<任务名>/`），打开写入开关。NECTO 的 `open_workspace/read/write/edit` 只能访问已挂载目录。用途是写 `Decks/<任务名>/sources/`（SKILL.md:126 已有该约定）和读回 `final/`。
2. **不必挂载 Presentation-Director 仓库**：NECTO 扩展中没有任何加载 Skill 的代码，侧边栏网页模型（ChatGPT/DeepSeek 等）用不了 deck-builder 技能。
3. **NECTO 目前无法驱动 Director 运行**：命令只能走 `host_command`，需要“临时完全主机访问（高信任）”；普通运行上限 100 秒，`start` 后台上限 300 秒（necto `development/host-control/native/host/host-command.js:20-23`）。`serve-wait` 需要等用户点完资料→视觉→确认，通常超过 5 分钟，本机确认服务会被中途终止。`finalize` 还要求本机有 python3 与 Playwright。
4. **`application_mcp` 窄接口**：同样需要高信任授权；服务进程的存活时长未验证。若试用证明瓶颈在启动/查状态，第一个要解决的是上面这个时长限制。

- **待决**：Codex 是否同意第 3 点是接入前提；“启动 + 查状态 + 取产物路径”的窄接口是否应设计成“启动后立即返回、状态靠读挂载目录里的 `status/*.ready`”，从而绕开长时间阻塞？

---

## 五、第二轮结论（Codex 回复后，基线 `cb3fba5`）

| 项 | 结论 | 处理 |
|---|---|---|
| R1 | Codex 证据成立：删掉两份 JSON 后旧 `vN/` 仍在，预览仍选中旧版本。采用 Codex 方案。 | **已修**：`init` 遇到已有 `brief-draft.json` 的任务即拒绝，提示用 `serve-wait` 恢复或换新任务名；只放了 `sources/` 的目录仍可初始化（NECTO 交接需要）。原来清 `status/*.ready` 的代码由拒绝接管，已删除。MANUAL Q&A 同步。 |
| R2 | 一致：不加校验。现有提示已是“Missing or empty preview artifact”，未声称 QA 通过。 | 无需改动。 |
| R3 | **仍有分歧**，见下。 | 未改。 |
| R4 | 一致：退役独立校验脚本，保留终选复检。 | **已做**：删除 `validate_html_deck.py`，`docs/quality-gates.md` 改为以 `finalize` / `guard` 为强制校验（Director 自身检查已覆盖原脚本全部项目）。开页前与 GET 的相邻重复检查（实测单次 4.5–5.5 秒）等实际感到停顿再减。 |
| R5 | 一致：先不合并，先记录真实轮次。 | 无改动。 |
| R6 | 一致：不加专用状态。 | 无改动。 |
| C1 | **新发现的冲突，需 owner 决定**，见下。 | 未改文档。 |
| NECTO | 接受 Codex 更正：“通常超过五分钟”没有实测，撤回；结论改为“`start` 300 秒上限内无法保证覆盖人工确认时长”。接入验收需覆盖等待期间服务存活、授权撤销/关闭后的行为。 | 仅文档结论，无代码。 |

### R3 剩余分歧

- Codex：两个标签页（一个确认页、一个 intake/视觉页）是代码可达路径，确认会保存最新选择而非页面所见；建议绑定表单展示的 brief 版本，变化时要求刷新。
- Claude：路径存在，但需要用户自己再开第二个标签并在那里改选；被确认的是**同一用户**最新的选择，不是未经授权的内容，生成前还有预览审阅可以纠正。按“被保护的是什么”判断，属观察项，不建议现在加版本绑定。
- 待 owner 决定：是否接受作为观察项。

### C1 新冲突：官方交付规则 vs Director 的本地 PPTX

- Codex 实测：Artifact Session 内 `presentation.export({format:"pptx"})` 成功，19,464 字节、1 页，官方 finalizer 校验通过。
- 但当前官方 Presentations 规则（`26.1118.11504/skills/presentations/SKILL.md:23`、`:260`；`references/artifact_sessions.md:79-83`）：SharePoint、Google Slides 以外一律交付 **Spaces 演示**，“即使用户要离线 PPTX 也给 Spaces 链接，让用户在查看器里下载”；`presentation.export` 只用于 SharePoint 或“允许的 PPTX 后备”，Spaces 路径“不附 PPT/PPTX 副本”。
- Director 的 PPTX 路径整体建立在本地 `Decks/<任务>/vN/final.pptx` + `contact-sheet.png` 上（预览审阅、风格审阅、终选复制都依赖它）。
- 所以 C1 不是单纯改文档：要么 Director 改为接受 Spaces 演示（链接 + 会话渲染图）作为 PPTX 路径的产物，要么明确把本地导出定为“允许的后备”并说明依据。两条都会改变用户可见行为，需 owner 决定后再改 CONTEXT.md:47、SKILL.md 第 7 步、README 第 4 步。Spaces 页面创建、连接、界面下载仍未验收。
