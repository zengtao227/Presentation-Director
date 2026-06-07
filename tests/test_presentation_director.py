from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from argparse import Namespace
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen


ROOT_DIR: Path = Path(__file__).resolve().parents[1]
MODULE_PATH: Path = ROOT_DIR / "skills" / "deck-builder" / "scripts" / "presentation_director.py"


def load_director_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("presentation_director_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PD: ModuleType = load_director_module()


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


if __name__ == "__main__":
    unittest.main()
