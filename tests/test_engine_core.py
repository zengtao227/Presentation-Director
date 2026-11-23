from __future__ import annotations

import json
import shutil
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import anyio
import pytest

from engine import render_check
from engine.core import Engine, EngineError

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (ROOT / "engine" / "samples" / "weekly-report.json").read_text(encoding="utf-8")
HAS_NODE = (
    shutil.which("node") is not None and (ROOT / "engine" / "generator" / "node_modules").exists()
)


def confirm_like_user(eng: Engine, task: str, output_format: str | None = None) -> None:
    """Walk intake -> visual -> confirm through the real confirmation server, as the form posts do."""
    task_dir = eng.task_dir(task)
    url = eng.open_confirmation(task, open_browser=False)["url"]
    base = url.rsplit("/", 1)[0]
    urlopen(url, timeout=5).read()
    token = (task_dir / "status" / "confirm.token").read_text(encoding="utf-8").strip()

    def post(path: str, data: dict[str, str]) -> None:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        req = Request(base + path, data=urlencode(data).encode(), method="POST", headers=headers)
        urlopen(req, timeout=5).read()

    intake = {"director_token": token}
    if output_format:
        intake["output_format"] = output_format
    post("/api/intake", intake)
    selection = json.loads((task_dir / "intake-selection.json").read_text(encoding="utf-8"))
    candidates = eng.pd.build_visual_candidates(
        "x", selection["selections"], selection.get("figma_source_packet", {})
    )
    post(
        "/api/visual-inspiration", {"director_token": token, "visual_candidate": candidates[0].key}
    )
    post("/api/confirm", {"director_token": token, "confirm_token": token})
    eng.close_confirmation(task)


@pytest.fixture(autouse=True)
def _render_with_libreoffice_in_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tests compare page counts only; keep them from opening the developer's PowerPoint or Keynote.
    if render_check.find_soffice() is not None:
        monkeypatch.setenv("PD_PPTX_RENDERER", "libreoffice")


@pytest.fixture()
def eng(tmp_path: Path) -> Engine:
    return Engine(tmp_path / "ws")


def test_new_task_preselects_pptx_without_ai_images(eng: Engine) -> None:
    task = eng.start_task("做一份周报")["task"]
    draft = json.loads((eng.task_dir(task) / "brief-draft.json").read_text(encoding="utf-8"))
    assert draft["selections"]["output_format"]["value"] == "pptx"
    assert draft["selections"]["image_policy"]["value"] == "none"


def test_generate_is_refused_until_the_user_confirms(eng: Engine) -> None:
    task = eng.start_task("做一份周报")["task"]
    with pytest.raises(EngineError, match="生成前检查没有通过"):
        eng.generate(task, SAMPLE)
    assert eng.status(task)["ready_to_generate"] is False


def test_unknown_task_is_reported(eng: Engine) -> None:
    with pytest.raises(EngineError, match="任务不存在"):
        eng.status("nope")


@pytest.mark.skipif(not HAS_NODE, reason="node or generator deps missing")
def test_full_flow_generate_check_export(eng: Engine, tmp_path: Path) -> None:
    task = eng.start_task("用这份项目周报，做一份 6 页中文 PPT")["task"]
    confirm_like_user(eng, task)
    assert eng.status(task)["ready_to_generate"] is True

    bad = json.loads(SAMPLE)
    bad["slides"][3]["table"]["rows"][0].pop()
    with pytest.raises(EngineError, match="逐页内容格式不对"):
        eng.generate(task, json.dumps(bad, ensure_ascii=False))

    first = eng.generate(task, SAMPLE)
    assert first["version"] == "v1" and Path(first["pptx"]).is_file()
    with pytest.raises(EngineError, match="还没有做渲染检查"):
        eng.export(task)

    report = eng.render_check(task)
    if render_check.find_soffice() is None:
        assert not report["passed"] and any("LibreOffice" in i for i in report["issues"])
        with pytest.raises(EngineError, match="检查没有通过"):
            eng.export(task)
        return
    assert report["passed"], report["issues"]
    assert report["pages"] == 6 and Path(report["contact_sheet"]).is_file()

    assert eng.generate(task, SAMPLE)["version"] == "v2"
    exported = eng.export(task, "v1", str(tmp_path / "out"))
    assert Path(exported["pptx"]).name == "星河项目第 12 周进展汇报.pptx"
    assert [v["version"] for v in eng.status(task)["versions"]] == ["v1", "v2"]


@pytest.mark.skipif(not HAS_NODE, reason="node or generator deps missing")
def test_structure_check_flags_overflowing_text(tmp_path: Path) -> None:
    import subprocess

    from engine.core import GENERATOR
    from engine.deck_spec import DeckSpec

    spec = json.loads(SAMPLE)
    spec["slides"] = [
        {
            "layout": "bullets",
            "title": "很长的要点",
            "bullets": ["这是一条故意写得非常长的要点" * 8] * 6,
        }
    ]
    path = tmp_path / "spec.json"
    path.write_text(DeckSpec.model_validate(spec).model_dump_json(), encoding="utf-8")
    pptx = tmp_path / "long.pptx"
    subprocess.run(["node", str(GENERATOR), str(path), str(pptx)], check=True, capture_output=True)
    issues = render_check.structure_issues(pptx)
    assert any("溢出" in i for i in issues), issues


def test_mcp_server_lists_tools_and_passes_refusals_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PD_WORKSPACE", str(tmp_path / "ws"))
    from mcp.server.mcpserver.exceptions import ToolError

    from engine import mcp_server

    monkeypatch.setattr(mcp_server, "_engine", None)

    async def run() -> None:
        names = [t.name for t in await mcp_server.server.list_tools()]
        assert names == [
            "start_task",
            "open_confirmation",
            "wait_for_confirmation",
            "get_status",
            "generate",
            "render_check",
            "export",
        ]
        task = mcp_server.start_task("做一份周报")["task"]
        with pytest.raises(ToolError, match="生成前检查没有通过"):
            await mcp_server.server.call_tool(
                "generate", {"task": task, "deck_spec": json.loads(SAMPLE)}
            )

    anyio.run(run)


def test_confirmed_palette_is_used_unless_spec_sets_a_theme() -> None:
    brief = {
        "visual_direction": {
            "selected_candidate": {"palette": ["#ffffff", "#0f172a", "#7c3aed", "#06b6d4"]}
        }
    }
    without_theme = json.loads(Engine._apply_confirmed_palette(SAMPLE, brief))
    assert without_theme["theme"] == {
        "background": "#ffffff",
        "text": "#0f172a",
        "accent": "#7c3aed",
        "accent2": "#06b6d4",
    }
    own = json.loads(SAMPLE)
    own["theme"] = {"accent": "#ff0000"}
    kept = json.loads(Engine._apply_confirmed_palette(json.dumps(own), brief))
    assert kept["theme"] == {"accent": "#ff0000"}


def test_wait_for_confirmation_returns_once_the_user_clicks(eng: Engine) -> None:
    task = eng.start_task("做一份周报")["task"]
    waiting = eng.wait_for_confirmation(task, timeout_s=1.5)
    assert waiting["still_waiting"] is True and waiting["confirmed"] is False

    import threading

    clicker = threading.Timer(1.0, confirm_like_user, args=(eng, task))
    clicker.start()
    done = eng.wait_for_confirmation(task, timeout_s=20)
    clicker.join()
    assert done["still_waiting"] is False and done["ready_to_generate"] is True


def test_html_deck_is_self_contained(tmp_path: Path) -> None:
    from engine.deck_spec import DeckSpec
    from engine.html_deck import build_html

    out = build_html(
        DeckSpec.model_validate_json(SAMPLE), "corporate-clean", tmp_path / "deck.html"
    )
    html = out.read_text(encoding="utf-8")
    assert html.count('<section class="slide') == 6
    assert "<svg" in html and '<table class="pd-table">' in html and 'class="notes"' in html
    # Nothing is fetched at open time: no external stylesheets, imports or scripts.
    assert "pd-check" in html and '<link rel="stylesheet"' not in html
    assert "@import" not in html and "<script src=" not in html


@pytest.mark.skipif(not HAS_NODE, reason="node or generator deps missing")
def test_both_formats_generate_check_and_export(eng: Engine, tmp_path: Path) -> None:
    task = eng.start_task("做一份演示")["task"]
    confirm_like_user(eng, task, "both")
    built = eng.generate(task, SAMPLE)
    assert Path(built["pptx"]).is_file() and Path(built["html"]).is_file()
    report = eng.render_check(task)
    assert set(report["formats"]) == {"pptx", "html"}
    if not report["passed"]:
        pytest.skip("renderer missing on this machine: " + "; ".join(report["issues"]))
    exported = eng.export(task, dest_dir=str(tmp_path / "out"))
    assert exported["pptx"].endswith(".pptx") and exported["html"].endswith(".html")


def test_office_app_is_preferred_over_libreoffice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PD_PPTX_RENDERER", raising=False)
    found = render_check.find_pptx_renderer()
    if found is None or found[0] == "libreoffice":
        pytest.skip("no PowerPoint, WPS or Keynote on this machine")
    assert found[0] in {"powerpoint-mac", "keynote", "powerpoint-win", "wps"}
