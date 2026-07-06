# Presentation Director 全面审查（2026-07-06）

审查范围：`CONTEXT.md` 描述的流程逻辑、`skills/deck-builder/scripts/presentation_director.py`（核心编排脚本，6711 行）、`scripts/` 顶层入口、`skills/pptx`、`skills/html-deck/pakco-html`、`skills/ui-ux-pro-max`、`tests/`、`bootstrap.sh`。

方法：读代码 + 跑 `pytest`（35 passed）+ 跑 `ruff check .`（17 处）+ 对每一处 ruff 命中回读上下文，确认是真实功能问题还是纯风格噪音，不做未经验证的猜测性结论。

## 总体结论

工程质量本身不差：安全相关路径（路径穿越、伪造 Origin/Host、confirm token 校验、CSP）都有专门的 `SecurityRegressionTest` 覆盖，35 个测试全绿。真正的问题集中在三处，且都不需要动大架构：两个"计算了但没用上"的功能性字段（渐变预览、翻页动效），一处顶层脚本相对 skill 内规范版本的功能性漂移，以及 `guard` 命令对文档承诺的"技术保证"覆盖不完整。

## 1. 流程逻辑审查

`CONTEXT.md` 描述的 Content Lock → Form Lock → Composition Lock → Generation 四段锁定协议，与旧 gate 名称（Research Strategy / Visual Inspiration / Brief Confirmation / Image Style / Post-v1 Image Placement）的映射关系清楚，`validate_generation_guard()`（`presentation_director.py:1980`）里对图片模式、image plan、失败资产的作用域隔离写得比较细致（例如明确注释说明"过期失败记录不应阻塞重新配置后的运行"），逻辑站得住。

**发现的落差：`guard` 没有完整兑现 CONTEXT.md 里的"强制审查门"承诺。**

CONTEXT.md 第 182 行写道："审查由 AI 自动完成，技术上保证 v1/final.html 在通过全部 QA 之前物理上不存在"，并列出两类 QA：静态检查 和 Playwright 视觉检查（overflow / 网格对齐）。代码里：

- `cmd_finalize()`（第 2989 行）确实先跑静态检查，再跑 `playwright_visual_qa()`（第 2564 行定义），任何一类失败都 `raise SystemExit(2)`，不会把 `.draft/final.html` 复制成 `final.html`——这部分保证是真的。
- 但 `validate_generation_guard()` → `preview_review_gate_errors()`（第 2954 行）只重新跑了 `html_deck_integrity_warnings` / `html_small_font_warnings` / `html_structural_warnings` 三个静态检查，**没有调用 `playwright_visual_qa()`**。全仓库唯一调用 `playwright_visual_qa()` 的地方就是 `cmd_finalize()`（用 `grep -n "playwright_visual_qa("` 验证过，只有定义处和第 3023 行这一次调用）。

也就是说：如果 agent 违反规则、跳过 `finalize` 直接把内容写进 `v1/final.html`（CONTEXT.md 明令禁止的行为），之后只运行 `guard` 而不运行 `finalize`，`guard` 依然能通过——只要静态检查过关，即使存在文字溢出、网格错位这类只有 Playwright 才能抓到的问题。静态 QA 层的"技术保证"成立，**视觉 QA 层的"技术保证"不成立**，它退化为对 agent 自律的约定，而不是代码强制。

建议：让 `preview_review_gate_errors()`（或 `validate_generation_guard`）在检测到某个版本已存在 `final.html` 时，一并跑一次 `playwright_visual_qa()`，或者要求存在 `status/preview-reviewed.ready`（只有 `cmd_finalize` 会 touch 这个文件）才允许该版本通过 guard。后者改动更小：guard 只需检查该状态文件是否存在，就能确保"final.html 存在"和"跑过完整 finalize 流程"这两件事被绑定。

**次要发现：`validate_generation_guard` 内 `output_format` 计算了两次，默认值不一致。**

第 2009 行：`output_format_from_brief(brief, "html-revealjs")`；第 2079 行：`output_format_from_brief(brief, "pptx")`。两处只有在 `brief-confirmed.json` 缺失 `output_format` 字段时才会分叉，而按当前实现，`output_format` 在 `build_draft_brief` 阶段就会写入，guard 运行时该字段理论上必然存在，所以现在不会触发。但同一函数内两次计算同一语义变量却给不同默认值，属于容易在未来重构时踩坑的坏味道，建议合并成一次计算、存成局部变量复用。

## 2. 架构评审

`presentation_director.py` 是全项目最大的架构负债：单文件 6711 行，混合了六类职责——数据模型（`Choice`/`Question`/`VisualCandidate`）、路径与 JSON 工具、i18n 文案（`t()`）、HTML 页面拼接（20+ 个 `render_*` 函数，用 f-string 手写整页 HTML）、QA 规则（结构检查、字号检查、Playwright 视觉检查）、内嵌 HTTP server（`DirectorHandler(BaseHTTPRequestHandler)`）、CLI 命令分发。

这不是"写得差"，测试证明关键路径（尤其是 HTTP server 的安全边界）是认真加固过的；问题纯粹是"一个文件装了六个模块"，导致：改一个 `render_*` 函数要在 6700 行文件里定位，diff review 成本高，IDE 符号索引变慢。

**是否要拆分：建议列为可选项，不建议现在做。** 理由：
- 这是对已测试、已上线工作流的大范围结构性改动，改动面几乎覆盖全文件，回归风险和当前"零功能收益"不成比例。
- `bootstrap.sh` 证实 `skills/deck-builder/` 被设计为可独立同步到 `~/.claude/skills`、`~/.codex/skills` 甚至远程主机（`rsync` 到 `frank`）。拆分模块时要保证拆完的目录整体仍能被原样复制、且拆分后的相对 import 在被复制到 `~/.claude/skills/deck-builder/` 后依然可用——这本身要小心处理包内相对导入。
- 只有在你打算继续对这个脚本做大量新功能开发时，才值得投入：按职责拆成 `director_render.py`（HTML 模板）、`director_guard.py`（校验规则/QA）、`director_server.py`（HTTP handler）、`director_cli.py`（argparse + command_*），用一个包 `__init__.py` 对外暴露和现在相同的 CLI 入口。

**`skills/` 下的"重复"是有意为之，不建议合并。** `scripts/presentation_director.py` 只有 465 字节，是用 `runpy` 转发到 `skills/deck-builder/scripts/presentation_director.py` 的 shim；`bootstrap.sh` 第 89-93 行把 `skills/deck-builder` 整体 `cp -r` 到全局 skill 目录——这证明 `skills/deck-builder` 必须自包含（不能依赖仓库顶层的 `scripts/`），否则复制出去就跑不起来。这个设计本身合理，不建议把两棵树合成一棵。

## 3. 代码冗余（真正需要处理的部分）

顶层 `scripts/` 和 `skills/deck-builder/scripts/` 下同名的三个文件里，只有一个是干净的（shim），另外两个是**过时分叉**而不是单纯重复：

| 文件 | 顶层 `scripts/` | `skills/deck-builder/scripts/` |
|---|---|---|
| `presentation_director.py` | 465 字节，`runpy` 转发到右侧文件 | 6711 行，规范实现 |
| `check_presentation_safe_area.py` | 与右侧字节级相同 | 规范版本 |
| `preview_locks.py` | 旧版：确认动作走"复制到剪贴板" | 新版：内置 `http.server` + `/confirmed` POST 端点 |
| `preview_palette.py` | 旧版：同上，复制到剪贴板 | 新版：同上，POST 端点 |

`skills/deck-builder/SKILL.md` 第 1075、1107 行明确指导仓库内用户运行 `python3 scripts/preview_palette.py` / `scripts/preview_locks.py`——也就是说文档引导用户运行的正是**顶层这份过时实现**，新功能（POST 确认端点）不会被走到。这是典型的"改了一份、忘了改另一份"的复制粘贴漂移，如果之后再修一次 bug，大概率还会只改中间那份规范文件，漂移只会越来越大。

**建议**：把 `scripts/preview_locks.py`、`scripts/preview_palette.py` 也改写成和 `scripts/presentation_director.py` 一样的 `runpy` shim，转发到 `skills/deck-builder/scripts/` 下的规范版本。`check_presentation_safe_area.py` 目前虽然没有漂移，也顺手改成 shim，一次性把"顶层脚本"这个概念统一成"全部是 shim，规范实现只有一份"，以后不会再长出新的分叉。这个改动不影响任何对外行为（CLI 参数、输出路径都不变），风险很低。

## 4. 具体小问题（已逐条读代码验证，非仅凭 ruff 报告）

### Medium — 功能性回归（字段算出来了，但没用上）

1. **`render_visual_candidate_card()`**（`presentation_director.py:4568-4630`）：`gradient_preview`（第 4584 行）拼好了一段展示 HTML 主题渐变色的 `<div>`，但函数最终 `return` 的卡片模板（第 4605-4630 行）里没有引用这个变量。结果：只要 `output_format` 是 `html-revealjs`/`both` 且候选主题设置了 `html_gradient`，用户在 Visual Inspiration 页面也永远看不到对应的渐变预览。
2. **HTML 生成指令拼装处**（`presentation_director.py:5548-5573`，在构造 `html_requirements` 的函数内）：`html_transition`（第 5560 行）算出来后从未被插入 `html_requirements` 字符串；紧邻它的 `html_gradient` 在第 5573 行正确地被用上了（`Background hint: "{html_gradient or ...}"`），唯独 transition 被漏用。结果：brief 里锁定的翻页动效（`transition` 字段）不会出现在发给生成 agent 的 HTML deck 生成规格里，生成方只能靠默认动效，锁定协议里"Form Lock 决定动效"这一环节在这个字段上失效。

两处都是"计算了但没接线"的典型 bug，建议直接补上（把变量插回对应模板字符串），改动量各一行，不涉及架构。

### Low / Maintainability

3. `render_visual_inspiration()` 第 4523 行 `current_candidate` 算出来后完全没用，纯遗留死代码，删掉即可。
4. 第 2 节提到的 `validate_generation_guard` 里 `output_format` 两次计算、默认值不一致（第 2009 / 2079 行），建议合并成一次。
5. `ruff check .` 命中的另外 11 处都在 `skills/ui-ux-pro-max/`（`search.py` 未用的 import、4 处多余 `f""` 前缀、`design_system.py` 3 处未用局部变量、`_sync_all.py` 1 处 `E401` + 1 处未用局部变量）——纯风格问题，无功能影响。因为 `ui-ux-pro-max` 也是这个仓库维护的规范源（`bootstrap.sh` 会把它复制出去，而不是从别处同步进来），可以直接 `ruff check . --fix` 处理，不存在"改了会和上游脱节"的顾虑。
6. `package.json` 里 `"name": "md2ppt"` 是项目改名前的旧名（`CONTEXT.md` 开篇就说明"仓库早期名为 MD2PPT；以后统一用 Presentation Director"），纯命名一致性问题，无功能影响，顺手可改成 `presentation-director`。

## 5. 测试与验证现状（供参考，不是本次审查新增）

```
python3 -m pytest tests/ -q
...................................
35 passed in 11.25s
```

`SecurityRegressionTest`（`tests/test_presentation_director.py:602-793`）已经覆盖：static 路由拒绝读取 `confirm.token`、拒绝 symlink 逃逸、CSP header 校验、POST 端点要求 workflow token、拒绝伪造 Host/Origin 组合、`final-selection` 拒绝版本目录穿越（`../../outside-secret`）、图片输出路径必须落在 `assets/images/` 下。这部分安全基本盘已经很扎实，不需要在这次审查里额外投入。

## 6. 行动清单（按优先级）

- **P1（建议做，改动小、收益明确）**
  - 修复 `gradient_preview`、`html_transition` 两处未接线字段（第 4 节 #1、#2）。
  - 把 `scripts/preview_locks.py`、`scripts/preview_palette.py`（视情况也包括 `check_presentation_safe_area.py`）统一改成转发规范实现的 shim，消除文档引导用户运行过时版本的问题（第 3 节）。
  - 让 `guard`（或 `preview_review_gate_errors`）在版本已生成 `final.html` 时，要求 `status/preview-reviewed.ready` 存在（即必须跑过 `finalize`），补上视觉 QA 层的强制保证（第 1 节）。
- **P2（可选，低风险清理）**
  - `ruff check . --fix` 清理 `ui-ux-pro-max` 下的 11 处风格问题。
  - 删除 `current_candidate` 死代码；合并 `validate_generation_guard` 里两次 `output_format` 计算。
  - `package.json` 更名。
- **P3（不建议现在做，仅记录以备将来）**
  - 把 `presentation_director.py` 按职责拆成多模块。只有在计划对这个脚本继续大量新增功能时才值得启动；作为整理性重构，投入产出比目前不划算。
