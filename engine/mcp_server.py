"""MCP server (stdio) that exposes the engine to AI hosts such as WorkBuddy, Claude and Codex."""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Iterator
from typing import Any

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from engine.core import Engine, EngineError
from engine.deck_spec import DeckSpec

INSTRUCTIONS = """\
Presentation Director：把用户的资料做成可编辑的 PPTX。必须按顺序：
1. start_task：传入用户原话和资料文件路径，得到 task。
2. open_confirmation：在用户浏览器打开确认页。告诉用户在页面里选好并点「确认」，你会自动继续。
3. wait_for_confirmation：反复调用直到 still_waiting 为 false。不要让用户回来说「已确认」。
   确认后 ready_to_generate 为 true 才能继续；confirmed_brief 是用户选的方向、页数和语言。
4. 读资料，按 confirmed_brief 写出逐页内容，调用 generate。
5. render_check：逐页渲染并检查；有问题就改逐页内容重新 generate（会生成新版本），再检查。
6. 检查通过后调用 export，把返回的文件路径交给用户，并说明可以在 PowerPoint 或 WPS 里继续编辑。
不要替用户点确认，也不要跳过检查直接交付。"""

server: MCPServer = MCPServer(name="presentation-director", instructions=INSTRUCTIONS)
_engine: Engine | None = None


def engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = Engine()
    return _engine


@contextlib.contextmanager
def quiet() -> Iterator[None]:
    # stdout carries the MCP protocol; any stray print from reused Director code must go to stderr.
    # EngineError messages are meant for the model, so pass them through instead of the SDK's generic text.
    with contextlib.redirect_stdout(sys.stderr):
        try:
            yield
        except EngineError as err:
            raise ToolError(str(err)) from err


@server.tool()
def start_task(
    request_text: str, topic: str = "", source_paths: list[str] | None = None
) -> dict[str, Any]:
    """新建演示任务。request_text 是用户原话；source_paths 是用户提供的资料文件绝对路径。"""
    with quiet():
        return engine().start_task(request_text, topic, source_paths or [])


@server.tool()
def open_confirmation(task: str) -> dict[str, Any]:
    """在用户浏览器打开问询与确认页，立即返回页面地址。用户在页面里确认后再调用 get_status。"""
    with quiet():
        return engine().open_confirmation(task)


@server.tool()
async def wait_for_confirmation(task: str) -> dict[str, Any]:
    """等待用户在确认页点「确认」，最多约 45 秒；still_waiting 为 true 时请再次调用，直到用户确认。"""
    with quiet():
        return await anyio.to_thread.run_sync(engine().wait_for_confirmation, task)


@server.tool()
def get_status(task: str) -> dict[str, Any]:
    """查询任务状态：是否已确认、能否生成、已确认的方向（confirmed_brief）和已有版本。"""
    with quiet():
        return engine().status(task)


@server.tool()
def generate(task: str, deck_spec: DeckSpec) -> dict[str, Any]:
    """按用户已确认的方向生成一个新版本 PPTX。deck_spec 是逐页内容；未确认时会被拒绝。"""
    with quiet():
        return engine().generate(task, deck_spec.model_dump_json())


@server.tool()
def render_check(task: str, version: str | None = None) -> dict[str, Any]:
    """逐页渲染并检查版面（默认最新版本），返回页图、总览图和问题列表。"""
    with quiet():
        return engine().render_check(task, version)


@server.tool()
def export(task: str, version: str | None = None, dest_dir: str | None = None) -> dict[str, Any]:
    """导出检查通过的版本（默认最新），返回 PPTX 路径；dest_dir 可指定导出文件夹。"""
    with quiet():
        return engine().export(task, version, dest_dir)


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
