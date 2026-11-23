"""deck-spec v1: the per-slide content the host model writes and the PPTX generator consumes.

The host model fills this from the user's material after the direction has been confirmed.
Limits keep each layout readable on a 16:9 slide; they are not security controls.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

Text = Annotated[str, Field(min_length=1, max_length=120)]
Title = Annotated[str, Field(min_length=1, max_length=60)]
Notes = Annotated[str, Field(max_length=2000)]
HexColor = Annotated[str, Field(pattern=r"^#?[0-9A-Fa-f]{6}$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Theme(Strict):
    background: HexColor = "#f8fafc"
    text: HexColor = "#1e293b"
    accent: HexColor = "#0ea5e9"
    accent2: HexColor = "#10b981"
    font_face: Annotated[str, Field(min_length=1, max_length=60)] = "Microsoft YaHei"


class Column(Strict):
    heading: Title
    bullets: Annotated[list[Text], Field(min_length=1, max_length=5)]


class Series(Strict):
    name: Annotated[str, Field(min_length=1, max_length=40)]
    values: Annotated[list[float], Field(min_length=1, max_length=12)]


class Chart(Strict):
    type: Literal["bar", "line", "pie"]
    categories: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=20)]], Field(min_length=1, max_length=12)
    ]
    series: Annotated[list[Series], Field(min_length=1, max_length=4)]
    unit: Annotated[str, Field(max_length=12)] = ""

    @model_validator(mode="after")
    def shape_matches(self) -> Chart:
        for s in self.series:
            if len(s.values) != len(self.categories):
                raise ValueError(
                    f"series '{s.name}' has {len(s.values)} values "
                    f"but there are {len(self.categories)} categories"
                )
        if self.type == "pie" and len(self.series) != 1:
            raise ValueError("a pie chart takes exactly one series")
        return self


Cell = Annotated[str, Field(max_length=40)]


class Table(Strict):
    header: Annotated[list[Cell], Field(min_length=1, max_length=6)]
    rows: Annotated[list[list[Cell]], Field(min_length=1, max_length=8)]

    @model_validator(mode="after")
    def rows_match_header(self) -> Table:
        for i, row in enumerate(self.rows, start=1):
            if len(row) != len(self.header):
                raise ValueError(
                    f"table row {i} has {len(row)} cells but the header has {len(self.header)}"
                )
        return self


class SlideBase(Strict):
    notes: Notes = ""


class CoverSlide(SlideBase):
    layout: Literal["cover"]
    title: Title
    subtitle: Annotated[str, Field(max_length=120)] = ""
    footnote: Annotated[str, Field(max_length=60)] = ""


class BulletsSlide(SlideBase):
    layout: Literal["bullets"]
    title: Title
    bullets: Annotated[list[Text], Field(min_length=1, max_length=6)]


class TwoColumnSlide(SlideBase):
    layout: Literal["two_column"]
    title: Title
    left: Column
    right: Column


class ChartSlide(SlideBase):
    layout: Literal["chart"]
    title: Title
    chart: Chart
    takeaway: Annotated[str, Field(max_length=80)] = ""


class TableSlide(SlideBase):
    layout: Literal["table"]
    title: Title
    table: Table
    takeaway: Annotated[str, Field(max_length=80)] = ""


class ClosingSlide(SlideBase):
    layout: Literal["closing"]
    title: Title
    items: Annotated[list[Text], Field(min_length=1, max_length=5)]


Slide = Annotated[
    CoverSlide | BulletsSlide | TwoColumnSlide | ChartSlide | TableSlide | ClosingSlide,
    Field(discriminator="layout"),
]


class DeckSpec(Strict):
    spec_version: Literal["1"]
    title: Title
    language: Annotated[str, Field(min_length=2, max_length=16)] = "zh-CN"
    theme: Theme = Theme()
    slides: Annotated[list[Slide], Field(min_length=1, max_length=40)]

    @field_validator("slides")
    @classmethod
    def cover_only_first(cls, slides: list[object]) -> list[object]:
        for i, s in enumerate(slides):
            if i > 0 and isinstance(s, CoverSlide):
                raise ValueError(f"slide {i + 1}: a cover slide can only be the first slide")
        return slides


def load(path: Path) -> DeckSpec:
    return DeckSpec.model_validate_json(path.read_text(encoding="utf-8"))


def describe_errors(err: ValidationError) -> list[str]:
    lines: list[str] = []
    for e in err.errors():
        loc = ".".join(str(p) for p in e["loc"])
        lines.append(f"{loc}: {e['msg']}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="deck-spec v1 tools")
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="validate a deck-spec file and print the normalized JSON")
    v.add_argument("file", type=Path)
    s = sub.add_parser("schema", help="print the JSON Schema")
    s.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    if args.cmd == "schema":
        text = json.dumps(DeckSpec.model_json_schema(), ensure_ascii=False, indent=2) + "\n"
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    try:
        spec = load(args.file)
    except ValidationError as err:
        for line in describe_errors(err):
            print(line, file=sys.stderr)
        return 2
    sys.stdout.write(spec.model_dump_json(indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
