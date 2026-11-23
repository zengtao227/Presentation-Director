from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from engine.deck_spec import DeckSpec, main

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "engine" / "samples" / "weekly-report.json"
GENERATOR = ROOT / "engine" / "generator" / "generate.mjs"


def sample() -> dict:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_sample_is_valid() -> None:
    spec = DeckSpec.model_validate(sample())
    assert [s.layout for s in spec.slides] == [
        "cover",
        "bullets",
        "chart",
        "table",
        "two_column",
        "closing",
    ]
    assert spec.theme.font_face == "Microsoft YaHei"


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda d: d["slides"][2]["chart"]["series"][0]["values"].pop(), "values but there are"),
        (lambda d: d["slides"][3]["table"]["rows"][0].pop(), "cells but the header has"),
        (
            lambda d: d["slides"].append(copy.deepcopy(d["slides"][0])),
            "cover slide can only be the first",
        ),
        (lambda d: d["slides"][2]["chart"].update(type="pie"), "exactly one series"),
        (lambda d: d["slides"][1].update(colour="red"), "Extra inputs are not permitted"),
        (
            lambda d: d["slides"][1].update(layout="timeline"),
            "does not match any of the expected tags",
        ),
    ],
)
def test_invalid_specs_are_rejected(mutate, message: str) -> None:
    data = sample()
    mutate(data)
    with pytest.raises(ValidationError, match=message):
        DeckSpec.model_validate(data)


def test_cli_reports_readable_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data = sample()
    data["slides"][3]["table"]["rows"][0].pop()
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert main(["validate", str(bad)]) == 2
    assert "slides.3.table" in capsys.readouterr().err


def test_checked_in_schema_matches_model() -> None:
    checked_in = json.loads(
        (ROOT / "schemas" / "deck-spec-v1.schema.json").read_text(encoding="utf-8")
    )
    assert checked_in == DeckSpec.model_json_schema()


@pytest.mark.skipif(
    shutil.which("node") is None or not (GENERATOR.parent / "node_modules").exists(),
    reason="node or generator deps missing",
)
def test_generator_builds_editable_native_objects(tmp_path: Path) -> None:
    spec = tmp_path / "spec.json"
    spec.write_text(DeckSpec.model_validate(sample()).model_dump_json(), encoding="utf-8")
    out = tmp_path / "deck.pptx"
    subprocess.run(["node", str(GENERATOR), str(spec), str(out)], check=True, capture_output=True)
    z = zipfile.ZipFile(out)
    names = z.namelist()
    assert sum(1 for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)) == 6
    assert any(re.fullmatch(r"ppt/embeddings/.+\.xlsx", n) for n in names), (
        "chart must carry an editable workbook"
    )
    chart = z.read("ppt/charts/chart1.xml").decode()
    assert "<c:barChart>" in chart and "支付" in chart
    assert "<a:tbl>" in z.read("ppt/slides/slide4.xml").decode()
    assert sum(1 for n in names if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n)) == 6
    assert "当场给出意见" in z.read("ppt/notesSlides/notesSlide6.xml").decode()


@pytest.mark.skipif(
    shutil.which("node") is None or not (GENERATOR.parent / "node_modules").exists(),
    reason="node or generator deps missing",
)
def test_chart_workbook_is_one_excel_and_powerpoint_accept(tmp_path: Path) -> None:
    """Regression: PowerPoint's Edit Data must stay linked to the chart (no Excel repair)."""
    import io

    spec = tmp_path / "spec.json"
    spec.write_text(DeckSpec.model_validate(sample()).model_dump_json(), encoding="utf-8")
    out = tmp_path / "deck.pptx"
    subprocess.run(["node", str(GENERATOR), str(spec), str(out)], check=True, capture_output=True)
    z = zipfile.ZipFile(out)
    chart = z.read("ppt/charts/chart1.xml").decode()
    assert "multiLvlStrRef" not in chart and "<c:strRef><c:f>Sheet1!$A$2:$A$6</c:f>" in chart
    book_name = next(n for n in z.namelist() if re.fullmatch(r"ppt/embeddings/[^/]+\.xlsx", n))
    book = zipfile.ZipFile(io.BytesIO(z.read(book_name)))
    table = book.read("xl/tables/table1.xml").decode()
    assert 'ref="A1:C6"' in table and "Column1" not in table and 'name="分类"' in table
    assert "<tableParts" in book.read("xl/worksheets/sheet1.xml").decode()
    assert "<cellXfs" in book.read("xl/styles.xml").decode()
    assert "<t>分类</t>" in book.read("xl/sharedStrings.xml").decode()
