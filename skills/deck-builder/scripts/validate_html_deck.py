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


def validate(path: str) -> list[str]:
    errors: list[str] = []

    with open(path, "rb") as f:
        raw = f.read()

    # 1. Smart quote check (binary — catches what text-mode grep misses)
    left_smart = raw.count(b"\xe2\x80\x9c")
    right_smart = raw.count(b"\xe2\x80\x9d")
    if left_smart + right_smart > 0:
        errors.append(
            f"SMART QUOTES: {left_smart + right_smart} curly quote(s) found. "
            "HTML attributes must use ASCII straight quotes only. "
            "Run: python3 -c \"path='{path}'; open(path,'wb').write(open(path,'rb').read().replace(b'\\xe2\\x80\\x9c',b'\\\"').replace(b'\\xe2\\x80\\x9d',b'\\\"'))\""
        )

    content = raw.decode("utf-8", errors="replace")

    # 2. Slide count: binary section count must match data-total
    section_count = raw.count(b'<section class="slide"')
    total_match = re.search(r'data-total="(\d+)"', content)
    if total_match:
        declared_total = int(total_match.group(1))
        if section_count != declared_total:
            errors.append(
                f"SLIDE COUNT MISMATCH: file has {section_count} valid <section class=\"slide\"> "
                f"but data-total declares {declared_total}."
            )
    else:
        errors.append("MISSING data-total: no slide-number element with data-total found.")

    # 3. data-current sequence must be 1..N with no gaps
    currents = [int(m) for m in re.findall(r'data-current="(\d+)"', content)]
    if currents:
        expected = list(range(1, len(currents) + 1))
        if sorted(currents) != expected:
            errors.append(
                f"SEQUENCE GAP: data-current values are {sorted(currents)}, expected {expected}."
            )
    else:
        errors.append("MISSING data-current: no slide-number elements found.")

    # 4. .notes must be hidden
    if ".notes" not in content or "display: none" not in content:
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
