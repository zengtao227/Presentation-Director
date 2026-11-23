"""Engine core shared by the command line and the MCP server.

It reuses the Director's intake/confirmation pages and generation guard, and adds the host-neutral
PPTX path: deck-spec v1 -> pptxgenjs generator -> render/structure check -> export.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any

from pydantic import ValidationError

from engine import render_check
from engine.deck_spec import DeckSpec, describe_errors

ENGINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = ENGINE_DIR.parent
DIRECTOR_SCRIPT = Path(
    os.environ.get(
        "PD_DIRECTOR_SCRIPT",
        REPO_ROOT / "skills" / "deck-builder" / "scripts" / "presentation_director.py",
    )
)
GENERATOR = ENGINE_DIR / "generator" / "generate.mjs"


class EngineError(Exception):
    """A user-facing refusal or failure; the message is shown to the host model as-is."""


def _load_director() -> ModuleType:
    spec = importlib.util.spec_from_file_location("presentation_director", DIRECTOR_SCRIPT)
    if spec is None or spec.loader is None:
        raise EngineError(f"找不到 Presentation Director 脚本：{DIRECTOR_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolve annotations through sys.modules, so register before executing.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def default_workspace() -> Path:
    configured = os.environ.get("PD_WORKSPACE")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "Documents" / "Presentation Director"


class Engine:
    def __init__(self, workspace: Path | None = None, node: str | None = None) -> None:
        self.workspace = (workspace or default_workspace()).expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.node = node or os.environ.get("PD_NODE") or shutil.which("node") or "node"
        self.pd = _load_director()
        self._servers: dict[str, tuple[ThreadingHTTPServer, str]] = {}
        self._lock = threading.Lock()

    # ---- task folders -------------------------------------------------------------------------

    def task_dir(self, task: str) -> Path:
        slug = self.pd.slugify(task)
        path = self.pd.resolve_workspace_root(self.workspace, slug)
        if not (path / "brief-draft.json").exists():
            raise EngineError(f"任务不存在：{task}。请先调用 start_task。")
        return path

    def _versions(self, task_dir: Path) -> list[str]:
        found = [
            p.name for p in task_dir.iterdir() if p.is_dir() and self.pd.version_number(p) >= 1
        ]
        return sorted(found, key=lambda name: int(name[1:]))

    def _version_dir(self, task_dir: Path, version: str | None) -> Path:
        versions = self._versions(task_dir)
        if not versions:
            raise EngineError("这个任务还没有生成任何版本。")
        name = version or versions[-1]
        if name not in versions:
            raise EngineError(f"没有版本 {name}，现有版本：{', '.join(versions)}")
        return task_dir / name

    # ---- steps ------------------------------------------------------------------------------

    def start_task(
        self, request_text: str, topic: str = "", sources: list[str] | None = None
    ) -> dict[str, Any]:
        slug = datetime.now().strftime("deck-%Y%m%d-%H%M%S")
        task_dir = self.pd.workspace_root(self.workspace, "", slug)
        task_dir.mkdir(parents=True, exist_ok=False)
        brief = self.pd.build_draft_brief(
            slug, topic or request_text[:80], list(sources or []), "auto", request_text
        )
        # This engine only produces PPTX and has no image generation yet, so preselect both; the user can
        # still change them on the intake page, and generate() refuses anything it cannot produce.
        questions = {q.key: q for q in self.pd.INTAKE_QUESTIONS}
        for key, value in (("output_format", "pptx"), ("image_policy", "none")):
            label = self.pd.selected_choice(questions[key], value).label
            brief["selections"][key] = {"value": value, "label": label, "source": "default"}
        self.pd.write_json(task_dir / "brief-draft.json", brief)
        self.pd.write_json(task_dir / "brief" / "draft-brief.json", brief)
        self.pd.render_all_pages(task_dir)
        return {"task": slug, "task_dir": str(task_dir)}

    def open_confirmation(self, task: str, open_browser: bool = True) -> dict[str, Any]:
        task_dir = self.task_dir(task)
        with self._lock:
            if task in self._servers:
                url = self._servers[task][1]
            else:
                handler = type(
                    "BoundDirectorHandler", (self.pd.DirectorHandler,), {"task_dir": task_dir}
                )
                server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
                host, port = self.pd.director_server_host_port(server, "127.0.0.1")
                url = self.pd.director_url(host, port, self.pd.PAGE_PATHS["intake"])
                threading.Thread(target=server.serve_forever, daemon=True).start()
                self._servers[task] = (server, url)
        if open_browser:
            webbrowser.open(url)
        return {"task": task, "url": url}

    def close_confirmation(self, task: str) -> None:
        with self._lock:
            entry = self._servers.pop(task, None)
        if entry:
            entry[0].shutdown()
            entry[0].server_close()

    def status(self, task: str) -> dict[str, Any]:
        task_dir = self.task_dir(task)
        confirmed = (self.pd.status_dir(task_dir) / self.pd.STATUS_FILES["confirmed"]).exists()
        guard_errors = self.pd.validate_generation_guard(task_dir) if confirmed else []
        versions = []
        for name in self._versions(task_dir):
            report = task_dir / name / "check-report.json"
            passed = (
                json.loads(report.read_text(encoding="utf-8")).get("passed")
                if report.exists()
                else None
            )
            versions.append({"version": name, "check_passed": passed})
        brief = self.pd.read_json(task_dir / "brief-confirmed.json") if confirmed else {}
        return {
            "task": task,
            "confirmed": confirmed,
            "ready_to_generate": confirmed and not guard_errors,
            "guard_errors": guard_errors,
            "confirmed_brief": brief,
            "versions": versions,
        }

    def generate(self, task: str, deck_spec: dict[str, Any] | str) -> dict[str, Any]:
        task_dir = self.task_dir(task)
        errors = self.pd.validate_generation_guard(task_dir)
        if errors:
            raise EngineError(
                "生成前检查没有通过（通常是用户还没在确认页点确认）：\n- " + "\n- ".join(errors)
            )
        brief = self.pd.read_json(task_dir / "brief-confirmed.json")
        output_format = self.pd.output_format_from_brief(brief, "pptx")
        if output_format != "pptx":
            raise EngineError(f"这个版本只支持 PPTX 输出，用户选择的是 {output_format}。")
        try:
            raw = (
                deck_spec
                if isinstance(deck_spec, str)
                else json.dumps(deck_spec, ensure_ascii=False)
            )
            spec = DeckSpec.model_validate_json(raw)
        except ValidationError as err:
            raise EngineError("逐页内容格式不对：\n- " + "\n- ".join(describe_errors(err))) from err
        existing = self._versions(task_dir)
        version = f"v{int(existing[-1][1:]) + 1 if existing else 1}"
        version_dir = task_dir / version
        version_dir.mkdir()
        spec_path = version_dir / "deck-spec.json"
        spec_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
        pptx = version_dir / "final.pptx"
        result = subprocess.run(
            [self.node, str(GENERATOR), str(spec_path), str(pptx)],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if result.returncode != 0 or not pptx.is_file():
            raise EngineError(f"生成失败：{result.stderr.strip()[-800:]}")
        return {"task": task, "version": version, "pptx": str(pptx), "slides": len(spec.slides)}

    def render_check(self, task: str, version: str | None = None) -> dict[str, Any]:
        task_dir = self.task_dir(task)
        version_dir = self._version_dir(task_dir, version)
        spec = json.loads((version_dir / "deck-spec.json").read_text(encoding="utf-8"))
        report = render_check.check(
            version_dir / "final.pptx",
            version_dir.name,
            len(spec["slides"]),
            self.workspace / ".libreoffice-profile",
        )
        return {"task": task, **report.to_json()}

    def export(
        self, task: str, version: str | None = None, dest_dir: str | None = None
    ) -> dict[str, Any]:
        task_dir = self.task_dir(task)
        version_dir = self._version_dir(task_dir, version)
        report_path = version_dir / "check-report.json"
        if not report_path.exists():
            raise EngineError(f"{version_dir.name} 还没有做渲染检查，请先调用 render_check。")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if not report.get("passed"):
            raise EngineError(
                f"{version_dir.name} 的检查没有通过，不能导出：\n- "
                + "\n- ".join(report.get("issues", []))
            )
        spec = json.loads((version_dir / "deck-spec.json").read_text(encoding="utf-8"))
        safe_title = "".join(ch for ch in spec["title"] if ch not in '\\/:*?"<>|').strip() or task
        target_dir = Path(dest_dir).expanduser() if dest_dir else task_dir / "final"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{safe_title}.pptx"
        shutil.copyfile(version_dir / "final.pptx", target)
        return {"task": task, "version": version_dir.name, "pptx": str(target)}
