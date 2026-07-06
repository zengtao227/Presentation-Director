#!/usr/bin/env python3
"""
Generate assets/locks-preview.html — structural comparison of all design-locks.

By default renders all locks in a NEUTRAL off-white color scheme so the user
can compare LAYOUT STRUCTURE (grid, typography hierarchy, card grammar) without
being distracted by each lock's original color personality.

If assets/palettes.json exists with a confirmed palette, a toggle button lets
the user preview all locks in their own Step-4 colors.

Usage:
    python3 scripts/preview_locks.py
    # then open: assets/locks-preview.html
"""

# MAINTENANCE: scripts/preview_locks.py (repo top level) must stay byte-identical
# to this file — do not replace it with a runpy shim (see Global Constraints in
# docs/superpowers/plans/2026-07-06-review-remediation.md for why). After editing
# this file, run: cp skills/deck-builder/scripts/preview_locks.py scripts/preview_locks.py
# Enforced by tests/test_presentation_director.py::TopLevelScriptSyncTest.

import http.server
import json as _json
import socket
import sys
import threading
import webbrowser
from pathlib import Path

MAX_POST_BYTES = 64_000


# ── Color helpers ────────────────────────────────────────────────────────────

def _blend(h1: str, h2: str, t: float) -> str:
    """Blend two hex colors. t=0 → h1, t=1 → h2."""
    r1, g1, b1 = int(h1[1:3], 16), int(h1[3:5], 16), int(h1[5:7], 16)
    r2, g2, b2 = int(h2[1:3], 16), int(h2[3:5], 16), int(h2[5:7], 16)
    r = round(r1 * (1 - t) + r2 * t)
    g = round(g1 * (1 - t) + g2 * t)
    b = round(b1 * (1 - t) + b2 * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _apply_subs(html: str, subs: list) -> str:
    for old, new in subs:
        html = html.replace(old, new)
    return html


# ── Neutral palette (applied when no Step-4 palette is available) ────────────
# All values are intentionally dull / achromatic so the layout reads clearly.

N = {
    "bg":       "#f7f7f5",
    "bg2":      "#ececea",
    "text":     "#1a1a1a",
    "text2":    "#555555",
    "accent":   "#2a2a2a",   # dark structural element (bars, borders as structure)
    "muted":    "#888888",
    "muted2":   "#aaaaaa",
    "card":     "#ebebea",
    "border":   "#c0c0be",
    "on_dark":  "#f0f0f0",   # light text sitting on a dark structural block
}

# Per-lock ordered substitution list for neutral mode.
# ORDER MATTERS — more specific patterns (full CSS property strings) before bare hex.
NEUTRAL_SUBS: dict[str, list] = {
    "swiss-klein-blue": [
        ("#fafaf8",   N["bg"]),
        ("#002FA7",   N["accent"]),
        ("#0a0a0a",   N["text"]),
        ("#1a1a1a",   N["text"]),
        ("#6b6b6b",   N["muted"]),
        ("#bbb",      N["muted2"]),
        ("#f0f0ee",   N["card"]),
    ],
    "linear-dark": [
        ("#08090a",   N["bg"]),
        ("#0f1011",   N["card"]),
        ("#5e6ad2",   N["accent"]),
        ("#f7f8f8",   N["text"]),
        ("#d0d6e0",   N["text2"]),
        ("#8a8f98",   N["muted"]),
        ("#3a3f47",   N["muted"]),
        ("#62666d",   N["muted"]),
        ("#23252a",   N["border"]),
    ],
    "academic": [
        # bg first (full property string to avoid replacing text uses of same hex)
        ("background:#f1f3f5",            f'background:{N["bg"]}'),
        # text on the dark header block → keep it light
        ("color:#f1f3f5",                 f'color:{N["on_dark"]}'),
        ("rgba(241,243,245,.45)",         "rgba(240,240,240,.45)"),
        ("rgba(241,243,245,.55)",         "rgba(240,240,240,.55)"),
        # dark structural color (header block bg, border, labels)
        ("#0a1f3d",                       N["accent"]),
        ("#4a6080",                       N["muted"]),
        ("#d0d7df",                       N["border"]),
        ("#e4e8ec",                       N["card"]),
        ("#c8d0da",                       N["border"]),
    ],
    "editorial": [
        ("#f1efea",   N["bg"]),
        ("#0a0a0b",   N["text"]),
        ("#5a5650",   N["muted"]),
        ("#8a8580",   N["muted2"]),
    ],
    "notion-warm": [
        ("#ffffff",   N["bg"]),
        ("#f6f5f4",   N["card"]),
        ("#0d0d0d",   N["text"]),
        ("#615d59",   N["muted"]),
        ("#9c9894",   N["muted2"]),
    ],
}


def _palette_subs(lock_id: str, p: dict) -> list:
    """Build substitution list for applying a user palette to a specific lock."""
    bg, text, accent, muted = p["bg"], p["text"], p["accent"], p["muted"]
    card   = _blend(bg, text, 0.07)
    border = _blend(bg, text, 0.15)
    card2  = _blend(bg, text, 0.12)

    if lock_id == "swiss-klein-blue":
        return [
            ("#fafaf8",   bg),
            ("#002FA7",   accent),
            ("#0a0a0a",   text),
            ("#1a1a1a",   text),
            ("#6b6b6b",   muted),
            ("#bbb",      muted),
            ("#f0f0ee",   card),
        ]
    if lock_id == "linear-dark":
        return [
            ("#08090a",   bg),
            ("#0f1011",   card),
            ("#5e6ad2",   accent),
            ("#f7f8f8",   text),
            ("#d0d6e0",   text),
            ("#8a8f98",   muted),
            ("#3a3f47",   muted),
            ("#62666d",   muted),
            ("#23252a",   border),
        ]
    if lock_id == "academic":
        return [
            ("background:#f1f3f5",           f"background:{bg}"),
            ("color:#f1f3f5",                "color:#f0f0f0"),   # text on dark block → keep light
            ("rgba(241,243,245,.45)",         "rgba(240,240,240,.45)"),
            ("rgba(241,243,245,.55)",         "rgba(240,240,240,.55)"),
            ("#0a1f3d",                       accent),
            ("#4a6080",                       muted),
            ("#d0d7df",                       border),
            ("#e4e8ec",                       card),
            ("#c8d0da",                       card2),
        ]
    if lock_id == "editorial":
        return [
            ("#f1efea",   bg),
            ("#0a0a0b",   text),
            ("#5a5650",   muted),
            ("#8a8580",   muted),
        ]
    if lock_id == "notion-warm":
        return [
            ("#ffffff",   bg),
            ("#f6f5f4",   card),
            ("#0d0d0d",   text),
            ("#615d59",   muted),
            ("#9c9894",   muted),
        ]
    return []


# ── Design locks ─────────────────────────────────────────────────────────────
# name / zh now describe STRUCTURE, not color.
# structure_desc describes layout grammar, not mood or color.

_LOCKS_RAW = [
    {
        "id": "swiss-klein-blue",
        "name": "Swiss Grid",
        "zh": "极简网格",
        "structure_desc": "边栏分割 · 严格栅格 · 精密层级",
        "suitable": ["商业计划", "产品路线图", "投资人演示", "执行报告"],
        "avoid": ["文化类", "叙事性演示"],
        "cover_html": """<div style="display:flex; height:100%; gap:0; background:#fafaf8;">
  <div style="width:6px; background:#002FA7; flex-shrink:0;"></div>
  <div style="flex:1; padding:22px 28px; display:flex; flex-direction:column; justify-content:space-between;">
    <div style="font-size:7.5px; font-weight:700; letter-spacing:2.5px; color:#002FA7; text-transform:uppercase;">STRATEGY REPORT 2024</div>
    <div>
      <div style="font-size:22px; font-weight:800; line-height:1.15; color:#0a0a0a; font-family:'Inter',sans-serif; margin-bottom:14px;">AI 基础设施<br>行业全景报告</div>
      <div style="height:2px; background:#002FA7; width:48px; margin-bottom:12px;"></div>
      <div style="font-size:9px; color:#6b6b6b;">中国 AI 产业研究院 · 2024.Q4</div>
    </div>
    <div style="font-size:7px; color:#bbb;">01 / 18</div>
  </div>
</div>""",
        "slide_html": """<div style="display:flex; height:100%; gap:0;">
  <div style="width:6px; background:#002FA7; flex-shrink:0;"></div>
  <div style="flex:1; padding:20px 24px; display:flex; flex-direction:column; gap:0;">
    <div style="font-size:8px; font-weight:700; letter-spacing:2px; color:#002FA7; text-transform:uppercase; margin-bottom:6px;">SECTION 02</div>
    <div style="font-size:18px; font-weight:800; line-height:1.15; color:#0a0a0a; margin-bottom:14px; font-family:'Inter',sans-serif;">市场规模已达 2,400 亿<br>年增速维持 34%</div>
    <div style="height:2px; background:#0a0a0a; width:40px; margin-bottom:14px;"></div>
    <div style="display:flex; gap:14px; flex:1;">
      <div style="flex:1; background:#f0f0ee; padding:10px; border-radius:2px;">
        <div style="font-size:9px; font-weight:700; color:#002FA7; margin-bottom:4px;">核心驱动</div>
        <div style="font-size:8px; color:#1a1a1a; line-height:1.6;">企业数字化转型加速<br>AI 基础设施投入翻倍<br>政策支持持续加码</div>
      </div>
      <div style="flex:1; background:#f0f0ee; padding:10px; border-radius:2px;">
        <div style="font-size:9px; font-weight:700; color:#002FA7; margin-bottom:4px;">竞争格局</div>
        <div style="font-size:8px; color:#1a1a1a; line-height:1.6;">头部集中度提升<br>垂直赛道分化明显<br>海外扩张窗口开启</div>
      </div>
    </div>
    <div style="margin-top:10px; font-size:7px; color:#6b6b6b; display:flex; justify-content:space-between;">
      <span>来源：IDC 2024</span><span>02 / 10</span>
    </div>
  </div>
</div>""",
    },
    {
        "id": "linear-dark",
        "name": "Engineering",
        "zh": "工程卡片",
        "structure_desc": "卡片边框 · 高密度 · 代码块结构",
        "suitable": ["SaaS 产品", "技术平台", "工程演示", "投资人（技术背景）"],
        "avoid": ["教学类", "文化类"],
        "cover_html": """<div style="height:100%; padding:24px 28px; display:flex; flex-direction:column; justify-content:space-between; background:#08090a;">
  <div style="display:flex; align-items:center; gap:8px;">
    <div style="width:8px; height:8px; border-radius:50%; background:#5e6ad2;"></div>
    <div style="font-size:7.5px; font-weight:600; color:#8a8f98; letter-spacing:1.5px; text-transform:uppercase; font-family:monospace;">Product · Engineering · 2024</div>
  </div>
  <div>
    <div style="font-size:21px; font-weight:700; color:#f7f8f8; line-height:1.2; font-family:'Inter',sans-serif; margin-bottom:10px;">重新定义<br>云原生部署流水线</div>
    <div style="font-size:9px; color:#5e6ad2; font-family:monospace;">v3.0 Architecture Deep Dive</div>
  </div>
  <div style="display:flex; justify-content:space-between; font-size:7px; color:#3a3f47; font-family:monospace;">
    <span>Internal · Confidential</span><span style="color:#5e6ad2;">01 / 12</span>
  </div>
</div>""",
        "slide_html": """<div style="height:100%; padding:18px 22px; display:flex; flex-direction:column; gap:0; background:#08090a;">
  <div style="display:flex; align-items:center; gap:8px; margin-bottom:14px;">
    <div style="width:8px; height:8px; border-radius:50%; background:#5e6ad2;"></div>
    <div style="font-size:8px; font-weight:600; color:#8a8f98; letter-spacing:1.5px; text-transform:uppercase;">Architecture Overview</div>
  </div>
  <div style="font-size:16px; font-weight:700; color:#f7f8f8; line-height:1.2; margin-bottom:16px; font-family:'Inter',sans-serif;">三层解耦架构将部署时间<br>从 4 小时压缩至 11 分钟</div>
  <div style="display:flex; gap:8px; flex:1;">
    <div style="flex:1; border:1px solid #23252a; border-radius:4px; padding:10px;">
      <div style="font-size:8px; font-weight:600; color:#5e6ad2; margin-bottom:6px; font-family:monospace;">API Layer</div>
      <div style="font-size:7.5px; color:#d0d6e0; line-height:1.7; font-family:monospace;">rate-limit: 10k/min<br>auth: JWT + mTLS<br>cache: Redis L1</div>
    </div>
    <div style="flex:1; border:1px solid #23252a; border-radius:4px; padding:10px; background:#0f1011;">
      <div style="font-size:8px; font-weight:600; color:#5e6ad2; margin-bottom:6px; font-family:monospace;">Core Engine</div>
      <div style="font-size:7.5px; color:#d0d6e0; line-height:1.7; font-family:monospace;">workers: 32 goroutines<br>queue: Kafka<br>latency: p99 &lt; 40ms</div>
    </div>
    <div style="flex:1; border:1px solid #23252a; border-radius:4px; padding:10px;">
      <div style="font-size:8px; font-weight:600; color:#5e6ad2; margin-bottom:6px; font-family:monospace;">Storage</div>
      <div style="font-size:7.5px; color:#d0d6e0; line-height:1.7; font-family:monospace;">pg: write-primary<br>s3: cold archive<br>ttl: 90d policy</div>
    </div>
  </div>
  <div style="margin-top:10px; font-size:7px; color:#62666d; display:flex; justify-content:space-between;">
    <span>Internal · Confidential</span><span style="color:#5e6ad2;">05 / 12</span>
  </div>
</div>""",
    },
    {
        "id": "academic",
        "name": "Academic",
        "zh": "学术层级",
        "structure_desc": "双色块 · 数据表格 · 权威分割线",
        "suitable": ["技术方案", "数据报告", "竞赛答辩", "学术研究"],
        "avoid": ["温暖叙事类", "消费者品牌"],
        "cover_html": """<div style="height:100%; display:flex; flex-direction:column; background:#f1f3f5;">
  <div style="background:#0a1f3d; flex:2.2; padding:20px 26px; display:flex; flex-direction:column; justify-content:flex-end;">
    <div style="font-size:7.5px; color:rgba(241,243,245,.45); letter-spacing:1.5px; margin-bottom:10px; font-family:'Noto Serif SC',serif;">研究报告 · 2024</div>
    <div style="font-size:20px; font-weight:700; color:#f1f3f5; line-height:1.3; font-family:'Noto Serif SC',serif;">AI 企业采用率<br>深度调研报告</div>
  </div>
  <div style="flex:1; padding:12px 26px; display:flex; align-items:center; justify-content:space-between; border-top:2px solid #0a1f3d;">
    <div style="font-size:9px; color:#0a1f3d; font-family:'Noto Serif SC',serif;">中国信通院 · 产业研究部</div>
    <div style="font-size:7.5px; color:#4a6080;">01 / 09</div>
  </div>
</div>""",
        "slide_html": """<div style="height:100%; display:flex; flex-direction:column; background:#f1f3f5;">
  <div style="background:#0a1f3d; padding:12px 22px 10px; display:flex; align-items:baseline; gap:12px;">
    <div style="font-size:16px; font-weight:700; color:#f1f3f5; font-family:'Noto Serif SC',serif; line-height:1.2;">数据显示：三类企业占据<br>行业 78% 的 AI 研发投入</div>
    <div style="font-size:7px; color:rgba(241,243,245,.55); align-self:flex-end; white-space:nowrap;">图 3-2</div>
  </div>
  <div style="flex:1; padding:12px 22px; display:flex; gap:14px;">
    <div style="flex:2;">
      <div style="font-size:7.5px; font-weight:600; color:#4a6080; letter-spacing:1px; text-transform:uppercase; margin-bottom:7px;">企业类型分布（N=847）</div>
      <div style="border-top:1.5px solid #0a1f3d;">
        <div style="display:flex; padding:5px 0; border-bottom:1px solid #d0d7df; font-size:8px;">
          <div style="flex:2; font-weight:600; color:#0a1f3d; font-family:'Noto Serif SC',serif;">大型国央企</div>
          <div style="flex:1; text-align:right; color:#0a1f3d;">43.2%</div>
          <div style="flex:1; text-align:right; color:#4a6080;">↑ 6.1pp</div>
        </div>
        <div style="display:flex; padding:5px 0; border-bottom:1px solid #d0d7df; font-size:8px; background:#e4e8ec;">
          <div style="flex:2; font-weight:600; color:#0a1f3d; font-family:'Noto Serif SC',serif;">科技独角兽</div>
          <div style="flex:1; text-align:right; color:#0a1f3d;">22.7%</div>
          <div style="flex:1; text-align:right; color:#4a6080;">↑ 3.4pp</div>
        </div>
        <div style="display:flex; padding:5px 0; border-bottom:1px solid #d0d7df; font-size:8px;">
          <div style="flex:2; font-weight:600; color:#0a1f3d; font-family:'Noto Serif SC',serif;">专精特新企业</div>
          <div style="flex:1; text-align:right; color:#0a1f3d;">12.1%</div>
          <div style="flex:1; text-align:right; color:#4a6080;">↑ 1.8pp</div>
        </div>
      </div>
    </div>
    <div style="flex:1; border-left:2px solid #0a1f3d; padding-left:10px;">
      <div style="font-size:8px; font-weight:700; color:#0a1f3d; margin-bottom:5px; font-family:'Noto Serif SC',serif;">研究方法</div>
      <div style="font-size:7.5px; color:#4a6080; line-height:1.65;">问卷+访谈混合<br>置信区间 95%<br>抽样误差 ±3.2%</div>
    </div>
  </div>
  <div style="padding:4px 22px 7px; font-size:6.5px; color:#4a6080; border-top:1px solid #c8d0da;">
    资料来源：中国信通院《2024年企业AI采用率报告》第三章 &nbsp;|&nbsp; 03 / 09
  </div>
</div>""",
    },
    {
        "id": "editorial",
        "name": "Editorial",
        "zh": "叙事版式",
        "structure_desc": "引言竖栏 · 长文段落 · 纵向叙事",
        "suitable": ["路演", "课程汇报", "观点类演示", "项目方案"],
        "avoid": ["纯工程类", "数据密集报告"],
        "cover_html": """<div style="height:100%; padding:22px 32px 18px; display:flex; flex-direction:column; justify-content:space-between; background:#f1efea;">
  <div style="font-size:7.5px; letter-spacing:2.5px; color:#5a5650; text-transform:uppercase;">演讲 · 2024</div>
  <div>
    <div style="font-size:22px; font-weight:700; color:#0a0a0b; line-height:1.25; font-family:'Noto Serif SC',serif; margin-bottom:12px;">为什么大多数<br>产品创新都在白费力气</div>
    <div style="border-left:3px solid #0a0a0b; padding-left:10px; font-size:9px; font-style:italic; color:#5a5650; font-family:'Noto Serif SC',serif; line-height:1.6;">一个关于用户价值的深度观察</div>
  </div>
  <div style="font-size:7.5px; color:#8a8580;">张明 · 产品副总裁 &nbsp;|&nbsp; 01 / 11</div>
</div>""",
        "slide_html": """<div style="height:100%; padding:18px 28px 14px 28px; display:flex; flex-direction:column; background:#f1efea;">
  <div style="font-size:7.5px; letter-spacing:2px; color:#5a5650; text-transform:uppercase; margin-bottom:8px;">洞察 · 03</div>
  <div style="font-size:17px; font-weight:700; line-height:1.25; color:#0a0a0b; margin-bottom:12px; font-family:'Noto Serif SC',serif; max-width:80%;">用户不是不愿付费，<br>而是还没看到值得付费的东西</div>
  <div style="border-left:3px solid #0a0a0b; padding-left:12px; margin-bottom:12px;">
    <div style="font-size:10px; font-style:italic; color:#0a0a0b; line-height:1.6; font-family:'Noto Serif SC',serif;">"我们访谈了 200 位流失用户，89% 给出的理由不是价格，而是「功能没用到」。"</div>
    <div style="font-size:7.5px; color:#5a5650; margin-top:4px;">— 用户研究报告，2024.Q3</div>
  </div>
  <div style="font-size:8.5px; color:#0a0a0b; line-height:1.75; font-family:'Noto Serif SC',serif; flex:1; opacity:.85;">
    付费转化率低的核心原因在于价值感知缺口。当产品的核心功能与用户实际工作流高度契合时，付费意愿显著提升——平均溢价接受度达到免费版的 3.4 倍。
  </div>
  <div style="font-size:7px; color:#8a8580; margin-top:8px;">04 / 11</div>
</div>""",
    },
    {
        "id": "notion-warm",
        "name": "Document",
        "zh": "文档列表",
        "structure_desc": "卡片列表 · 扁平层级 · 亲和结构",
        "suitable": ["内部汇报", "文化类", "课程讲义", "轻量演示"],
        "avoid": ["投资人演示", "高强度外部场合"],
        "cover_html": """<div style="height:100%; padding:24px 30px; display:flex; flex-direction:column; justify-content:space-between; background:#ffffff;">
  <div style="font-size:8px; color:#615d59; font-weight:500; letter-spacing:.5px;">2024 Q3 · 内部复盘</div>
  <div>
    <div style="font-size:21px; font-weight:700; color:#0d0d0d; line-height:1.3; font-family:'Inter',sans-serif; margin-bottom:10px;">产品团队<br>季度总结</div>
    <div style="font-size:9.5px; color:#615d59; line-height:1.7;">三个值得关注的结构性变化<br>以及下季度的重点方向</div>
  </div>
  <div style="display:flex; align-items:center; gap:10px;">
    <div style="width:18px; height:18px; background:#0d0d0d; border-radius:3px;"></div>
    <div style="font-size:9px; color:#9c9894;">产品团队 &nbsp;·&nbsp; 01 / 08</div>
  </div>
</div>""",
        "slide_html": """<div style="height:100%; padding:20px 26px; display:flex; flex-direction:column; gap:0; background:#ffffff;">
  <div style="font-size:15px; font-weight:700; color:#0d0d0d; margin-bottom:6px; font-family:'Inter',sans-serif;">本季度三个值得关注的变化</div>
  <div style="font-size:8.5px; color:#615d59; margin-bottom:16px;">2024 Q3 内部复盘 · 产品团队</div>
  <div style="display:flex; flex-direction:column; gap:8px; flex:1;">
    <div style="background:#f6f5f4; border-radius:6px; padding:10px 12px; display:flex; gap:10px; align-items:flex-start;">
      <div style="width:20px; height:20px; background:#0d0d0d; border-radius:4px; flex-shrink:0; display:flex; align-items:center; justify-content:center;">
        <div style="width:8px; height:1.5px; background:white;"></div>
      </div>
      <div>
        <div style="font-size:9px; font-weight:600; color:#0d0d0d; margin-bottom:2px;">日活增长放缓，但留存显著改善</div>
        <div style="font-size:7.5px; color:#615d59; line-height:1.6;">次日留存从 38% 升至 51%，7日留存从 19% 升至 27%</div>
      </div>
    </div>
    <div style="background:#f6f5f4; border-radius:6px; padding:10px 12px; display:flex; gap:10px; align-items:flex-start;">
      <div style="width:20px; height:20px; background:#0d0d0d; border-radius:4px; flex-shrink:0; display:flex; align-items:center; justify-content:center;">
        <div style="width:8px; height:1.5px; background:white;"></div>
      </div>
      <div>
        <div style="font-size:9px; font-weight:600; color:#0d0d0d; margin-bottom:2px;">移动端使用比例超过桌面端</div>
        <div style="font-size:7.5px; color:#615d59; line-height:1.6;">移动占比 54%，较上季度 +11pp，催生新的导航需求</div>
      </div>
    </div>
    <div style="background:#f6f5f4; border-radius:6px; padding:10px 12px; display:flex; gap:10px; align-items:flex-start;">
      <div style="width:20px; height:20px; background:#0d0d0d; border-radius:4px; flex-shrink:0; display:flex; align-items:center; justify-content:center;">
        <div style="width:8px; height:1.5px; background:white;"></div>
      </div>
      <div>
        <div style="font-size:9px; font-weight:600; color:#0d0d0d; margin-bottom:2px;">NPS 从 32 跃升至 48</div>
        <div style="font-size:7.5px; color:#615d59; line-height:1.6;">主要驱动因素为新版编辑器和搜索速度提升</div>
      </div>
    </div>
  </div>
  <div style="font-size:7px; color:#9c9894; margin-top:10px; text-align:right;">03 / 08</div>
</div>""",
    },
]


def _build_locks(palette: dict | None) -> list:
    result = []
    for raw in _LOCKS_RAW:
        lid = raw["id"]
        entry = {
            "id":             lid,
            "name":           raw["name"],
            "zh":             raw["zh"],
            "structure_desc": raw["structure_desc"],
            "suitable":       raw["suitable"],
            "avoid":          raw["avoid"],
            "cover_neutral":  _apply_subs(raw["cover_html"], NEUTRAL_SUBS[lid]),
            "slide_neutral":  _apply_subs(raw["slide_html"], NEUTRAL_SUBS[lid]),
        }
        if palette:
            subs = _palette_subs(lid, palette)
            entry["cover_palette"] = _apply_subs(raw["cover_html"], subs)
            entry["slide_palette"] = _apply_subs(raw["slide_html"], subs)
        result.append(entry)
    return result


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>结构层预览 — Design Locks</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Serif+SC:wght@400;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#eceae6;min-height:100vh;padding:28px 24px 48px;color:#1a1a1a}
h1{font-size:20px;font-weight:700;color:#111;margin-bottom:4px}
.subtitle{font-size:13px;color:#666;margin-bottom:8px;line-height:1.5}
.palette-bar{display:flex;align-items:center;gap:10px;margin-bottom:20px;min-height:32px}
.palette-info{font-size:12px;color:#444;display:flex;align-items:center;gap:8px}
.swatch{width:16px;height:16px;border-radius:3px;border:1px solid rgba(0,0,0,.1);flex-shrink:0}
.toggle-btn{padding:6px 16px;border-radius:20px;border:1.5px solid #2a2a2a;background:white;font-size:12px;font-weight:600;color:#2a2a2a;cursor:pointer;transition:all .15s}
.toggle-btn:hover{background:#f0f0ee}
.toggle-btn.palette-active{background:#2a2a2a;color:white;border-color:#2a2a2a}
.neutral-note{font-size:11px;color:#888;background:#f4f4f2;padding:3px 10px;border-radius:10px}

.layout{display:flex;gap:20px;max-width:1100px;align-items:flex-start}

/* Sidebar */
.sidebar{width:172px;flex-shrink:0;background:white;border-radius:12px;padding:8px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.sidebar-item{padding:10px 12px;border-radius:8px;cursor:pointer;transition:background .12s;margin-bottom:2px;user-select:none}
.sidebar-item:hover{background:#f4f4f2}
.sidebar-item.active{background:#EEF3FF;border-left:3px solid #0061FF;padding-left:9px}
.sidebar-name{font-size:13px;font-weight:700;color:#111;line-height:1.3}
.sidebar-item.active .sidebar-name{color:#0061FF}
.sidebar-zh{font-size:11px;color:#888;margin-top:1px}

/* Detail */
.detail{flex:1;min-width:0}
.slides-row{display:flex;gap:12px;margin-bottom:14px}
.slide-col{flex:1;min-width:0}
.slide-label{font-size:10px;font-weight:600;color:#888;letter-spacing:.5px;text-transform:uppercase;margin-bottom:5px}
.slide-frame{width:100%;aspect-ratio:16/9;position:relative;border-radius:8px;overflow:hidden;box-shadow:0 3px 14px rgba(0,0,0,.13)}

/* Desc box */
.desc-box{background:white;border-radius:10px;padding:14px 18px;box-shadow:0 1px 4px rgba(0,0,0,.06);display:flex;gap:24px}
.desc-left{flex:1;min-width:0}
.desc-title{font-size:15px;font-weight:700;color:#111;margin-bottom:2px}
.desc-zh{font-size:12px;color:#888;margin-bottom:8px}
.desc-tags{font-size:12px;color:#444;line-height:1.6;border-left:2px solid #ddd;padding-left:10px}
.desc-right{width:200px;flex-shrink:0}
.use-section{margin-bottom:10px}
.use-label{font-size:10px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;margin-bottom:5px}
.use-label.good{color:#16a34a}
.use-label.bad{color:#dc2626}
.use-tags{display:flex;flex-wrap:wrap;gap:4px}
.tag{font-size:11px;padding:3px 8px;border-radius:20px;line-height:1.4}
.tag.good{background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0}
.tag.bad{background:#fff1f2;color:#be123c;border:1px solid #fecdd3}

/* Confirm */
.confirm-area{margin-top:14px;display:flex;align-items:center;gap:14px}
.confirm-btn{padding:11px 26px;background:#0061FF;color:white;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;transition:background .15s,transform .1s}
.confirm-btn:hover{background:#004ee0;transform:translateY(-1px)}
.confirm-btn.done{background:#16a34a;cursor:default;transform:none}
.copied-msg{display:none;font-size:13px;color:#16a34a;font-weight:600;padding:10px 14px;background:#f0fdf4;border-radius:8px;border:1px solid #bbf7d0;line-height:1.5}
.copied-msg.show{display:block}
</style>
</head>
<body>
<h1>Step 5 — 结构层选择</h1>
<p class="subtitle">此处选择布局语法（网格、字体层级、卡片结构），与配色无关。预览默认已去除各自颜色，便于纯粹比较结构。</p>

<div class="palette-bar" id="palette-bar"></div>

<div class="layout">
  <div class="sidebar" id="sidebar"></div>
  <div class="detail">
    <div class="slides-row">
      <div class="slide-col">
        <div class="slide-label">封面</div>
        <div class="slide-frame" id="cover-frame"></div>
      </div>
      <div class="slide-col">
        <div class="slide-label">内页</div>
        <div class="slide-frame" id="content-frame"></div>
      </div>
    </div>
    <div class="desc-box">
      <div class="desc-left">
        <div class="desc-title" id="desc-title"></div>
        <div class="desc-zh" id="desc-zh"></div>
        <div class="desc-tags" id="desc-tags"></div>
      </div>
      <div class="desc-right">
        <div class="use-section">
          <div class="use-label good">✓ 适合</div>
          <div class="use-tags" id="suitable-tags"></div>
        </div>
        <div class="use-section">
          <div class="use-label bad">✗ 不适合</div>
          <div class="use-tags" id="avoid-tags"></div>
        </div>
      </div>
    </div>
    <div class="confirm-area">
      <button class="confirm-btn" id="confirm-btn" onclick="confirmSelection()">确认此结构层 →</button>
      <div class="copied-msg" id="copied-msg">
        ✓ 已复制到剪贴板！<br>粘贴到 Claude 对话框，继续生成。
      </div>
    </div>
  </div>
</div>

<script>
const LOCKS = __LOCKS_JSON__;
const PALETTE = __PALETTE_JSON__;
let activeId = LOCKS[0].id;
let showPalette = false;

function renderPaletteBar() {
  const bar = document.getElementById('palette-bar');
  if (PALETTE) {
    const swatches = ['bg','text','accent','muted']
      .map(r => `<div class="swatch" style="background:${PALETTE[r]}" title="${r}: ${PALETTE[r]}"></div>`)
      .join('');
    bar.innerHTML = `
      <span class="neutral-note">默认：中性色结构预览</span>
      <button class="toggle-btn ${showPalette?'palette-active':''}" id="toggle-btn" onclick="toggleMode()">
        ${showPalette ? '切换回中性色 ↩' : '用我的配色预览 →'}
      </button>
      <span class="palette-info">${swatches}
        <span style="font-size:11px;color:#888;">${PALETTE.name||''}</span>
      </span>`;
  } else {
    bar.innerHTML = `<span class="neutral-note">中性色模式 · 专注比较布局结构</span>`;
  }
}

function render() {
  const lock = LOCKS.find(l => l.id === activeId);
  const usePalette = showPalette && lock.cover_palette;
  const wrap = h => '<div style="position:absolute;inset:0;">' + h + '</div>';
  document.getElementById('cover-frame').innerHTML   = wrap(usePalette ? lock.cover_palette : lock.cover_neutral);
  document.getElementById('content-frame').innerHTML = wrap(usePalette ? lock.slide_palette : lock.slide_neutral);
  document.getElementById('sidebar').innerHTML = LOCKS.map(l => `
    <div class="sidebar-item ${l.id===activeId?'active':''}" onclick="selectLock('${l.id}')">
      <div class="sidebar-name">${l.name}</div>
      <div class="sidebar-zh">${l.zh}</div>
    </div>`).join('');
  document.getElementById('desc-title').textContent  = lock.name;
  document.getElementById('desc-zh').textContent     = lock.zh;
  document.getElementById('desc-tags').textContent   = lock.structure_desc;
  document.getElementById('suitable-tags').innerHTML = lock.suitable.map(t=>`<span class="tag good">${t}</span>`).join('');
  document.getElementById('avoid-tags').innerHTML    = lock.avoid.map(t=>`<span class="tag bad">${t}</span>`).join('');
  document.getElementById('confirm-btn').textContent = '确认此结构层 →';
  document.getElementById('confirm-btn').classList.remove('done');
  document.getElementById('copied-msg').classList.remove('show');
}

function selectLock(id) { activeId = id; render(); }

function toggleMode() {
  showPalette = !showPalette;
  renderPaletteBar();
  render();
}

function confirmSelection() {
  const lock = LOCKS.find(l => l.id === activeId);
  const text = `我选择 ${lock.name} / ${lock.zh}`;
  fetch('/confirmed',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id:lock.id,name:lock.name,zh:lock.zh,text:text})
  }).then(r=>r.ok?r:Promise.reject()).then(()=>{
    document.getElementById('confirm-btn').textContent='✓ 已发送至 Claude';
    document.getElementById('confirm-btn').classList.add('done');
    document.getElementById('copied-msg').textContent='✓ 选择已自动发送，Claude 即将继续。';
    document.getElementById('copied-msg').classList.add('show');
  }).catch(()=>{
    navigator.clipboard.writeText(text).then(()=>{
      document.getElementById('confirm-btn').textContent='✓ 已复制（请粘贴到 Claude）';
      document.getElementById('confirm-btn').classList.add('done');
      document.getElementById('copied-msg').classList.add('show');
    });
  });
}

renderPaletteBar();
render();
</script>
</body>
</html>"""


_LOCKS_PORT = 7532
_SEL_FILE = Path("/tmp/deck-locks-selection.json")


class _LocksHandler(http.server.BaseHTTPRequestHandler):
    html: str = ""
    done: threading.Event = threading.Event()
    result: dict = {}

    def do_GET(self) -> None:
        if self.path in ('/', '/index.html'):
            body = self.html.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        if self.path == '/confirmed':
            try:
                body = self._read_body()
            except ValueError:
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'ok')
            try:
                _LocksHandler.result = _json.loads(body)
            except Exception:
                pass
            threading.Thread(target=_LocksHandler.done.set, daemon=True).start()
        else:
            self.send_response(404)
            self.end_headers()

    def _read_body(self) -> bytes:
        try:
            n = int(self.headers.get('Content-Length', '0'))
        except ValueError as exc:
            self.send_error(400, 'Invalid Content-Length')
            raise ValueError('invalid content length') from exc
        if n < 0:
            self.send_error(400, 'Invalid Content-Length')
            raise ValueError('negative content length')
        if n > MAX_POST_BYTES:
            self.send_error(413, 'Request body too large')
            raise ValueError('body too large')
        return self.rfile.read(n)

    def log_message(self, *_args: object) -> None:
        pass


def main() -> None:
    repo_root = Path(__file__).parent.parent
    assets_dir = repo_root / "assets"
    assets_dir.mkdir(exist_ok=True)

    # Try to read confirmed palette from palettes.json
    palette: dict | None = None
    palette_json = assets_dir / "palettes.json"
    if palette_json.exists():
        try:
            raw = _json.loads(palette_json.read_text(encoding="utf-8"))
            candidates = raw.get("palettes", raw) if isinstance(raw, dict) else raw
            if isinstance(candidates, list) and candidates:
                palette = candidates[0]
        except Exception:
            pass

    locks = _build_locks(palette)
    html_content = HTML_TEMPLATE.replace("__LOCKS_JSON__", _json.dumps(locks, ensure_ascii=False))
    palette_js = _json.dumps(palette, ensure_ascii=False) if palette else "null"
    html_content = html_content.replace("__PALETTE_JSON__", palette_js)

    # Write static fallback file
    out = assets_dir / "locks-preview.html"
    out.write_text(html_content, encoding="utf-8")

    # Find an available port starting from _LOCKS_PORT
    port = _LOCKS_PORT
    for _ in range(20):
        with socket.socket() as sock:
            if sock.connect_ex(('localhost', port)) != 0:
                break
            port += 1

    _LocksHandler.html = html_content
    _LocksHandler.done.clear()
    _LocksHandler.result = {}

    httpd = http.server.HTTPServer(('localhost', port), _LocksHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    url = f"http://localhost:{port}"
    print(f"✓ 结构层预览已启动: {url}")
    if palette:
        print(f"  配色已加载：{palette.get('name', '?')}  — 点「用我的配色预览」查看实际效果")
    else:
        print("  中性色模式（未找到 palettes.json）")
    print("  选择结构层后点「确认此结构层」，选择将自动发送给 Claude。")
    sys.stdout.flush()

    webbrowser.open(url)

    _LocksHandler.done.wait()
    httpd.shutdown()

    sel = _LocksHandler.result
    _SEL_FILE.write_text(_json.dumps(sel, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"DECK_SELECTION_LOCKS: {_json.dumps(sel, ensure_ascii=False)}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
