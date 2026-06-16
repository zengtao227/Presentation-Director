from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from argparse import Namespace
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Iterator
from types import ModuleType
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT_DIR: Path = Path(__file__).resolve().parents[1]
MODULE_PATH: Path = ROOT_DIR / "skills" / "deck-builder" / "scripts" / "presentation_director.py"
GENERATE_IMAGES_PATH: Path = ROOT_DIR / "skills" / "deck-builder" / "scripts" / "generate_images.py"
SAFE_AREA_PATH: Path = ROOT_DIR / "scripts" / "check_presentation_safe_area.py"


def load_director_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("presentation_director_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PD: ModuleType = load_director_module()


def load_script_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GI: ModuleType = load_script_module("generate_images_test", GENERATE_IMAGES_PATH)


BAD_HTML: str = """<!doctype html>
<html>
<head>
  <style>
    .reveal .slides section { width:1280px; height:720px; position:relative; }
    .cols, .cards { display:flex; gap:24px; }
  </style>
</head>
<body>
  <div class="cols stagger"><div>A</div><div>B</div></div>
</body>
</html>
"""


GOOD_HTML: str = """<!doctype html>
<html lang="en" data-preview-as="desktop">
<head>
  <meta charset="utf-8">
  <style>
    .notes { display: none; }
    .slide { width: 1280px; height: 720px; overflow: hidden; }
    .slide-safe { width: 1172px; height: 590px; overflow: hidden; }
  </style>
</head>
<body data-preview-as="desktop">
  <div class="deck">
    <section class="slide" data-title="One">
      <div class="slide-safe">
        <p>Ready</p>
        <span class="slide-number" data-current="1" data-total="1"></span>
      </div>
      <aside class="notes">Speaker notes</aside>
    </section>
  </div>
</body>
</html>
"""


def write_task(base_dir: Path, html_text: str, output_format: str = "html-revealjs") -> Path:
    task_dir: Path = base_dir / "Decks" / "bad-task"
    (task_dir / "v1").mkdir(parents=True)
    (task_dir / "brief-draft.json").write_text("{}", encoding="utf-8")
    brief: dict[str, object] = {
        "confirmed": True,
        "output_format": output_format,
        "confirmation_gate": {
            "method": "browser-form",
            "confirmed_by": "user-click",
            "token_verified": True,
        },
    }
    (task_dir / "brief-confirmed.json").write_text(json.dumps(brief), encoding="utf-8")
    (task_dir / "v1" / "final.html").write_text(html_text, encoding="utf-8")
    return task_dir


def command_args(base_dir: Path, command: str, **kwargs: object) -> Namespace:
    values: dict[str, object] = {
        "base_dir": str(base_dir),
        "task": "bad-task",
        "task_dir": None,
        "thread_id": None,
        "host": "127.0.0.1",
        "port": 0,
    }
    values.update(kwargs)
    values["command"] = command
    return Namespace(**values)


@contextmanager
def run_director_server(task_dir: Path) -> Iterator[tuple[str, int]]:
    handler_class: type[object] = type(
        "BoundDirectorHandler",
        (PD.DirectorHandler,),
        {"task_dir": task_dir},
    )
    server: ThreadingHTTPServer = ThreadingHTTPServer(("127.0.0.1", 0), handler_class)
    thread: threading.Thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.1},
        daemon=True,
    )
    thread.start()
    try:
        yield str(server.server_address[0]), int(server.server_address[1])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def post_form(base_url: str, path: str, data: dict[str, str], headers: dict[str, str] | None = None) -> bytes:
    body: bytes = urlencode(data).encode()
    request_headers: dict[str, str] = {"Content-Type": "application/x-www-form-urlencoded"}
    if headers:
        request_headers.update(headers)
    request = Request(
        base_url + path,
        data=body,
        method="POST",
        headers=request_headers,
    )
    return urlopen(request, timeout=2).read()


class HtmlStructuralWarningsTest(unittest.TestCase):
    def warnings_for(self, html_text: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path: Path = Path(tmp_dir) / "final.html"
            path.write_text(html_text, encoding="utf-8")
            return PD.html_structural_warnings(path)

    def assertHasWarning(self, html_text: str) -> None:
        self.assertTrue(self.warnings_for(html_text))

    def assertNoWarning(self, html_text: str) -> None:
        self.assertEqual([], self.warnings_for(html_text))

    def test_section_position_selector_variants_fail(self) -> None:
        self.assertHasWarning("<style>.reveal .slides section, .reveal .slides section.present { position:relative; }</style>")
        self.assertHasWarning("<style>.reveal .slides section.slide { position:relative; }</style>")
        self.assertHasWarning('<style>.reveal .slides section[data-state="x"] { position:relative; }</style>')

    def test_section_class_and_descendant_selectors_do_not_false_positive(self) -> None:
        self.assertNoWarning("<style>.section { position:relative; }</style>")
        self.assertNoWarning("<style>.reveal .slides section .child { position:relative; }</style>")

    def test_unapproved_stagger_patterns_fail(self) -> None:
        self.assertHasWarning('<style>.cols, .cards { display:flex; }</style><div class="cols stagger"></div>')
        self.assertHasWarning(
            '<style>.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); }</style>'
            '<div class="cards stagger"></div>'
        )
        self.assertHasWarning(
            '<style>.cards { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); }</style>'
            '<div class="cards stagger"></div>'
        )

    def test_stagger_ok_blocks_forbidden_names_and_vertical_stacks(self) -> None:
        # Explicitly forbidden content container names still blocked even with stagger-ok
        self.assertHasWarning('<div class="cols stagger stagger-ok"></div>')
        self.assertHasWarning('<div class="cmp stagger stagger-ok"></div>')
        self.assertHasWarning('<div class="steps stagger stagger-ok"></div>')
        self.assertHasWarning('<div class="timeline stagger stagger-ok"></div>')
        # Vertical stacks blocked regardless of name
        self.assertHasWarning('<style>.layout { display:flex; flex-direction:column; }</style><div class="layout stagger stagger-ok"></div>')
        self.assertHasWarning('<ul class="stagger stagger-ok"><li>A</li><li>B</li></ul>')

    def test_stagger_ok_generic_horizontal_row_passes(self) -> None:
        # Any non-forbidden, non-vertical container passes with stagger-ok (no magic class name required)
        self.assertNoWarning('<style>.icon-row { display:flex; }</style><div class="icon-row stagger stagger-ok"></div>')
        self.assertNoWarning(
            '<style>.layout { display:grid; grid-template-columns:repeat(3,1fr); }</style>'
            '<div class="layout stagger stagger-ok"></div>'
        )

    def test_decorative_stagger_ok_card_row_passes(self) -> None:
        self.assertNoWarning('<style>.feature-cards { display:flex; flex-direction:row; }</style><div class="feature-cards stagger stagger-ok"></div>')


class PreviewReviewGateTest(unittest.TestCase):
    def test_init_renders_pages_before_v1_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--base-dir",
                    tmp_dir,
                    "init",
                    "--task",
                    "init-check",
                    "--topic",
                    "Init check",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((Path(tmp_dir) / "Decks" / "init-check" / "style-review.html").exists())

    def test_render_open_preview_review_blocks_bad_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir: Path = Path(tmp_dir)
            write_task(base_dir, BAD_HTML)
            args: Namespace = command_args(base_dir, "render", open_page="preview-review")
            with patch.object(PD.webbrowser, "open", side_effect=AssertionError("browser should not open")):
                with self.assertRaises(SystemExit) as raised:
                    PD.command_render(args)
            self.assertEqual(2, raised.exception.code)

    def test_serve_open_preview_review_blocks_bad_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir: Path = Path(tmp_dir)
            write_task(base_dir, BAD_HTML)
            args: Namespace = command_args(base_dir, "serve", open_page="preview-review", no_open=False)
            with patch.object(PD.webbrowser, "open", side_effect=AssertionError("browser should not open")):
                with self.assertRaises(SystemExit) as raised:
                    PD.command_serve(args)
            self.assertEqual(2, raised.exception.code)

    def test_open_page_preview_review_blocks_bad_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir: Path = Path(tmp_dir)
            write_task(base_dir, BAD_HTML)
            args: Namespace = command_args(base_dir, "open-page", page="preview-review")
            with patch.object(PD.webbrowser, "open", side_effect=AssertionError("browser should not open")):
                with self.assertRaises(SystemExit) as raised:
                    PD.command_open_page(args)
            self.assertEqual(2, raised.exception.code)

    def test_http_preview_review_route_blocks_bad_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir: Path = Path(tmp_dir)
            task_dir: Path = write_task(base_dir, BAD_HTML)
            handler_class: type[object] = type(
                "BoundDirectorHandler",
                (PD.DirectorHandler,),
                {"task_dir": task_dir},
            )
            server: ThreadingHTTPServer = ThreadingHTTPServer(("127.0.0.1", 0), handler_class)
            thread: threading.Thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.1},
                daemon=True,
            )
            thread.start()
            host: str = str(server.server_address[0])
            port: int = int(server.server_address[1])
            try:
                with self.assertRaises(HTTPError) as raised:
                    urlopen(f"http://{host}:{port}/preview-review", timeout=2)
                error: HTTPError = raised.exception
                self.assertEqual(HTTPStatus.CONFLICT, error.code)
                try:
                    body: str = error.read().decode("utf-8")
                    self.assertIn("Preview-review gate failed", body)
                finally:
                    error.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_both_output_includes_html_in_preview_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir: Path = Path(tmp_dir)
            task_dir: Path = write_task(base_dir, BAD_HTML, output_format="both")
            self.assertTrue(PD.preview_review_gate_errors(task_dir))

    def test_both_output_requires_html_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir: Path = Path(tmp_dir)
            task_dir: Path = write_task(base_dir, GOOD_HTML, output_format="both")
            (task_dir / "v1" / "final.html").unlink()
            (task_dir / "v1" / "final.pptx").write_bytes(b"pptx")
            (task_dir / "v1" / "contact-sheet.png").write_bytes(b"png")
            self.assertFalse(PD.v1_preview_exists(task_dir, "both"))
            self.assertTrue(any("final.html" in error for error in PD.preview_review_gate_errors(task_dir)))

    def test_html_preview_form_marker_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir: Path = Path(tmp_dir)
            task_dir: Path = write_task(base_dir, GOOD_HTML.replace(' data-preview-as="desktop"', ""))
            errors: list[str] = PD.preview_review_gate_errors(task_dir)
            self.assertTrue(any("data-preview-as" in error for error in errors))

    def test_generation_guard_checks_generated_v2_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir: Path = Path(tmp_dir)
            task_dir: Path = write_task(base_dir, GOOD_HTML)
            v2_dir: Path = task_dir / "v2"
            v2_dir.mkdir()
            (v2_dir / "final.html").write_text(BAD_HTML, encoding="utf-8")
            errors: list[str] = PD.validate_generation_guard(task_dir)
            self.assertTrue(any(error.startswith("v2:") for error in errors))

    def test_finalize_promotes_requested_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir: Path = Path(tmp_dir)
            task_dir: Path = base_dir / "Decks" / "bad-task"
            draft_dir: Path = task_dir / "v2" / ".draft"
            draft_dir.mkdir(parents=True)
            (draft_dir / "final.html").write_text(GOOD_HTML, encoding="utf-8")
            args: Namespace = command_args(base_dir, "finalize", version="v2")
            with patch.object(PD.webbrowser, "open"):
                with patch.object(PD, "playwright_visual_qa", return_value=[]):
                    PD.cmd_finalize(args)
            self.assertTrue((task_dir / "v2" / "final.html").exists())
            self.assertFalse((task_dir / "v1" / "final.html").exists())

    def test_generation_guard_allows_missing_v1_before_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = Path(tmp_dir) / "Decks" / "pre-v1-task"
            (task_dir / "status").mkdir(parents=True)
            brief: dict[str, object] = {
                "confirmed": True,
                "output_format": "html-revealjs",
                "image_policy": "none",
                "image_generation_mode": "none",
                "confirmation_gate": {
                    "method": "browser-form",
                    "confirmed_by": "user-click",
                    "token_verified": True,
                },
            }
            (task_dir / "brief-confirmed.json").write_text(json.dumps(brief), encoding="utf-8")
            (task_dir / "status" / "confirmed.ready").write_text("ready\n", encoding="utf-8")
            (task_dir / "status" / "images-style.ready").write_text("ready\n", encoding="utf-8")
            self.assertEqual([], PD.validate_generation_guard(task_dir))


class OptionalFigmaReferenceTest(unittest.TestCase):
    def test_init_renders_optional_reference_page_without_default_stdout_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--base-dir",
                    tmp_dir,
                    "init",
                    "--task",
                    "figma-gate",
                    "--topic",
                    "教师课程介绍",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            task_dir: Path = Path(tmp_dir) / "Decks" / "figma-gate"
            self.assertTrue((task_dir / "figma-source.html").exists())
            self.assertNotIn("Figma source", result.stdout)
            intake_html: str = (task_dir / "intake.html").read_text(encoding="utf-8")
            self.assertIn("figma-source", intake_html)

    def test_default_intake_goes_to_visual_and_records_internal_design_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir: Path = Path(tmp_dir)
            args = command_args(
                base_dir,
                "init",
                task="default-flow",
                topic="给教师使用的 Presentation Director",
                source=[],
                ui_language="zh",
                conversation_text="教师 课程 课件",
                mode="new",
            )
            PD.command_init(args)
            task_dir: Path = base_dir / "Decks" / "default-flow"
            token: str = (task_dir / "status" / "confirm.token").read_text(encoding="utf-8").strip()
            with run_director_server(task_dir) as (host, port):
                base_url: str = f"http://{host}:{port}"
                intake_body: bytes = post_form(
                    base_url,
                    "/api/intake",
                    {
                        "director_token": token,
                        "topic": "给教师使用的 Presentation Director",
                        "deck_type": "knowledge-teaching",
                        "output_format": "html-revealjs",
                        "audience": "teachers-researchers",
                        "goal": "teaching",
                        "source_boundary": "provided-only",
                        "research_strategy": "provided-materials",
                        "content_language": "zh",
                        "output_constraints": "pages-8-10",
                        "logo_policy": "none",
                        "image_policy": "none",
                        "visual_freedom": "academic-editorial",
                        "reference_deck": "none",
                    },
                )
                html: str = intake_body.decode("utf-8")
                self.assertIn("选择第一版视觉方向", html)
                self.assertNotIn("选择 Figma-assisted", html)
            self.assertFalse((task_dir / "figma-source-packet.json").exists())
            selected: dict[str, object] = json.loads((task_dir / "intake-selection.json").read_text(encoding="utf-8"))
            design_source: dict[str, object] = selected["design_source"]  # type: ignore[assignment]
            self.assertEqual("internal", design_source["mode"])
            self.assertFalse(design_source["figma_required"])

    def test_optional_figma_reference_writes_packet_and_confirmed_design_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            args = command_args(
                base_dir,
                "init",
                task="reference-flow",
                topic="客户品牌介绍",
                source=[],
                ui_language="zh",
                conversation_text="客户 品牌 Figma",
                mode="new",
            )
            PD.command_init(args)
            task_dir = base_dir / "Decks" / "reference-flow"
            token: str = (task_dir / "status" / "confirm.token").read_text(encoding="utf-8").strip()
            with run_director_server(task_dir) as (host, port):
                base_url: str = f"http://{host}:{port}"
                reference_body: bytes = post_form(
                    base_url,
                    "/api/intake",
                    {
                        "director_token": token,
                        "next_step": "figma-source",
                        "topic": "客户品牌介绍",
                        "deck_type": "sales-product",
                        "output_format": "html-revealjs",
                        "audience": "clients-buyers",
                        "goal": "explain-value",
                        "source_boundary": "provided-only",
                        "research_strategy": "provided-materials",
                        "content_language": "zh",
                        "output_constraints": "pages-8-10",
                        "logo_policy": "provided-only",
                        "image_policy": "none",
                        "visual_freedom": "brand-safe",
                        "reference_deck": "none",
                    },
                )
                self.assertIn("可选：使用 Figma", reference_body.decode("utf-8"))
                visual_body: bytes = post_form(
                    base_url,
                    "/api/figma-source",
                    {
                        "director_token": token,
                        "figma_source_mode": "figma-url",
                        "figma_url": "https://www.figma.com/design/example/brand",
                        "figma_source_notes": "只吸收品牌色和组件气质，不照搬模板",
                    },
                )
                self.assertIn("外部设计参考", visual_body.decode("utf-8"))
                selected: dict[str, object] = json.loads((task_dir / "intake-selection.json").read_text(encoding="utf-8"))
                selections = selected["selections"] if isinstance(selected["selections"], dict) else {}
                figma_packet = selected["figma_source_packet"] if isinstance(selected["figma_source_packet"], dict) else {}
                candidate_key: str = PD.build_visual_candidates("客户品牌介绍", selections, figma_packet)[0].key
                post_form(
                    base_url,
                    "/api/visual-inspiration",
                    {
                        "director_token": token,
                        "visual_candidate": candidate_key,
                    },
                )
                post_form(
                    base_url,
                    "/api/confirm",
                    {
                        "director_token": token,
                        "confirm_token": token,
                    },
                )
            packet: dict[str, object] = json.loads((task_dir / "figma-source-packet.json").read_text(encoding="utf-8"))
            self.assertEqual("figma-url", packet["source_status"])
            self.assertFalse(packet["runtime_dependency"])
            self.assertIn("figma_source_packet", selected)
            design_source: dict[str, object] = selected["design_source"]  # type: ignore[assignment]
            self.assertEqual("figma-url", design_source["mode"])
            self.assertFalse(design_source["figma_required"])
            confirmed: dict[str, object] = json.loads((task_dir / "brief-confirmed.json").read_text(encoding="utf-8"))
            confirmed_design_source: dict[str, object] = confirmed["design_source"]  # type: ignore[assignment]
            self.assertEqual("figma-url", confirmed_design_source["mode"])


class SecurityRegressionTest(unittest.TestCase):
    def test_static_does_not_serve_confirmation_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = write_task(Path(tmp_dir), GOOD_HTML)
            PD.ensure_confirm_token(task_dir)
            with run_director_server(task_dir) as (host, port):
                with self.assertRaises(HTTPError) as raised:
                    urlopen(f"http://{host}:{port}/static/status/confirm.token", timeout=2)
                self.assertEqual(HTTPStatus.BAD_REQUEST, raised.exception.code)
                raised.exception.close()

    def test_static_rejects_symlink_escape_from_allowed_preview_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = write_task(Path(tmp_dir), GOOD_HTML)
            PD.ensure_confirm_token(task_dir)
            (task_dir / "v1" / "final.html").unlink()
            (task_dir / "v1" / "final.html").symlink_to(task_dir / "status" / "confirm.token")
            with run_director_server(task_dir) as (host, port):
                with self.assertRaises(HTTPError) as raised:
                    urlopen(f"http://{host}:{port}/static/v1/final.html", timeout=2)
                self.assertEqual(HTTPStatus.BAD_REQUEST, raised.exception.code)
                raised.exception.close()

    def test_static_html_is_served_with_api_blocking_csp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = write_task(Path(tmp_dir), GOOD_HTML)
            with run_director_server(task_dir) as (host, port):
                response = urlopen(f"http://{host}:{port}/static/v1/final.html", timeout=2)
                try:
                    csp: str = response.headers["Content-Security-Policy"]
                    self.assertIn("connect-src 'none'", csp)
                    self.assertIn("form-action 'none'", csp)
                    self.assertIn("frame-src 'none'", csp)
                finally:
                    response.close()

    def test_pakco_style_picker_is_served_without_static_preview_csp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = write_task(Path(tmp_dir), GOOD_HTML)
            with run_director_server(task_dir) as (host, port):
                response = urlopen(f"http://{host}:{port}/pakco-html/templates/style-picker.html", timeout=2)
                try:
                    body: str = response.read().decode("utf-8")
                    self.assertIn("pakco.html", body)
                    self.assertNotIn("Content-Security-Policy", response.headers)
                finally:
                    response.close()

    def test_final_selection_copies_html_deck_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = write_task(Path(tmp_dir), GOOD_HTML)
            version_assets: Path = task_dir / "v1" / "assets"
            version_assets.mkdir()
            (version_assets / "runtime.js").write_text("window.__pd_asset_test = true;", encoding="utf-8")
            payload: dict[str, object] = PD.finalize_selected_version(task_dir, "v1")
            self.assertEqual(str(task_dir / "final" / f"{task_dir.name}.html"), payload["final_html"])
            self.assertTrue((task_dir / "final" / "assets" / "runtime.js").exists())

    def test_preview_review_post_requires_workflow_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = write_task(Path(tmp_dir), GOOD_HTML)
            with run_director_server(task_dir) as (host, port):
                base_url: str = f"http://{host}:{port}"
                with self.assertRaises(HTTPError) as raised:
                    post_form(base_url, "/api/preview-review", {"base_version": "v1", "preview_action": "keep-final"})
                self.assertEqual(HTTPStatus.FORBIDDEN, raised.exception.code)
                raised.exception.close()
                self.assertFalse((task_dir / "preview-review.json").exists())

                token: str = PD.ensure_confirm_token(task_dir)
                post_form(
                    base_url,
                    "/api/preview-review",
                    {
                        "director_token": token,
                        "base_version": "v1",
                        "preview_action": "keep-final",
                    },
                )
                self.assertTrue((task_dir / "preview-review.json").exists())

    def test_post_rejects_spoofed_host_origin_pair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = write_task(Path(tmp_dir), GOOD_HTML)
            token: str = PD.ensure_confirm_token(task_dir)
            with run_director_server(task_dir) as (host, port):
                with self.assertRaises(HTTPError) as raised:
                    post_form(
                        f"http://{host}:{port}",
                        "/api/preview-review",
                        {
                            "director_token": token,
                            "base_version": "v1",
                            "preview_action": "style-review",
                        },
                        headers={
                            "Origin": "http://evil.example",
                            "Host": "evil.example",
                        },
                    )
                self.assertEqual(HTTPStatus.FORBIDDEN, raised.exception.code)
                raised.exception.close()

    def test_final_selection_rejects_version_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir: Path = Path(tmp_dir)
            task_dir: Path = write_task(base_dir, GOOD_HTML)
            outside: Path = base_dir / "outside-secret"
            outside.mkdir()
            (outside / "final.html").write_text("SECRET", encoding="utf-8")
            token: str = PD.ensure_confirm_token(task_dir)
            with run_director_server(task_dir) as (host, port):
                with self.assertRaises(HTTPError) as raised:
                    post_form(
                        f"http://{host}:{port}",
                        "/api/final-selection",
                        {
                            "director_token": token,
                            "selected_version": "../../outside-secret",
                            "action": "finalize",
                        },
                    )
                self.assertEqual(HTTPStatus.BAD_REQUEST, raised.exception.code)
                raised.exception.close()
            final_html: Path = task_dir / "final" / f"{task_dir.name}.html"
            self.assertFalse(final_html.exists())

    def test_image_asset_output_path_must_stay_under_assets_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = Path(tmp_dir) / "Decks" / "image-task"
            (task_dir / "assets" / "images").mkdir(parents=True)
            valid_path: Path = task_dir / "assets" / "images" / "cover.png"
            valid_path.write_bytes(b"png")
            record: dict[str, object] = PD.record_image_asset_attempt(
                task_dir,
                "cover",
                "prompt",
                "assets/images/cover.png",
                "success",
            )
            self.assertEqual("success", record["final_status"])
            with self.assertRaises(ValueError):
                PD.record_image_asset_attempt(
                    task_dir,
                    "escape",
                    "prompt",
                    str(Path(tmp_dir) / "escape.png"),
                    "success",
                )

    def test_generate_images_rejects_plan_output_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = Path(tmp_dir) / "Decks" / "image-task"
            (task_dir / "assets" / "images").mkdir(parents=True)
            self.assertEqual(
                (task_dir / "assets" / "images" / "cover.png").resolve(),
                GI.target_output_path(task_dir, {"id": "cover", "output_path": "assets/images/cover.png"}),
            )
            with self.assertRaises(ValueError):
                GI.target_output_path(task_dir, {"id": "cover", "output_path": str(Path(tmp_dir) / "escape.png")})

    def test_pakco_assets_served_as_fallback_from_version_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = write_task(Path(tmp_dir), GOOD_HTML)
            with run_director_server(task_dir) as (host, port):
                response = urlopen(f"http://{host}:{port}/static/v1/assets/runtime.js", timeout=2)
                try:
                    body: bytes = response.read()
                    self.assertGreater(len(body), 100)
                    self.assertNotIn("Content-Security-Policy", response.headers)
                finally:
                    response.close()

    def test_pakco_asset_fallback_blocks_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            task_dir: Path = write_task(Path(tmp_dir), GOOD_HTML)
            with run_director_server(task_dir) as (host, port):
                with self.assertRaises(HTTPError) as raised:
                    urlopen(f"http://{host}:{port}/static/v1/assets/../brief-confirmed.json", timeout=2)
                self.assertIn(raised.exception.code, {HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND})
                raised.exception.close()

    def test_safe_area_checker_fails_on_empty_layout_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = subprocess.run(
                [sys.executable, str(SAFE_AREA_PATH), "--layout", tmp_dir],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("No layout files found", result.stderr)


if __name__ == "__main__":
    unittest.main()
