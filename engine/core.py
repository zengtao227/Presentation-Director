"""Engine core shared by the command line and the MCP server.

It reuses the Director's intake/confirmation pages and generation guard, and adds the host-neutral
PPTX path: deck-spec v1 -> pptxgenjs generator -> render/structure check -> export.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any

from pydantic import ValidationError

from engine import html_deck, render_check
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
# Director output_format values -> files the engine builds.
FORMATS: dict[str, tuple[str, ...]] = {
    "pptx": ("pptx",),
    "html-revealjs": ("html",),
    "both": ("pptx", "html"),
}


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
        # Most users of AI hosts want an editable PPT, and the engine has no image generation yet; preselect
        # both. The user can still pick HTML or both on the intake page.
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

    def wait_for_confirmation(self, task: str, timeout_s: float = 45.0) -> dict[str, Any]:
        """Block until the user clicks confirm on the page, or until timeout_s passes.

        Short waits keep each call under hosts' tool-call time limits; the model simply calls again
        while still_waiting is true, so the user never has to come back and say they confirmed.
        """
        deadline = time.monotonic() + timeout_s
        while True:
            state = self.status(task)
            if state["confirmed"] or time.monotonic() >= deadline:
                state["still_waiting"] = not state["confirmed"]
                return state
            time.sleep(1)

    def generate(self, task: str, deck_spec: dict[str, Any] | str) -> dict[str, Any]:
        task_dir = self.task_dir(task)
        # Earlier versions' agent-authored preview gates (vN: ...) do not apply: the engine's own
        # render_check is mandatory before export, so only the confirmation part of the guard is used here.
        errors = [
            e for e in self.pd.validate_generation_guard(task_dir) if not re.match(r"^v\d+: ", e)
        ]
        if errors:
            raise EngineError(
                "生成前检查没有通过（通常是用户还没在确认页点确认）：\n- " + "\n- ".join(errors)
            )
        brief = self.pd.read_json(task_dir / "brief-confirmed.json")
        formats = FORMATS.get(self.pd.output_format_from_brief(brief, "pptx"), ("pptx",))
        try:
            raw = (
                deck_spec
                if isinstance(deck_spec, str)
                else json.dumps(deck_spec, ensure_ascii=False)
            )
            spec = DeckSpec.model_validate_json(self._apply_confirmed_palette(raw, brief))
        except ValidationError as err:
            raise EngineError("逐页内容格式不对：\n- " + "\n- ".join(describe_errors(err))) from err
        existing = self._versions(task_dir)
        version = f"v{int(existing[-1][1:]) + 1 if existing else 1}"
        version_dir = task_dir / version
        version_dir.mkdir()
        outputs = self._build(spec, version_dir, formats, self._html_theme(brief))
        return {"task": task, "version": version, "slides": len(spec.slides), **outputs}

    @staticmethod
    def _html_theme(brief: dict[str, Any]) -> str | None:
        direction = brief.get("visual_direction")
        candidate = direction.get("selected_candidate") if isinstance(direction, dict) else None
        suggested = candidate.get("suggested_html_theme") if isinstance(candidate, dict) else None
        return brief.get("html_theme_key") or suggested

    def _build(
        self,
        spec: DeckSpec,
        out_dir: Path,
        formats: tuple[str, ...] = ("pptx",),
        theme: str | None = None,
    ) -> dict[str, str]:
        spec_path = out_dir / "deck-spec.json"
        spec_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
        outputs: dict[str, str] = {}
        if "html" in formats:
            outputs["html"] = str(html_deck.build_html(spec, theme, out_dir / "final.html"))
        if "pptx" not in formats:
            return outputs
        pptx = out_dir / "final.pptx"
        result = subprocess.run(
            [self.node, str(GENERATOR), str(spec_path), str(pptx)],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if result.returncode != 0 or not pptx.is_file():
            raise EngineError(f"生成失败：{result.stderr.strip()[-800:]}")
        outputs["pptx"] = str(pptx)
        return outputs

    @staticmethod
    def _apply_confirmed_palette(raw: str, brief: dict[str, Any]) -> str:
        """Use the colours of the visual direction the user confirmed unless the spec sets its own."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        direction = brief.get("visual_direction")
        candidate = direction.get("selected_candidate") if isinstance(direction, dict) else None
        palette = candidate.get("palette") if isinstance(candidate, dict) else None
        if not isinstance(data, dict) or "theme" in data:
            return raw
        if not isinstance(palette, list) or len(palette) < 4:
            return raw
        keys = ("background", "text", "accent", "accent2")
        data["theme"] = dict(zip(keys, palette[:4], strict=True))
        return json.dumps(data, ensure_ascii=False)

    def selftest(self) -> dict[str, Any]:
        """Build and check the bundled sample outside any task, so an install proves node, the
        generator and LibreOffice work before the user's first real deck."""
        out = self.workspace / ".selftest"
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        sample = (ENGINE_DIR / "samples" / "weekly-report.json").read_text(encoding="utf-8")
        spec = DeckSpec.model_validate_json(sample)
        self._build(spec, out, ("pptx", "html"))
        return self._check_outputs(out, "selftest", len(spec.slides))

    def _check_outputs(self, version_dir: Path, version: str, expected: int) -> dict[str, Any]:
        reports: dict[str, render_check.CheckReport] = {}
        if (version_dir / "final.pptx").is_file():
            profile = self.workspace / ".libreoffice-profile"
            reports["pptx"] = render_check.check(
                version_dir / "final.pptx", version, expected, profile
            )
        if (version_dir / "final.html").is_file():
            profile = self.workspace / ".browser-profile"
            reports["html"] = render_check.check_html(
                version_dir / "final.html", version, expected, profile
            )
        if not reports:
            raise EngineError(f"{version} 里没有生成好的文件。")
        first = next(iter(reports.values()))
        combined = {
            "version": version,
            "passed": all(r.passed for r in reports.values()),
            "issues": [i for r in reports.values() for i in r.issues],
            "expected_pages": expected,
            "pages": first.pages,
            "renderer": " + ".join(r.renderer for r in reports.values()),
            "contact_sheet": first.contact_sheet,
            "images": first.images,
            "formats": {name: r.to_json() for name, r in reports.items()},
        }
        (version_dir / "check-report.json").write_text(
            json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return combined

    def render_check(self, task: str, version: str | None = None) -> dict[str, Any]:
        task_dir = self.task_dir(task)
        version_dir = self._version_dir(task_dir, version)
        spec = json.loads((version_dir / "deck-spec.json").read_text(encoding="utf-8"))
        return {
            "task": task,
            **self._check_outputs(version_dir, version_dir.name, len(spec["slides"])),
        }

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
        exported: dict[str, str] = {}
        for ext in ("pptx", "html"):
            source = version_dir / f"final.{ext}"
            if source.is_file():
                target = target_dir / f"{safe_title}.{ext}"
                shutil.copyfile(source, target)
                exported[ext] = str(target)
        return {"task": task, "version": version_dir.name, **exported}
