"""Build a self-contained HTML deck from deck-spec v1 using the bundled pakco-html theme and runtime.

Everything (base CSS, theme, runtime, charts as inline SVG) is inlined into one file so the deck opens
offline by double-click and can be sent as a single attachment.
"""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path

from engine.deck_spec import (
    BulletsSlide,
    Chart,
    ChartSlide,
    ClosingSlide,
    CoverSlide,
    DeckSpec,
    TableSlide,
    TwoColumnSlide,
)

PAKCO_ASSETS = (
    Path(__file__).resolve().parent.parent / "skills" / "html-deck" / "pakco-html" / "assets"
)
DEFAULT_THEME = "corporate-clean"
SERIES_COLORS = ("var(--accent)", "var(--accent-2)", "var(--accent-3)", "var(--text-3)")

# Layout additions for the engine's six layouts; colours come from the pakco theme variables.
ENGINE_CSS = """
:root{--font-sans:'Inter','Noto Sans SC','Microsoft YaHei','PingFang SC',sans-serif;
  --font-display:var(--font-sans)}
.slide{justify-content:flex-start;padding:64px 88px 80px}
.slide.pd-cover{justify-content:center}
.pd-cover .h1{font-size:72px;line-height:1.15;margin:0 0 20px}
.pd-cover .lede{font-size:30px;max-width:none}
.pd-cover .pd-foot{margin-top:48px;color:var(--text-3);font-size:18px}
.pd-title{font-size:48px;line-height:1.25;margin:0 0 8px;font-weight:700}
.pd-rule{width:64px;height:4px;background:var(--accent);border-radius:2px;margin:0 0 32px}
.pd-list{margin:0;padding-left:1.2em;font-size:32px;line-height:1.6}
.pd-list li{margin:0 0 20px}
.pd-list li::marker{color:var(--accent)}
.card .pd-list{font-size:26px}
.card h4{font-size:30px;margin:0 0 16px;color:var(--accent)}
.pd-two .card:nth-child(2) h4{color:var(--accent-2)}
.pd-chart svg{width:100%;height:auto;max-height:600px;overflow:visible}
.pd-chart text{fill:var(--text-2);font-family:var(--font-sans)}
.pd-table{width:100%;border-collapse:collapse;font-size:24px}
.pd-table th{background:var(--accent);color:var(--bg);text-align:left;padding:16px 18px;font-weight:600}
.pd-table td{padding:16px 18px;border-bottom:1px solid var(--border)}
.pd-table tr:nth-child(even) td{background:var(--surface-2)}
.pd-takeaway{margin-top:24px;padding:16px 22px;border-left:6px solid var(--accent);
  background:var(--surface-2);font-size:26px;font-weight:600;border-radius:0 var(--radius-sm) var(--radius-sm) 0}
.pd-steps{list-style:none;margin:8px 0 0;padding:0;counter-reset:pd}
.pd-steps li{counter-increment:pd;display:flex;align-items:center;gap:28px;font-size:36px;margin:0 0 36px}
.pd-steps li::before{content:counter(pd);flex:0 0 56px;height:56px;border-radius:50%;background:var(--accent);
  color:var(--bg);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:26px}
@page{size:1600px 900px;margin:0}
@media print{#pd-tip{display:none}html,body{width:1600px}.deck{height:auto;overflow:visible}
  .slide{width:1600px;height:900px!important}.notes{display:none!important}}
body.pd-check .deck{height:auto;overflow:visible}
body.pd-check .slide{position:relative;opacity:1;transform:none;width:1600px;height:900px}
"""

# Measures each slide at 1600x900 when opened with ?pd-check; the result is written into the DOM
# so a headless browser's --dump-dom can read it without any driver library.
CHECK_JS = """
(function(){
  if(!/[?&]pd-check/.test(location.search))return;
  document.body.classList.add('pd-check');
  var out=[];
  document.querySelectorAll('.deck > .slide').forEach(function(s,i){
    var box=s.getBoundingClientRect(),problems=[];
    s.querySelectorAll('*').forEach(function(el){
      if(el.closest('.notes'))return;
      var r=el.getBoundingClientRect();
      if(r.width===0||r.height===0)return;
      if(r.bottom>box.bottom+1||r.right>box.right+1){
        var t=(el.textContent||el.tagName).trim().slice(0,20);
        if(problems.indexOf(t)<0)problems.push(t);
      }
    });
    out.push({slide:i+1,overflow:problems.slice(0,3)});
  });
  document.body.setAttribute('data-pd-check',JSON.stringify(out));
})();
"""


# T cycles through every bundled pakco theme inside the single file (pakco's own T loads theme files
# from disk, which a self-contained deck does not have).
THEME_JS = """
(function(){
  var themes=__THEMES__,names=Object.keys(themes),el=document.getElementById('theme');
  var cur=names.indexOf(document.documentElement.getAttribute('data-theme'));
  var tip=document.createElement('div');tip.id='pd-tip';
  tip.style.cssText='position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:99;padding:8px 16px;'+
    'border-radius:8px;background:rgba(0,0,0,.72);color:#fff;font:14px sans-serif;opacity:0;transition:opacity .3s;pointer-events:none';
  document.body.appendChild(tip);
  document.addEventListener('keydown',function(e){
    if((e.key!=='t'&&e.key!=='T')||e.metaKey||e.ctrlKey||e.altKey)return;
    if(/INPUT|TEXTAREA|SELECT/.test((e.target&&e.target.tagName)||''))return;
    cur=(cur+1)%names.length;el.textContent=themes[names[cur]];
    document.documentElement.setAttribute('data-theme',names[cur]);
    tip.textContent='主题：'+names[cur]+'（'+(cur+1)+'/'+names.length+'）';tip.style.opacity=1;
    clearTimeout(tip._t);tip._t=setTimeout(function(){tip.style.opacity=0},1400);
  });
})();
"""


def _themes_json() -> str:
    themes = {
        p.stem: p.read_text(encoding="utf-8")
        for p in sorted((PAKCO_ASSETS / "themes").glob("*.css"))
    }
    # Keep "</style>" or "</script>" inside CSS from closing the surrounding script element.
    return json.dumps(themes, ensure_ascii=False).replace("</", "<\\/")


def _asset(relative: str) -> str:
    return (PAKCO_ASSETS / relative).read_text(encoding="utf-8")


def available_theme(key: str | None) -> str:
    if key and (PAKCO_ASSETS / "themes" / f"{key}.css").is_file():
        return key
    return DEFAULT_THEME


def _nice_max(value: float) -> float:
    if value <= 0:
        return 1.0
    exp = 10 ** math.floor(math.log10(value))
    for step in (1, 2, 2.5, 5, 10):
        if value <= step * exp:
            return step * exp
    return 10 * exp


def _fmt(v: float, unit: str) -> str:
    text = f"{v:g}"
    return f"{text}{escape(unit)}"


def _legend(series_names: list[str], x: float, y: float) -> str:
    parts = []
    for i, name in enumerate(series_names):
        cx = x + i * 220
        parts.append(
            f'<rect x="{cx}" y="{y - 14}" width="16" height="16" rx="3" style="fill:{SERIES_COLORS[i % 4]}"/>'
            f'<text x="{cx + 24}" y="{y}" font-size="20">{escape(name)}</text>'
        )
    return "".join(parts)


def chart_svg(chart: Chart) -> str:
    w, h = 1400, 560
    if chart.type == "pie":
        return _pie_svg(chart, w, h)
    left, right, top, bottom = 80, 20, 30, 110
    plot_w, plot_h = w - left - right, h - top - bottom
    top_value = _nice_max(max(max(s.values) for s in chart.series))
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="chart">']
    for k in range(6):
        val = top_value * k / 5
        y = top + plot_h - plot_h * k / 5
        parts.append(
            f'<line x1="{left}" x2="{w - right}" y1="{y:.1f}" y2="{y:.1f}" style="stroke:var(--border)"/>'
        )
        parts.append(
            f'<text x="{left - 12}" y="{y + 6:.1f}" font-size="16" text-anchor="end">{_fmt(val, chart.unit)}</text>'
        )
    n = len(chart.categories)
    band = plot_w / n
    for i, cat in enumerate(chart.categories):
        cx = left + band * (i + 0.5)
        parts.append(
            f'<text x="{cx:.1f}" y="{top + plot_h + 34}" font-size="20" text-anchor="middle">{escape(cat)}</text>'
        )
    if chart.type == "bar":
        group = band * 0.7
        bar_w = group / len(chart.series)
        for si, s in enumerate(chart.series):
            for i, v in enumerate(s.values):
                bh = plot_h * v / top_value
                x = left + band * i + (band - group) / 2 + bar_w * si
                y = top + plot_h - bh
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w * 0.92:.1f}" height="{bh:.1f}" rx="3" style="fill:{SERIES_COLORS[si % 4]}"/>'
                    f'<text x="{x + bar_w * 0.46:.1f}" y="{y - 8:.1f}" font-size="16" text-anchor="middle">{_fmt(v, chart.unit)}</text>'
                )
    else:
        for si, s in enumerate(chart.series):
            pts = [
                (left + band * (i + 0.5), top + plot_h - plot_h * v / top_value)
                for i, v in enumerate(s.values)
            ]
            color = SERIES_COLORS[si % 4]
            path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            parts.append(
                f'<polyline points="{path}" style="fill:none;stroke:{color};stroke-width:4"/>'
            )
            for (x, y), v in zip(pts, s.values, strict=True):
                parts.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" style="fill:{color}"/>'
                    f'<text x="{x:.1f}" y="{y - 16:.1f}" font-size="16" text-anchor="middle">{_fmt(v, chart.unit)}</text>'
                )
    if len(chart.series) > 1:
        legend_w = 220 * len(chart.series)
        parts.append(_legend([s.name for s in chart.series], (w - legend_w) / 2, h - 24))
    parts.append("</svg>")
    return "".join(parts)


def _pie_svg(chart: Chart, w: int, h: int) -> str:
    values = chart.series[0].values
    total = sum(values) or 1.0
    cx, cy, r = 360, h / 2, 230
    colors = [*SERIES_COLORS, "var(--good)", "var(--warn)"]
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="chart">']
    angle = -math.pi / 2
    for i, v in enumerate(values):
        sweep = 2 * math.pi * v / total
        x1, y1 = cx + r * math.cos(angle), cy + r * math.sin(angle)
        x2, y2 = cx + r * math.cos(angle + sweep), cy + r * math.sin(angle + sweep)
        large = 1 if sweep > math.pi else 0
        color = colors[i % len(colors)]
        if len(values) == 1:
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" style="fill:{color}"/>')
        else:
            parts.append(
                f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {large} 1 {x2:.1f},{y2:.1f} Z" style="fill:{color};stroke:var(--bg);stroke-width:3"/>'
            )
        ly = 120 + i * 48
        parts.append(
            f'<rect x="700" y="{ly - 18}" width="22" height="22" rx="4" style="fill:{color}"/>'
            f'<text x="736" y="{ly}" font-size="24">{escape(chart.categories[i])}　{v / total:.0%}</text>'
        )
        angle += sweep
    parts.append("</svg>")
    return "".join(parts)


def _list(items: list[str], cls: str = "pd-list") -> str:
    return f'<ul class="{cls}">' + "".join(f"<li>{escape(t)}</li>" for t in items) + "</ul>"


def _slide_body(s: object) -> tuple[str, str]:
    if isinstance(s, CoverSlide):
        body = f'<h1 class="h1">{escape(s.title)}</h1>'
        if s.subtitle:
            body += f'<p class="lede">{escape(s.subtitle)}</p>'
        if s.footnote:
            body += f'<p class="pd-foot">{escape(s.footnote)}</p>'
        return "pd-cover", body
    head = f'<h2 class="pd-title">{escape(s.title)}</h2><div class="pd-rule"></div>'  # type: ignore[attr-defined]
    if isinstance(s, BulletsSlide):
        return "pd-bullets", head + _list(s.bullets)
    if isinstance(s, TwoColumnSlide):
        cards = "".join(
            f'<div class="card"><h4>{escape(c.heading)}</h4>{_list(c.bullets)}</div>'
            for c in (s.left, s.right)
        )
        return "pd-two-slide", head + f'<div class="grid g2 pd-two">{cards}</div>'
    if isinstance(s, ChartSlide):
        body = head + f'<div class="pd-chart">{chart_svg(s.chart)}</div>'
        if s.takeaway:
            body += f'<div class="pd-takeaway">{escape(s.takeaway)}</div>'
        return "pd-chart-slide", body
    if isinstance(s, TableSlide):
        rows = "".join(
            "<tr>" + "".join(f"<td>{escape(c)}</td>" for c in r) + "</tr>" for r in s.table.rows
        )
        header = "".join(f"<th>{escape(h)}</th>" for h in s.table.header)
        body = (
            head
            + f'<table class="pd-table"><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>'
        )
        if s.takeaway:
            body += f'<div class="pd-takeaway">{escape(s.takeaway)}</div>'
        return "pd-table-slide", body
    if isinstance(s, ClosingSlide):
        steps = "".join(f"<li><span>{escape(t)}</span></li>" for t in s.items)
        return "pd-closing", head + f'<ol class="pd-steps">{steps}</ol>'
    raise ValueError(f"unsupported layout: {s!r}")


def build_html(spec: DeckSpec, theme_key: str | None, out_path: Path) -> Path:
    theme = available_theme(theme_key)
    total = len(spec.slides)
    sections = []
    for i, s in enumerate(spec.slides, start=1):
        cls, body = _slide_body(s)
        footer = (
            ""
            if isinstance(s, CoverSlide)
            else f'<div class="deck-footer"><span class="dim2">{escape(spec.title)}</span>'
            f'<span class="slide-number" data-current="{i}" data-total="{total}"></span></div>'
        )
        notes = f'<div class="notes">{escape(s.notes)}</div>' if s.notes else ""
        title = escape(getattr(s, "title", ""))
        sections.append(
            f'<section class="slide {cls}" data-title="{title}">{body}{footer}{notes}</section>'
        )
    html = f"""<!DOCTYPE html>
<html lang="{escape(spec.language)}" data-theme="{theme}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(spec.title)}</title>
<style>{_asset("base.css")}</style>
<style id="theme">{_asset(f"themes/{theme}.css")}</style>
<style>{ENGINE_CSS}</style>
</head>
<body>
<div class="deck">
{chr(10).join(sections)}
</div>
<script>{_asset("runtime.js")}</script>
<script>{CHECK_JS}</script>
<script>{THEME_JS.replace("__THEMES__", _themes_json())}</script>
</body></html>
"""
    out_path.write_text(html, encoding="utf-8")
    return out_path
