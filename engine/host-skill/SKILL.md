---
name: presentation-director
description: 把用户提供的资料（周报、方案、文章、表格等）做成可在 PowerPoint 或 WPS 里继续编辑的 PPT。用户要求做 PPT、演示文稿、幻灯片、汇报材料时使用。需要已连接的 presentation-director 连接器。
---

# Presentation Director

用 presentation-director 连接器的 6 个工具，按顺序完成。不要跳步，不要替用户点确认。

## 1. 开始

- 调用 `start_task`：`request_text` 填用户原话；`source_paths` 填用户给的资料文件的绝对路径。
- 调用 `open_confirmation`，然后对用户说：「确认页已在浏览器打开。请在页面里选好方向、页数和风格，点「确认」后回来告诉我。」
- 等用户回复。用户说已确认后，调用 `get_status`：
  - `ready_to_generate` 为 false：把 `guard_errors` 用一句话告诉用户，请他回到确认页完成。
  - 为 true：继续下一步。

## 2. 写逐页内容并生成

先读完资料，再按 `get_status` 返回的 `confirmed_brief` 写逐页内容：

- 页数按 `confirmed_brief.selections.output_constraints`；正文语言按 `content_language`。
- 听众与目的按 `audience`、`goal`，标题写成一句结论（例如「支付模块落后计划 18 个百分点」），不要只写「支付模块」。
- 版式（每页一种）：
  - `cover` 封面（只能是第一页）
  - `bullets` 要点，最多 6 条
  - `two_column` 左右对比或「计划 / 需要的支持」
  - `chart` 柱状图 `bar`、折线图 `line`、饼图 `pie`（只能一组数据）；数据必须来自资料，不要编造
  - `table` 表格，最多 6 列 8 行
  - `closing` 结尾：结论、下一步或需要拍板的事项
- 讲稿写在每页的 `notes`。
- 不写 `theme` 时，自动使用用户在确认页选的配色。

调用 `generate`。如果返回「逐页内容格式不对」，按提示改好再调用。

## 3. 检查

调用 `render_check`。
- `passed` 为 true：进入下一步。
- 有问题（例如文字可能溢出）：精简对应页的文字或拆成两页，重新 `generate`（会生成新版本），再 `render_check`。

## 4. 交付

调用 `export`，把返回的文件路径告诉用户，并说明：可以直接在 PowerPoint 或 WPS 里打开修改；图表数据可在图表上右键「编辑数据」修改。
