#!/usr/bin/env python3
"""
Validate an HTML deck before delivery.

Catches issues that grep and visual inspection miss:
- Smart/curly quotes in HTML attributes (invalid HTML, breaks browser parsing)
- Slide count mismatch between actual sections and data-total
- Gaps or duplicates in data-current sequence
- Visible .notes content (missing display:none)

Usage:
    python3 validate_html_deck.py <path-to-html>

Exit code 0 = pass, 1 = fail.
"""

import re
import sys
from pathlib import Path
from urllib.parse import unquote


def slide_section_count(content: str) -> int:
    return sum(
        1
        for _ in re.finditer(
            r"<section\b[^>]*\bclass\s*=\s*(['\"])(?=[^'\"]*\bslide\b)[^'\"]*\1",
            content,
            re.IGNORECASE,
        )
    )


def linked_css_text(path: str, content: str) -> str:
    html_path = Path(path)
    chunks: list[str] = []
    hrefs = re.findall(
        r"<link\b[^>]*\bhref\s*=\s*['\"]([^'\"]+\.css(?:\?[^'\"]*)?)['\"]",
        content,
        re.IGNORECASE,
    )
    for href in hrefs:
        clean_href = unquote(href.split("?", 1)[0])
        if re.match(r"^[a-z][a-z0-9+.-]*:", clean_href, re.IGNORECASE):
            continue
        css_path = (html_path.parent / clean_href).resolve()
        if not css_path.exists() or not css_path.is_file():
            continue
        chunks.append(css_path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def has_hidden_notes_rule(path: str, content: str) -> bool:
    css_text = content + "\n" + linked_css_text(path, content)
    return bool(re.search(r"\.notes\b[^{]*\{[^}]*display\s*:\s*none", css_text, re.IGNORECASE))


def validate(path: str) -> list[str]:
    errors: list[str] = []

    with open(path, "rb") as f:
        raw = f.read()

    content = raw.decode("utf-8", errors="replace")

    # 1. Curly quotes only break parsing inside tags; Chinese body text uses them legitimately.
    smart_in_tags = sum(
        tag.count("“") + tag.count("”") for tag in re.findall(r"<[^<>]*>", content)
    )
    if smart_in_tags > 0:
        errors.append(
            f"SMART QUOTES: {smart_in_tags} curly quote(s) found inside HTML tags. "
            "HTML attributes must use ASCII straight quotes only."
        )

    # 2. Slide count: any section whose class list contains slide must match data-total
    section_count = slide_section_count(content)
    total_match = re.search(r"data-total\s*=\s*['\"](\d+)['\"]", content)
    if total_match:
        declared_total = int(total_match.group(1))
        if section_count != declared_total:
            errors.append(
                f"SLIDE COUNT MISMATCH: file has {section_count} valid slide section(s) "
                f"but data-total declares {declared_total}."
            )
    else:
        errors.append("MISSING data-total: no slide-number element with data-total found.")

    # 3. data-current sequence must be 1..N with no gaps
    preview_marker = re.search(
        r"data-preview-as\s*=\s*['\"](mobile|desktop|both)['\"]",
        content,
        re.IGNORECASE,
    ) or re.search(
        r"name\s*=\s*['\"]presentation-preview['\"][^>]*content\s*=\s*['\"](mobile|desktop|both)['\"]",
        content,
        re.IGNORECASE,
    )
    if not preview_marker:
        errors.append("MISSING data-preview-as: declare mobile, desktop, or both on <html> or <body>.")

    currents = [int(m) for m in re.findall(r"data-current\s*=\s*['\"](\d+)['\"]", content)]
    if currents:
        expected = list(range(1, section_count + 1))
        if sorted(currents) != expected:
            errors.append(
                f"SEQUENCE GAP: data-current values are {sorted(currents)}, expected {expected}."
            )
    else:
        errors.append("MISSING data-current: no slide-number elements found.")

    # 4. .notes must be hidden
    if ".notes" not in content or not has_hidden_notes_rule(path, content):
        errors.append(
            "NOTES VISIBLE: .notes CSS rule with display:none not found. "
            "Speaker notes will render on slides."
        )

    return errors


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-html>")
        sys.exit(1)

    path = sys.argv[1]
    errors = validate(path)

    if errors:
        print(f"FAIL  {path}")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print(f"PASS  {path}")
        print("  ✓ No smart quotes")
        print("  ✓ Slide count matches data-total")
        print("  ✓ data-current sequence complete")
        print("  ✓ Speaker notes hidden")


if __name__ == "__main__":
    main()
