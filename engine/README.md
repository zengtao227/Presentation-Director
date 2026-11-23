# Presentation Director 本机引擎

把用户资料做成可编辑 PPTX 的本机引擎。命令行与 MCP 服务共用 `engine/core.py` 的同一套步骤：

1. `start_task` 新建任务（默认 PPTX、不用 AI 生图）
2. `open_confirmation` 打开问询 / 视觉方向 / 确认页（复用 `skills/deck-builder` 的页面与守卫）
3. `wait_for_confirmation` 等用户在页面点确认（每次最多约 45 秒，未确认就再调用；用户不需要回到对话里报告），`get_status` 随时查看状态
4. `generate` 按逐页内容（`schemas/deck-spec-v1.schema.json`）生成新版本 `Decks/<任务>/vN/final.pptx`；未确认时拒绝
5. `render_check` 用 LibreOffice 逐页出图并做版面检查，报告写在 `vN/check-report.json`
6. `export` 只导出检查通过的版本

## 依赖

- Python：`uv sync --extra engine`
- Node：`cd engine/generator && npm ci`（pptxgenjs 固定 4.0.1）
- LibreOffice：渲染检查用；可用环境变量 `PD_SOFFICE` 指定路径

环境变量：`PD_WORKSPACE`（任务目录，默认 `文档/Presentation Director`）、`PD_NODE`（Node 路径）。

## 命令行

```bash
python -m engine.cli start --request "用这份周报做 6 页中文 PPT" --source /path/周报.docx
python -m engine.cli confirm <任务>        # 打开确认页，等用户点确认
python -m engine.cli generate <任务> --spec deck-spec.json
python -m engine.cli check <任务>
python -m engine.cli export <任务> --dest ~/Desktop
```

## 作为 MCP 连接器（stdio）

```json
{
  "mcpServers": {
    "presentation-director": {
      "type": "stdio",
      "command": "<Python 路径>",
      "args": ["-m", "engine.mcp_server"],
      "env": { "PYTHONPATH": "<本仓库或安装目录>" }
    }
  }
}
```

已知：macOS 27 上的 LibreOffice 26.8 会丢失非粗体中文，Mac 上的出图不能用来判断中文版面；页数与结构检查不受影响。
