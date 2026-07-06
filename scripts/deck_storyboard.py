#!/usr/bin/env python3
"""
deck_storyboard.py — Generate a visual storyboard HTML from deck.md before generation.

Borrowed from Codex Product Design plugin insight: review section-by-section
structure before committing to full render. Catches layout mismatch, claim
weakness, or missing proof objects before generation wastes time.

Usage:
    python3 scripts/deck_storyboard.py --deck Decks/<task>/deck.md
    python3 scripts/deck_storyboard.py --deck deck.md --out storyboard.html --open
"""

from __future__ import annotations

import argparse
import html as _html
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ── Layout badge colours ─────────────────────────────────────────────────────

LAYOUT_COLOURS: dict[str, str] = {
    "cover":         "#3b6cff",
    "cover-hero":    "#3b6cff",
    "hero":          "#3b6cff",
    "title":         "#3b6cff",
    "claim":         "#7a5cff",
    "claim-bullets": "#7a5cff",
    "bullets":       "#7a5cff",
    "stat":          "#ff5c8a",
    "stat-highlight":"#ff5c8a",
    "kpi":           "#ff5c8a",
    "kpi-grid":      "#ff5c8a",
    "chart":         "#1aaf6c",
    "chart-bar":     "#1aaf6c",
    "chart-line":    "#1aaf6c",
    "chart-pie":     "#1aaf6c",
    "table":         "#1aaf6c",
    "evidence":      "#1aaf6c",
    "quote":         "#f5a524",
    "big-quote":     "#f5a524",
    "two-column":    "#55596a",
    "comparison":    "#55596a",
    "image":         "#8a8f9e",
    "image-hero":    "#8a8f9e",
    "flow":          "#0ea5e9",
    "process":       "#0ea5e9",
    "timeline":      "#0ea5e9",
    "cta":           "#e0445a",
    "cta-close":     "#e0445a",
    "section":       "#111216",
    "divider":       "#111216",
    "appendix":      "#8a8f9e",
}

PROOF_ICONS: dict[str, str] = {
    "chart":    "📊",
    "table":    "📋",
    "diagram":  "🗂",
    "quote":    "💬",
    "image":    "🖼",
    "number":   "🔢",
    "stat":     "🔢",
    "case":     "📌",
    "code":     "💻",
    "video":    "🎬",
    "map":      "🗺",
}


# ── Slide dataclass ───────────────────────────────────────────────────────────

@dataclass
class Slide:
    index: int
    title: str = ""
    claim: str = ""
    layout: str = ""
    proof: str = ""
    source: str = ""
    content_preview: str = ""
    raw_lines: list[str] = field(default_factory=list)

    def layout_colour(self) -> str:
        key = self.layout.lower().strip()
        for k, v in LAYOUT_COLOURS.items():
            if key.startswith(k):
                return v
        return "#8a8f9e"

    def proof_icon(self) -> str:
        p = self.proof.lower()
        for k, v in PROOF_ICONS.items():
            if k in p:
                return v
        return "📄"

    def display_title(self) -> str:
        return self.title or self.claim or f"Slide {self.index}"

    def display_layout(self) -> str:
        return self.layout or "—"

    def display_proof(self) -> str:
        return self.proof or "—"


# ── Parser ────────────────────────────────────────────────────────────────────

def _extract_field(lines: list[str], *keys: str) -> str:
    """Extract **Key:** value from a list of lines."""
    pattern = re.compile(
        r"^\s*\*{0,2}(?:" + "|".join(re.escape(k) for k in keys) + r")\*{0,2}\s*:?\s*(.+)",
        re.IGNORECASE,
    )
    for line in lines:
        m = pattern.match(line)
        if m:
            return m.group(1).strip().strip("*_`")
    return ""


def _strip_markdown(text: str) -> str:
    """Remove common markdown syntax for plain text preview."""
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+>|]\s*", "", text, flags=re.MULTILINE)
    return " ".join(text.split())


def parse_deck_md(path: Path) -> tuple[str, list[Slide]]:
    """
    Parse deck.md into (thesis, slides).
    Supports three formats:
    - Marp: slides separated by '---'
    - Structured: '## Slide N: Title' headers
    - Generic: any '## ' level-2 headers
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Extract thesis (look for a line after "# Thesis" or "## Thesis" or a bolded sentence)
    thesis = ""
    for i, line in enumerate(lines):
        if re.match(r"^#{1,3}\s+thesis", line, re.IGNORECASE):
            for j in range(i + 1, min(i + 5, len(lines))):
                stripped = lines[j].strip().strip("*_>")
                if stripped:
                    thesis = stripped
                    break
            break

    # Skip front-matter YAML
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start = i + 1
                break

    body_lines = lines[start:]

    # Try to detect format
    marp_sep = sum(1 for ln in body_lines if ln.strip() == "---")
    structured = sum(1 for ln in body_lines if re.match(r"^#{1,3}\s+slide\s+\d+", ln, re.IGNORECASE))

    slides: list[Slide] = []

    if structured > 0:
        slides = _parse_structured(body_lines)
    elif marp_sep > 0:
        slides = _parse_marp(body_lines)
    else:
        slides = _parse_generic(body_lines)

    return thesis, slides


def _parse_marp(lines: list[str]) -> list[Slide]:
    """Parse Marp-style deck (--- separators)."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip() == "---":
            if current:
                blocks.append(current)
            current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)

    slides = []
    for i, block in enumerate(blocks, 1):
        s = Slide(index=i, raw_lines=block)
        # Title: first H1 or H2 or H3
        for line in block:
            m = re.match(r"^#{1,3}\s+(.+)", line)
            if m:
                s.title = m.group(1).strip()
                break
        s.claim  = _extract_field(block, "claim", "Claim", "CLAIM")
        s.layout = _extract_field(block, "layout", "Layout", "LAYOUT")
        s.proof  = _extract_field(block, "proof", "Proof", "Proof Object", "PROOF")
        s.source = _extract_field(block, "source", "Source", "SOURCE")
        # Content preview: non-field, non-header lines
        content_lines = [
            ln for ln in block
            if not re.match(r"^#{1,6}\s", ln)
            and not re.match(r"^\*{0,2}(claim|layout|proof|source)\*{0,2}\s*:", ln, re.IGNORECASE)
            and ln.strip()
        ]
        s.content_preview = _strip_markdown(" ".join(content_lines))[:160]
        slides.append(s)
    return slides


def _parse_structured(lines: list[str]) -> list[Slide]:
    """Parse structured format with '## Slide N: Title' headers."""
    slide_re = re.compile(r"^#{1,3}\s+(?:slide\s+)?(\d+)[.:\s]+(.+)", re.IGNORECASE)
    blocks: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        m = slide_re.match(line)
        if m:
            if current_lines or current_title:
                blocks.append((current_title, current_lines))
            current_title = m.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines or current_title:
        blocks.append((current_title, current_lines))

    slides = []
    for i, (title, block) in enumerate(blocks, 1):
        s = Slide(index=i, title=title, raw_lines=block)
        s.claim  = _extract_field(block, "claim", "Claim", "CLAIM") or title
        s.layout = _extract_field(block, "layout", "Layout", "LAYOUT")
        s.proof  = _extract_field(block, "proof", "Proof", "Proof Object", "PROOF")
        s.source = _extract_field(block, "source", "Source", "SOURCE")
        content_lines = [
            ln for ln in block
            if not re.match(r"^\*{0,2}(claim|layout|proof|source)\*{0,2}\s*:", ln, re.IGNORECASE)
            and ln.strip()
        ]
        s.content_preview = _strip_markdown(" ".join(content_lines))[:160]
        slides.append(s)
    return slides


def _parse_generic(lines: list[str]) -> list[Slide]:
    """Fall back to splitting on any H2/H3 headers."""
    blocks: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        m = re.match(r"^#{2,3}\s+(.+)", line)
        if m:
            if current_lines or current_title:
                blocks.append((current_title, current_lines))
            current_title = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines or current_title:
        blocks.append((current_title, current_lines))

    slides = []
    for i, (title, block) in enumerate(blocks, 1):
        if title.lower() in ("thesis", "audience", "omissions", "appendix", "notes"):
            continue
        s = Slide(index=i, title=title, raw_lines=block)
        s.claim  = _extract_field(block, "claim", "Claim") or title
        s.layout = _extract_field(block, "layout", "Layout")
        s.proof  = _extract_field(block, "proof", "Proof", "Proof Object")
        s.source = _extract_field(block, "source", "Source")
        content_lines = [ln for ln in block if ln.strip()]
        s.content_preview = _strip_markdown(" ".join(content_lines))[:160]
        slides.append(s)

    # Re-number after filtering
    for i, s in enumerate(slides, 1):
        s.index = i
    return slides


# ── HTML renderer ─────────────────────────────────────────────────────────────

def render_html(thesis: str, slides: list[Slide], deck_path: Path) -> str:
    e = _html.escape

    def badge(text: str, colour: str) -> str:
        return (
            f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;'
            f'font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;'
            f'background:{colour}22;color:{colour};border:1px solid {colour}55">'
            f"{e(text)}</span>"
        )

    card_html = ""
    for s in slides:
        colour = s.layout_colour()
        icon   = s.proof_icon()
        layout_badge = badge(s.display_layout(), colour) if s.layout else badge("layout ?", "#8a8f9e")
        source_line  = f'<div class="source">Source: {e(s.source)}</div>' if s.source else ""
        preview_text = e(s.content_preview) + "…" if s.content_preview and len(s.content_preview) >= 158 else e(s.content_preview)

        card_html += f"""
<div class="card" style="--accent:{colour}">
  <div class="card-num">{s.index:02d}</div>
  <div class="card-title">{e(s.display_title())}</div>
  <div class="card-meta">
    {layout_badge}
    <span class="proof-icon" title="Proof object">{icon} {e(s.display_proof())}</span>
  </div>
  <div class="card-preview">{preview_text}</div>
  {source_line}
</div>"""

    thesis_block = (
        f'<div class="thesis"><strong>Thesis:</strong> {e(thesis)}</div>'
        if thesis else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Storyboard — {e(deck_path.name)}</title>
<style>
  :root{{--bg:#0f1117;--surface:#181c24;--border:rgba(255,255,255,.08);--text-1:#e8eaf0;--text-2:#8a8f9e;--text-3:#55596a;--accent:#3b6cff;--shadow:rgba(0,0,0,.3)}}
  :root.light{{--bg:#ffffff;--surface:#f7f7f8;--border:rgba(0,0,0,.08);--text-1:#111216;--text-2:#55596a;--text-3:#8a8f9e;--shadow:rgba(18,24,40,.1)}}
  @media(prefers-color-scheme:light){{:root:not(.dark){{--bg:#ffffff;--surface:#f7f7f8;--border:rgba(0,0,0,.08);--text-1:#111216;--text-2:#55596a;--text-3:#8a8f9e;--shadow:rgba(18,24,40,.1)}}}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text-1);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;padding:40px 32px;min-height:100vh;transition:background .2s,color .2s}}
  header{{max-width:1200px;margin:0 auto 32px;border-bottom:1px solid var(--border);padding-bottom:24px}}
  .header-row{{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}}
  h1{{font-size:20px;font-weight:700;color:var(--text-1);margin-bottom:8px}}
  .deck-path{{font-size:12px;color:var(--text-3);font-family:monospace}}
  .slide-count{{display:inline-block;margin-top:8px;font-size:13px;color:var(--text-2)}}
  .thesis{{margin-top:16px;padding:12px 16px;background:rgba(59,108,255,.1);border-left:3px solid #3b6cff;border-radius:4px;font-size:14px;line-height:1.6;color:var(--text-1)}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px;max-width:1200px;margin:0 auto}}
  .card{{background:var(--surface);border:1px solid var(--border);border-top:3px solid var(--accent);border-radius:12px;padding:20px;position:relative;transition:transform .2s,box-shadow .2s}}
  .card:hover{{transform:translateY(-2px);box-shadow:0 8px 24px var(--shadow)}}
  .card-num{{position:absolute;top:16px;right:16px;font-size:11px;font-weight:700;color:var(--text-3);font-family:monospace}}
  .card-title{{font-size:15px;font-weight:600;line-height:1.4;margin-bottom:12px;color:var(--text-1);padding-right:32px}}
  .card-meta{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}}
  .proof-icon{{font-size:12px;color:var(--text-2)}}
  .card-preview{{font-size:13px;color:var(--text-2);line-height:1.55;border-top:1px solid var(--border);padding-top:10px;margin-top:4px}}
  .source{{font-size:11px;color:var(--text-3);margin-top:8px;font-family:monospace}}
  footer{{max-width:1200px;margin:40px auto 0;font-size:12px;color:var(--text-3);border-top:1px solid var(--border);padding-top:16px}}
  .legend{{display:flex;flex-wrap:wrap;gap:12px;margin-top:12px}}
  .legend-item{{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-2)}}
  .legend-dot{{width:10px;height:10px;border-radius:50%}}
  #theme-btn{{cursor:pointer;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid var(--border);background:var(--surface);color:var(--text-2);white-space:nowrap;transition:all .2s;flex-shrink:0}}
  #theme-btn:hover{{border-color:var(--accent);color:var(--accent)}}
</style>
<script>
  (function(){{
    var saved = localStorage.getItem('sb-theme');
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var isDark = saved ? saved === 'dark' : prefersDark;
    if (isDark) document.documentElement.classList.add('dark');
    else document.documentElement.classList.add('light');
  }})();
</script>
</head>
<body>
<header>
  <div class="header-row">
    <div>
      <h1>Storyboard Review</h1>
      <div class="deck-path">{e(str(deck_path))}</div>
      <div class="slide-count">{len(slides)} slides planned</div>
    </div>
    <button id="theme-btn" onclick="(function(){{var r=document.documentElement;var dark=r.classList.toggle('dark');r.classList.toggle('light',!dark);localStorage.setItem('sb-theme',dark?'dark':'light');document.getElementById('theme-btn').textContent=dark?'☀ Light':'☾ Dark';}})()">☾ Dark</button>
  </div>
  {thesis_block}
</header>
<script>
  document.addEventListener('DOMContentLoaded',function(){{
    var isDark=document.documentElement.classList.contains('dark');
    document.getElementById('theme-btn').textContent=isDark?'☀ Light':'☾ Dark';
  }});
</script>
<div class="grid">{card_html}
</div>
<footer>
  <div>Review layout spread, claim strength, and proof object type before committing to full render.</div>
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#3b6cff"></div>Cover / Title</div>
    <div class="legend-item"><div class="legend-dot" style="background:#7a5cff"></div>Claim</div>
    <div class="legend-item"><div class="legend-dot" style="background:#ff5c8a"></div>Stat / KPI</div>
    <div class="legend-item"><div class="legend-dot" style="background:#1aaf6c"></div>Evidence / Chart</div>
    <div class="legend-item"><div class="legend-dot" style="background:#f5a524"></div>Quote</div>
    <div class="legend-item"><div class="legend-dot" style="background:#0ea5e9"></div>Flow / Process</div>
    <div class="legend-item"><div class="legend-dot" style="background:#e0445a"></div>CTA</div>
    <div class="legend-item"><div class="legend-dot" style="background:#111216"></div>Section divider</div>
  </div>
  <div style="margin-top:8px">Generated by <code>scripts/deck_storyboard.py</code> · Presentation Director</div>
</footer>
</body>
</html>"""


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a visual storyboard HTML from deck.md before full generation.",
    )
    parser.add_argument("--deck", required=True, help="Path to deck.md")
    parser.add_argument("--out", default="", help="Output HTML path. Defaults to <deck-dir>/storyboard.html")
    parser.add_argument("--open", action="store_true", help="Open the storyboard in the default browser after generation.")
    parser.add_argument("--json", action="store_true", help="Also write storyboard.json alongside the HTML.")
    args = parser.parse_args()

    deck_path = Path(args.deck).resolve()
    if not deck_path.exists():
        print(f"ERROR: deck.md not found: {deck_path}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out).resolve() if args.out else deck_path.parent / "storyboard.html"

    thesis, slides = parse_deck_md(deck_path)

    if not slides:
        print("WARNING: No slides parsed. Check deck.md format (Marp ---, ## Slide N:, or ## headings).")

    html = render_html(thesis, slides, deck_path)
    out_path.write_text(html, encoding="utf-8")
    print(f"Storyboard written: {out_path}  ({len(slides)} slides)")

    if args.json:
        json_path = out_path.with_suffix(".json")
        data = {
            "thesis": thesis,
            "slide_count": len(slides),
            "slides": [
                {
                    "index": s.index,
                    "title": s.title,
                    "claim": s.claim,
                    "layout": s.layout,
                    "proof": s.proof,
                    "source": s.source,
                    "content_preview": s.content_preview,
                }
                for s in slides
            ],
        }
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON written:       {json_path}")

    if args.open:
        try:
            subprocess.Popen(["open", str(out_path)])
        except FileNotFoundError:
            subprocess.Popen(["xdg-open", str(out_path)])


if __name__ == "__main__":
    main()
