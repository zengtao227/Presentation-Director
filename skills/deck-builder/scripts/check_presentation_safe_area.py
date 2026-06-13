#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


DEFAULT_SLIDE_SIZE: tuple[float, float] = (1280.0, 720.0)
DEFAULT_SAFE_ZONE: tuple[float, float, float, float] = (54.0, 70.0, 1172.0, 590.0)
DEFAULT_CHROME_PATTERN: str = (
    r"(background|grid|bleed|footer|kicker|page-marker|chrome|"
    r"accent|rail|wire|node|dot|track|rule)"
)


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h


@dataclass(frozen=True)
class Issue:
    severity: str
    layout_path: Path
    element_name: str
    message: str


def parse_box(value: str) -> Box:
    parts: list[float] = [float(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("Expected x,y,w,h")
    return Box(parts[0], parts[1], parts[2], parts[3])


def parse_slide_size(value: str) -> tuple[float, float]:
    match: re.Match[str] | None = re.match(r"^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$", value)
    if not match:
        raise argparse.ArgumentTypeError("Expected WIDTHxHEIGHT, for example 1280x720")
    return (float(match.group(1)), float(match.group(2)))


def collect_layout_paths(path_value: Path) -> list[Path]:
    if path_value.is_dir():
        return sorted(path_value.glob("*.layout.json"))
    return [path_value]


def as_box(value: Any) -> Box | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    coords: list[float] = []
    for item in value:
        if not isinstance(item, (int, float)):
            return None
        coords.append(float(item))
    return Box(coords[0], coords[1], coords[2], coords[3])


def contains(container: Box, child: Box, tolerance: float) -> bool:
    return (
        child.x >= container.x - tolerance
        and child.y >= container.y - tolerance
        and child.x2 <= container.x2 + tolerance
        and child.y2 <= container.y2 + tolerance
    )


def element_name(element: dict[str, Any]) -> str:
    raw_name: Any = element.get("name") or element.get("textPreview") or element.get("text") or element.get("kind")
    return str(raw_name or f"element-{element.get('order', '?')}")


def is_chrome_or_decorative(element: dict[str, Any], chrome_regex: re.Pattern[str]) -> bool:
    name: str = element_name(element).lower()
    if chrome_regex.search(name):
        return True
    if element.get("kind") == "shape" and not (element.get("textPreview") or element.get("text")):
        geometry: str = str(element.get("geometry") or "")
        width: float = float(element.get("bbox", [0, 0, 0, 0])[2])
        height: float = float(element.get("bbox", [0, 0, 0, 0])[3])
        return geometry == "rect" and (width <= 8 or height <= 8)
    return False


def is_essential_content(element: dict[str, Any], chrome_regex: re.Pattern[str]) -> bool:
    if is_chrome_or_decorative(element, chrome_regex):
        return False
    if element.get("textPreview") or element.get("text"):
        return True
    return str(element.get("kind") or "") in {"image", "table", "chart", "shape"}


def check_layout(
    layout_path: Path,
    slide_size: tuple[float, float],
    safe_zone: Box,
    chrome_regex: re.Pattern[str],
    tolerance: float,
) -> list[Issue]:
    data: dict[str, Any] = json.loads(layout_path.read_text(encoding="utf-8"))
    slide_box: Box = Box(0.0, 0.0, slide_size[0], slide_size[1])
    issues: list[Issue] = []
    elements: Iterable[dict[str, Any]] = data.get("elements", [])
    for element in elements:
        box: Box | None = as_box(element.get("bbox"))
        if box is None:
            continue
        name: str = element_name(element)
        if not contains(slide_box, box, tolerance):
            issues.append(
                Issue(
                    "error",
                    layout_path,
                    name,
                    f"outside slide frame: bbox=[{box.x:.1f},{box.y:.1f},{box.w:.1f},{box.h:.1f}]",
                )
            )
            continue
        if is_essential_content(element, chrome_regex) and not contains(safe_zone, box, tolerance):
            issues.append(
                Issue(
                    "error",
                    layout_path,
                    name,
                    f"outside content safe zone {safe_zone}: bbox=[{box.x:.1f},{box.y:.1f},{box.w:.1f},{box.h:.1f}]",
                )
            )
    return issues


def build_parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Check PPTX layout JSON for slide-frame and content-safe-area violations."
    )
    parser.add_argument("--layout", required=True, type=Path, help="Layout JSON file or directory of *.layout.json files.")
    parser.add_argument("--slide-size", default="1280x720", type=parse_slide_size, help="Slide size, default 1280x720.")
    parser.add_argument(
        "--safe-zone",
        default="54,70,1172,590",
        type=parse_box,
        help="Content safe area as x,y,w,h in slide pixels. Default: 54,70,1172,590.",
    )
    parser.add_argument(
        "--chrome-pattern",
        default=DEFAULT_CHROME_PATTERN,
        help="Regex for slide chrome/decorative element names exempt from content safe-zone checks.",
    )
    parser.add_argument("--tolerance", default=1.0, type=float, help="Pixel tolerance. Default 1.")
    parser.add_argument("--warn-only", action="store_true", help="Print issues but exit 0.")
    parser.add_argument("--allow-empty", action="store_true", help="Exit 0 when no layout files are found.")
    return parser


def main(argv: Sequence[str]) -> int:
    parser: argparse.ArgumentParser = build_parser()
    args: argparse.Namespace = parser.parse_args(argv)
    layout_paths: list[Path] = collect_layout_paths(args.layout)
    chrome_regex: re.Pattern[str] = re.compile(str(args.chrome_pattern), re.IGNORECASE)
    all_issues: list[Issue] = []
    for layout_path in layout_paths:
        all_issues.extend(check_layout(layout_path, args.slide_size, args.safe_zone, chrome_regex, args.tolerance))

    for issue in all_issues:
        print(f"[{issue.severity}] {issue.layout_path.name}: {issue.element_name}: {issue.message}")

    print(f"Checked {len(layout_paths)} layout file(s): {len(all_issues)} issue(s).")
    if not layout_paths:
        print(f"No layout files found for {args.layout}.", file=sys.stderr)
        return 0 if args.warn_only or args.allow_empty else 1
    if all_issues and not args.warn_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
