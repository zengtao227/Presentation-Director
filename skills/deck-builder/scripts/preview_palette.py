#!/usr/bin/env python3
"""
Generate assets/palette-preview.html.

Shows Claude's selected palettes (from assets/palettes.json) at the top,
followed by a full browsable library of 50 curated palettes with category
filter tabs.  User clicks any palette, then confirms — selection is
auto-copied to clipboard.

palettes.json may be either:
  - A plain array of palette objects (legacy / backward-compatible)
  - An object: {"deck_industry": "saas", "palettes": [...]}
    When deck_industry is present, the header shows it for context.

Usage:
    python3 scripts/preview_palette.py
    # then open: assets/palette-preview.html
"""

# MAINTENANCE: scripts/preview_palette.py (repo top level) must stay byte-identical
# to this file — do not replace it with a runpy shim (see Global Constraints in
# docs/superpowers/plans/2026-07-06-review-remediation.md for why). After editing
# this file, run: cp skills/deck-builder/scripts/preview_palette.py scripts/preview_palette.py
# Enforced by tests/test_presentation_director.py::TopLevelScriptSyncTest.

import http.server
import json
import socket
import sys
import threading
import webbrowser
from pathlib import Path

MAX_POST_BYTES = 64_000

# ── Built-in palette library ────────────────────────────────────────────────
# 50 curated palettes across 5 categories, sourced from ui-ux-pro-max colors.csv.
# Categories describe mood/style (for browsing), not industry.
# lock: recommended structure lock for each palette.

PALETTE_LIBRARY = [
    # ── 企业权威 corporate (10) ─────────────────────────────────────────────
    {
        "id": "lib-klein-authority",
        "name": "Klein Authority",
        "zh": "克莱因权威",
        "category": "corporate",
        "bg": "#fafaf8", "text": "#0a0a0a", "accent": "#002FA7", "muted": "#6b6b6b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "权威 · 精准 · 高对比",
        "lock": "swiss-klein-blue",
    },
    {
        "id": "lib-navy-executive",
        "name": "Navy Executive",
        "zh": "深海蓝执行力",
        "category": "corporate",
        "bg": "#f8f9fb", "text": "#0a1628", "accent": "#1d4ed8", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "专业 · 信赖感 · 企业蓝",
        "lock": "swiss-klein-blue",
    },
    {
        "id": "lib-gold-corporate",
        "name": "Cold Gold",
        "zh": "冷金权威",
        "category": "corporate",
        "bg": "#f5f4f0", "text": "#0a1f3d", "accent": "#C9A227", "muted": "#6b7280",
        "font_zh": "思源宋体", "font_en": "IBM Plex Sans",
        "mood": "高端品牌感 · 稳重权威 · 金调对比",
        "lock": "academic",
    },
    {
        "id": "lib-charcoal-elite",
        "name": "Charcoal Elite",
        "zh": "炭黑精英",
        "category": "corporate",
        "bg": "#fafafa", "text": "#111827", "accent": "#374151", "muted": "#9ca3af",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "极简权威 · 黑白对比 · 国际感",
        "lock": "swiss-klein-blue",
    },
    {
        "id": "lib-crimson-authority",
        "name": "Crimson Authority",
        "zh": "深红权威",
        "category": "corporate",
        "bg": "#fafafa", "text": "#1a0a0a", "accent": "#9B1C1C", "muted": "#6b7280",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "强势 · 决断力 · 红调品牌",
        "lock": "swiss-klein-blue",
    },
    {
        "id": "lib-navy-trust",
        "name": "Navy Trust",
        "zh": "海军信任",
        "category": "corporate",
        "bg": "#f8fafc", "text": "#020617", "accent": "#1e3a8a", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "银行 · 法律 · 稳健可信",
        "lock": "swiss-klein-blue",
    },
    {
        "id": "lib-gold-prestige",
        "name": "Gold Prestige",
        "zh": "奢华黄金",
        "category": "corporate",
        "bg": "#fafaf9", "text": "#0c0a09", "accent": "#a16207", "muted": "#78716c",
        "font_zh": "思源宋体", "font_en": "IBM Plex Sans",
        "mood": "奢华 · 传承 · 金融精英",
        "lock": "editorial",
    },
    {
        "id": "lib-teal-esg",
        "name": "Teal ESG",
        "zh": "绿色可持续",
        "category": "corporate",
        "bg": "#f0fdfa", "text": "#134e4a", "accent": "#0f766e", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "ESG · 可持续 · 企业责任",
        "lock": "swiss-klein-blue",
    },
    {
        "id": "lib-cobalt-report",
        "name": "Cobalt Report",
        "zh": "钴蓝报告",
        "category": "corporate",
        "bg": "#f8fafc", "text": "#1e3a8a", "accent": "#3b82f6", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "数据驱动 · 分析洞察 · 报告感",
        "lock": "academic",
    },
    {
        "id": "lib-analytics-amber",
        "name": "Analytics Amber",
        "zh": "分析琥珀",
        "category": "corporate",
        "bg": "#f8fafc", "text": "#1e3a8a", "accent": "#d97706", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "蓝金互补 · 数据亮点 · 仪表盘感",
        "lock": "academic",
    },
    # ── 科技工程 tech (10) ──────────────────────────────────────────────────
    {
        "id": "lib-engineering-dark",
        "name": "Engineering Dark",
        "zh": "工程深色",
        "category": "tech",
        "bg": "#08090a", "text": "#f7f8f8", "accent": "#5e6ad2", "muted": "#8a8f98",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "工程精密 · 现代科技 · 暗色",
        "lock": "linear-dark",
    },
    {
        "id": "lib-deep-ocean",
        "name": "Deep Ocean",
        "zh": "深海科技",
        "category": "tech",
        "bg": "#0b1527", "text": "#c8d5e8", "accent": "#5E6AD2", "muted": "#7a8ba0",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "工程感 · AI 科技 · 沉浸深蓝",
        "lock": "linear-dark",
    },
    {
        "id": "lib-nebula-purple",
        "name": "Nebula Purple",
        "zh": "星云紫境",
        "category": "tech",
        "bg": "#0a0a0f", "text": "#EDEDEF", "accent": "#7C3AED", "muted": "#8A8F98",
        "font_zh": "思源黑体", "font_en": "Plus Jakarta Sans",
        "mood": "AI 未来感 · 沉浸感强 · 视觉冲击",
        "lock": "linear-dark",
    },
    {
        "id": "lib-matrix-green",
        "name": "Matrix Green",
        "zh": "绿色矩阵",
        "category": "tech",
        "bg": "#0a0f0d", "text": "#d4f0e4", "accent": "#10b981", "muted": "#52796f",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "Terminal 感 · 代码美学 · 生物科技",
        "lock": "linear-dark",
    },
    {
        "id": "lib-midnight-teal",
        "name": "Midnight Teal",
        "zh": "午夜青色",
        "category": "tech",
        "bg": "#050e12", "text": "#cceeff", "accent": "#0891b2", "muted": "#5a8fa0",
        "font_zh": "思源黑体", "font_en": "Plus Jakarta Sans",
        "mood": "沉静科技感 · 数据可视化 · 深色清凉",
        "lock": "linear-dark",
    },
    {
        "id": "lib-saas-blue",
        "name": "SaaS Blue",
        "zh": "SaaS 蓝",
        "category": "tech",
        "bg": "#f8fafc", "text": "#1e293b", "accent": "#2563eb", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "信任蓝 · SaaS 产品感 · 简洁明快",
        "lock": "swiss-klein-blue",
    },
    {
        "id": "lib-indigo-product",
        "name": "Indigo Product",
        "zh": "靛蓝产品",
        "category": "tech",
        "bg": "#f5f3ff", "text": "#1e1b4b", "accent": "#6366f1", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "Micro SaaS · 灵动 · 现代感",
        "lock": "swiss-klein-blue",
    },
    {
        "id": "lib-violet-ai",
        "name": "Violet AI",
        "zh": "紫罗兰 AI",
        "category": "tech",
        "bg": "#faf5ff", "text": "#1e1b4b", "accent": "#7c3aed", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Plus Jakarta Sans",
        "mood": "AI 智能 · 创新 · 未来感",
        "lock": "linear-dark",
    },
    {
        "id": "lib-dark-fintech",
        "name": "Fintech Dark Gold",
        "zh": "金融科技暗金",
        "category": "tech",
        "bg": "#0f172a", "text": "#f8fafc", "accent": "#f59e0b", "muted": "#94a3b8",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "加密 · 价值 · 金融科技暗色",
        "lock": "linear-dark",
    },
    {
        "id": "lib-teal-platform",
        "name": "Teal Platform",
        "zh": "青绿平台",
        "category": "tech",
        "bg": "#f0fdfa", "text": "#134e4a", "accent": "#0d9488", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "协作平台 · 效率工具 · 清爽",
        "lock": "swiss-klein-blue",
    },
    # ── 学术研究 academic (10) ──────────────────────────────────────────────
    {
        "id": "lib-academic-indigo",
        "name": "Academic Indigo",
        "zh": "靛蓝学术",
        "category": "academic",
        "bg": "#f1f3f5", "text": "#0a1f3d", "accent": "#0a1f3d", "muted": "#4a6080",
        "font_zh": "思源宋体", "font_en": "IBM Plex Sans",
        "mood": "冷调学术 · 信息密度高 · 研究感",
        "lock": "academic",
    },
    {
        "id": "lib-prussian-research",
        "name": "Prussian Research",
        "zh": "普鲁士蓝研究",
        "category": "academic",
        "bg": "#eef2ff", "text": "#1e3a5f", "accent": "#1e40af", "muted": "#64748b",
        "font_zh": "思源宋体", "font_en": "IBM Plex Sans",
        "mood": "学术蓝 · 严谨 · 高校报告感",
        "lock": "academic",
    },
    {
        "id": "lib-ink-scholar",
        "name": "Ink Scholar",
        "zh": "墨水学者",
        "category": "academic",
        "bg": "#f8f8f6", "text": "#1a1a2e", "accent": "#16213e", "muted": "#6b7280",
        "font_zh": "思源宋体", "font_en": "IBM Plex Sans",
        "mood": "黑白学术 · 极简严肃 · 论文感",
        "lock": "academic",
    },
    {
        "id": "lib-arctic-study",
        "name": "Arctic Study",
        "zh": "北极研究蓝",
        "category": "academic",
        "bg": "#f0f4f8", "text": "#0a2540", "accent": "#1a4480", "muted": "#52748c",
        "font_zh": "思源黑体", "font_en": "IBM Plex Sans",
        "mood": "冷静 · 系统感 · 国际学术机构",
        "lock": "academic",
    },
    {
        "id": "lib-slate-academic",
        "name": "Slate Academic",
        "zh": "板岩学术",
        "category": "academic",
        "bg": "#f4f6f8", "text": "#1e293b", "accent": "#475569", "muted": "#94a3b8",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "低调专业 · 数据报告 · 中性学术",
        "lock": "academic",
    },
    {
        "id": "lib-sky-research",
        "name": "Sky Research",
        "zh": "晴空研究",
        "category": "academic",
        "bg": "#f0f9ff", "text": "#0c4a6e", "accent": "#0369a1", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "IBM Plex Sans",
        "mood": "知识库 · 文档化 · 清晰有序",
        "lock": "academic",
    },
    {
        "id": "lib-emerald-science",
        "name": "Emerald Science",
        "zh": "翡翠科学",
        "category": "academic",
        "bg": "#ecfdf5", "text": "#064e3b", "accent": "#059669", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "生命科学 · 环境研究 · 健康数据",
        "lock": "academic",
    },
    {
        "id": "lib-indigo-edu",
        "name": "Indigo Education",
        "zh": "靛蓝教育",
        "category": "academic",
        "bg": "#eef2ff", "text": "#1e1b4b", "accent": "#4f46e5", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "教育平台 · 课程讲义 · 互动感",
        "lock": "academic",
    },
    {
        "id": "lib-burgundy-academic",
        "name": "Burgundy Academic",
        "zh": "勃艮第学院",
        "category": "academic",
        "bg": "#fafaf9", "text": "#1c0a0a", "accent": "#881337", "muted": "#6b7280",
        "font_zh": "思源宋体", "font_en": "IBM Plex Sans",
        "mood": "人文 · 法学 · 历史学术感",
        "lock": "academic",
    },
    {
        "id": "lib-cyan-health",
        "name": "Cyan Health",
        "zh": "青色医疗",
        "category": "academic",
        "bg": "#ecfeff", "text": "#164e63", "accent": "#0891b2", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "医疗健康 · 科学 · 冷静专业",
        "lock": "academic",
    },
    # ── 叙事温暖 narrative (10) ─────────────────────────────────────────────
    {
        "id": "lib-warm-paper",
        "name": "Warm Paper",
        "zh": "暖纸叙事",
        "category": "narrative",
        "bg": "#f1efea", "text": "#0a0a0b", "accent": "#0a0a0b", "muted": "#5a5650",
        "font_zh": "思源宋体", "font_en": "IBM Plex Sans",
        "mood": "叙事 · 温暖纸感 · 编辑感",
        "lock": "editorial",
    },
    {
        "id": "lib-sand-editorial",
        "name": "Sand Editorial",
        "zh": "沙色编辑",
        "category": "narrative",
        "bg": "#f5f0e8", "text": "#1a1208", "accent": "#6b4c11", "muted": "#7a6a54",
        "font_zh": "思源宋体", "font_en": "IBM Plex Sans",
        "mood": "自然 · 手工质感 · 策略报告",
        "lock": "editorial",
    },
    {
        "id": "lib-terracotta",
        "name": "Terracotta Story",
        "zh": "陶土叙事",
        "category": "narrative",
        "bg": "#faf3ed", "text": "#2d1b0e", "accent": "#b5533c", "muted": "#8b6355",
        "font_zh": "思源宋体", "font_en": "Plus Jakarta Sans",
        "mood": "温暖品牌 · 文化创意 · 有温度",
        "lock": "editorial",
    },
    {
        "id": "lib-cream-literary",
        "name": "Cream Literary",
        "zh": "奶油文学",
        "category": "narrative",
        "bg": "#fdf8f0", "text": "#2c2416", "accent": "#8b6914", "muted": "#9a8870",
        "font_zh": "思源宋体", "font_en": "IBM Plex Sans",
        "mood": "文学感 · 人文气质 · 课程讲义",
        "lock": "editorial",
    },
    {
        "id": "lib-forest-narrative",
        "name": "Forest Narrative",
        "zh": "森林叙事",
        "category": "narrative",
        "bg": "#f2f4f0", "text": "#1a2618", "accent": "#2d5a27", "muted": "#6b7c68",
        "font_zh": "思源宋体", "font_en": "Plus Jakarta Sans",
        "mood": "自然 · 可持续 · ESG 报告",
        "lock": "editorial",
    },
    {
        "id": "lib-pitch-orange",
        "name": "Pitch Orange",
        "zh": "橙色路演",
        "category": "narrative",
        "bg": "#fff7ed", "text": "#1c1917", "accent": "#ea580c", "muted": "#78716c",
        "font_zh": "思源宋体", "font_en": "Plus Jakarta Sans",
        "mood": "创业路演 · 紧迫感 · 行动力",
        "lock": "editorial",
    },
    {
        "id": "lib-rose-culture",
        "name": "Rose Culture",
        "zh": "玫瑰文化",
        "category": "narrative",
        "bg": "#fdf2f8", "text": "#831843", "accent": "#be185d", "muted": "#6b7280",
        "font_zh": "思源宋体", "font_en": "Plus Jakarta Sans",
        "mood": "创意品牌 · 文化活力 · 视觉吸引",
        "lock": "editorial",
    },
    {
        "id": "lib-ocean-brand",
        "name": "Ocean Brand",
        "zh": "海洋品牌",
        "category": "narrative",
        "bg": "#f0f9ff", "text": "#0c4a6e", "accent": "#0ea5e9", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Plus Jakarta Sans",
        "mood": "旅行 · 生活方式 · 清新开阔",
        "lock": "editorial",
    },
    {
        "id": "lib-dusk-editorial",
        "name": "Dusk Editorial",
        "zh": "黄昏编辑",
        "category": "narrative",
        "bg": "#fdf4ff", "text": "#2e1065", "accent": "#7e22ce", "muted": "#6b7280",
        "font_zh": "思源宋体", "font_en": "IBM Plex Sans",
        "mood": "文化媒体 · 深度思考 · 创意观点",
        "lock": "editorial",
    },
    {
        "id": "lib-midnight-manifesto",
        "name": "Midnight Manifesto",
        "zh": "午夜宣言",
        "category": "narrative",
        "bg": "#0f0f23", "text": "#f8fafc", "accent": "#e2e8f0", "muted": "#94a3b8",
        "font_zh": "思源宋体", "font_en": "IBM Plex Sans",
        "mood": "领导力 · 观点声明 · 思想影响",
        "lock": "linear-dark",
    },
    # ── 极简文档 minimal (10) ───────────────────────────────────────────────
    {
        "id": "lib-notion-classic",
        "name": "Notion Classic",
        "zh": "Notion 经典",
        "category": "minimal",
        "bg": "#ffffff", "text": "#0d0d0d", "accent": "#37352f", "muted": "#615d59",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "亲和 · 极简 · 文档感",
        "lock": "notion-warm",
    },
    {
        "id": "lib-soft-linen",
        "name": "Soft Linen",
        "zh": "亚麻极简",
        "category": "minimal",
        "bg": "#fafaf8", "text": "#1a1a1a", "accent": "#2d2d2d", "muted": "#737373",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "柔和 · 无压感 · 内部汇报",
        "lock": "notion-warm",
    },
    {
        "id": "lib-warm-minimal",
        "name": "Warm Minimal",
        "zh": "温白极简",
        "category": "minimal",
        "bg": "#fffef9", "text": "#111111", "accent": "#44403c", "muted": "#78716c",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "温暖白底 · 轻量演示 · 文化类",
        "lock": "notion-warm",
    },
    {
        "id": "lib-paper-light",
        "name": "Paper Light",
        "zh": "纸光极简",
        "category": "minimal",
        "bg": "#f9f9f7", "text": "#1c1c1c", "accent": "#404040", "muted": "#888888",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "轻盈 · 高可读性 · 课程讲义",
        "lock": "notion-warm",
    },
    {
        "id": "lib-cloud-white",
        "name": "Cloud White",
        "zh": "云白",
        "category": "minimal",
        "bg": "#f7f8fa", "text": "#1a1d23", "accent": "#343a40", "muted": "#868e96",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "清爽 · 科技文档 · 产品说明",
        "lock": "notion-warm",
    },
    {
        "id": "lib-pure-white",
        "name": "Pure White",
        "zh": "纯白极简",
        "category": "minimal",
        "bg": "#ffffff", "text": "#09090b", "accent": "#18181b", "muted": "#71717a",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "极简 · 专注 · 无干扰",
        "lock": "notion-warm",
    },
    {
        "id": "lib-warm-oat",
        "name": "Warm Oat",
        "zh": "温暖燕麦",
        "category": "minimal",
        "bg": "#fef9f3", "text": "#1c1917", "accent": "#92400e", "muted": "#78716c",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "温和 · 人性化 · HR 内部文档",
        "lock": "notion-warm",
    },
    {
        "id": "lib-steel-tech",
        "name": "Steel Tech",
        "zh": "钢铁科技",
        "category": "minimal",
        "bg": "#f9fafb", "text": "#111827", "accent": "#2563eb", "muted": "#9ca3af",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "产品文档 · 工程规范 · 技术说明",
        "lock": "notion-warm",
    },
    {
        "id": "lib-design-system",
        "name": "Design System",
        "zh": "设计系统",
        "category": "minimal",
        "bg": "#eef2ff", "text": "#312e81", "accent": "#4f46e5", "muted": "#64748b",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "产品设计 · 组件库 · 规范文档",
        "lock": "notion-warm",
    },
    {
        "id": "lib-cement-modern",
        "name": "Cement Modern",
        "zh": "水泥现代",
        "category": "minimal",
        "bg": "#f5f4f0", "text": "#1a1a1a", "accent": "#2563eb", "muted": "#9ca3af",
        "font_zh": "思源黑体", "font_en": "Inter",
        "mood": "建筑感 · 设计师 · 都市现代",
        "lock": "notion-warm",
    },
]

CATEGORY_LABELS = {
    "all":       "全部",
    "corporate": "企业权威",
    "tech":      "科技工程",
    "academic":  "学术研究",
    "narrative": "叙事温暖",
    "minimal":   "极简文档",
}

# ── HTML template ────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>Step 4 — 配色方案</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#eceae6;min-height:100vh;padding:28px 24px 56px;color:#1a1a1a}
h1{font-size:20px;font-weight:700;color:#111;margin-bottom:4px}
.subtitle{font-size:13px;color:#666;margin-bottom:4px;line-height:1.5}
.industry-tag{display:inline-block;font-size:11px;font-weight:600;background:#1e293b;color:#e2e8f0;padding:3px 10px;border-radius:12px;margin-bottom:20px}
.section-title{font-size:13px;font-weight:700;color:#555;letter-spacing:.5px;text-transform:uppercase;margin-bottom:14px;display:flex;align-items:center;gap:10px}
.section-title::after{content:"";flex:1;height:1px;background:#d0ccc8}

/* Category filter */
.filter-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}
.filter-btn{padding:6px 14px;border-radius:20px;border:1.5px solid #ccc;background:white;font-size:12px;font-weight:600;color:#555;cursor:pointer;transition:all .15s}
.filter-btn:hover{border-color:#888;color:#222}
.filter-btn.active{background:#0061FF;border-color:#0061FF;color:white}

/* Palette grid */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;margin-bottom:24px}

/* Palette card */
.pcard{background:white;border-radius:10px;overflow:hidden;cursor:pointer;transition:box-shadow .18s,transform .18s;border:2px solid transparent;user-select:none}
.pcard:hover{box-shadow:0 4px 18px rgba(0,0,0,.13);transform:translateY(-2px)}
.pcard.selected{border-color:#0061FF;box-shadow:0 0 0 3px rgba(0,97,255,.12),0 4px 18px rgba(0,0,0,.1);transform:translateY(-2px)}
.pcard.hidden{display:none}

/* Mini slide */
.slide-wrap{width:100%;aspect-ratio:16/9;overflow:hidden}

/* Swatches */
.swatches{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:#eee;border-top:1px solid #eee;border-bottom:1px solid #eee}
.sw{display:flex;align-items:center;gap:7px;padding:6px 10px;background:white}
.sw-dot{width:18px;height:18px;border-radius:4px;flex-shrink:0;border:1px solid rgba(0,0,0,.08)}
.sw-role{font-size:8.5px;color:#999;text-transform:uppercase;letter-spacing:.4px}
.sw-hex{font-size:10.5px;font-weight:600;color:#333;font-family:monospace}

/* Meta */
.meta{padding:10px 12px 12px}
.pname{font-size:13px;font-weight:700;color:#111;margin-bottom:1px}
.pzh{font-size:11px;color:#888;margin-bottom:5px}
.pmood{font-size:10.5px;color:#444;line-height:1.5;border-left:2px solid #ddd;padding-left:7px;margin-bottom:7px}
.plock{font-size:10px;color:#0061FF;font-weight:600;background:#EEF3FF;padding:2px 8px;border-radius:10px;display:inline-block}
.sel-btn{display:block;width:calc(100% - 24px);margin:0 12px 12px;padding:8px;background:#f4f4f2;border:1px solid #ddd;border-radius:6px;font-size:11.5px;font-weight:600;color:#333;cursor:pointer;text-align:center;transition:background .12s}
.sel-btn:hover{background:#eaeae8}
.pcard.selected .sel-btn{background:#0061FF;color:white;border-color:#0061FF}

/* Industry match badge */
.industry-match{font-size:9.5px;font-weight:700;background:#dcfce7;color:#166534;padding:2px 7px;border-radius:10px;display:inline-block;margin-bottom:4px}

/* Showcase drawer — slides up from bottom on selection */
body{padding-bottom:260px}
.showcase{position:fixed;bottom:0;left:0;right:0;background:white;border-top:1.5px solid #e0ddd8;box-shadow:0 -6px 32px rgba(0,0,0,.13);padding:16px 24px 18px;transform:translateY(calc(100% + 10px));transition:transform .32s cubic-bezier(.4,0,.2,1);z-index:100}
.showcase.visible{transform:translateY(0)}
.sc-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.sc-title{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.sc-name{font-size:15px;font-weight:700;color:#111}
.sc-zh{font-size:12px;color:#888}
.sc-mood{font-size:11px;color:#444;border-left:2px solid #ddd;padding-left:8px;margin-left:4px}
.sc-close{width:28px;height:28px;border:none;background:#f0f0ee;border-radius:50%;font-size:16px;cursor:pointer;color:#555;flex-shrink:0}
.sc-slides{display:flex;gap:14px;margin-bottom:12px}
.sc-col{flex:1;min-width:0}
.sc-label{font-size:10px;font-weight:600;color:#888;letter-spacing:.5px;text-transform:uppercase;margin-bottom:5px}
.sc-frame{width:100%;aspect-ratio:16/9;overflow:hidden;border-radius:7px;box-shadow:0 3px 14px rgba(0,0,0,.14)}
.sc-bottom{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.sc-swatches{display:flex;gap:10px;flex:1;flex-wrap:wrap}
.sc-sw{display:flex;align-items:center;gap:6px}
.sc-dot{width:22px;height:22px;border-radius:5px;border:1px solid rgba(0,0,0,.09);flex-shrink:0}
.sc-swatch-info .sc-hex{font-size:10.5px;font-weight:600;color:#333;font-family:monospace}
.sc-swatch-info .sc-role{font-size:8.5px;color:#888;text-transform:uppercase;letter-spacing:.4px}

/* Confirm */
.cbtn{padding:12px 30px;background:#0061FF;color:white;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;transition:background .15s,transform .1s;box-shadow:0 2px 10px rgba(0,97,255,.3)}
.cbtn:hover{background:#004ee0;transform:translateY(-1px)}
.cbtn.done{background:#16a34a;cursor:default;transform:none;box-shadow:none}
.cmsg{display:none;font-size:13px;color:#16a34a;font-weight:600;padding:10px 14px;background:#f0fdf4;border-radius:8px;border:1px solid #bbf7d0;line-height:1.5}
.cmsg.show{display:block}
</style>
</head>
<body>
<h1>Step 4 — 配色方案选择</h1>
<p class="subtitle">点击任意配色卡片预览真实效果，选好后点「确认此配色方案」，选择自动复制到剪贴板。</p>
<div id="industry-display"></div>

<div id="recommended-section"></div>

<div class="section-title" id="library-title">配色库 — 50 套精选方案</div>
<div class="filter-row" id="filter-row"></div>
<div class="grid" id="library-grid"></div>

<!-- Showcase drawer: slides up when a palette is selected -->
<div class="showcase" id="showcase">
  <div class="sc-header">
    <div class="sc-title">
      <span class="sc-name" id="sc-name"></span>
      <span class="sc-zh" id="sc-zh"></span>
      <span class="sc-mood" id="sc-mood"></span>
    </div>
    <button class="sc-close" onclick="closeShowcase()">×</button>
  </div>
  <div class="sc-slides">
    <div class="sc-col">
      <div class="sc-label">封面</div>
      <div class="sc-frame" id="sc-cover"></div>
    </div>
    <div class="sc-col">
      <div class="sc-label">内页</div>
      <div class="sc-frame" id="sc-content"></div>
    </div>
  </div>
  <div class="sc-bottom">
    <div class="sc-swatches" id="sc-swatches"></div>
    <button class="cbtn" id="cbtn" onclick="confirm_()">确认此配色方案 →</button>
    <div class="cmsg" id="cmsg">✓ 已复制！粘贴到 Claude 继续 Step 5。</div>
  </div>
</div>

<script>
const RECOMMENDED = RECOMMENDED_JSON;
const LIBRARY = LIBRARY_JSON;
const DECK_INDUSTRY = DECK_INDUSTRY_JSON;

const CATS = {all:"全部",corporate:"企业权威",tech:"科技工程",academic:"学术研究",narrative:"叙事温暖",minimal:"极简文档"};
let activeCat = "all";
let selectedId = null;

const FONT_MAP = {"思源黑体":"'Noto Sans SC'","思源宋体":"'Noto Serif SC'","黑体":"'Noto Sans SC'","宋体":"'Noto Serif SC'"};
function fontStack(zh,en){return`${FONT_MAP[zh]||"'Noto Sans SC'"}, '${en}', sans-serif`}

function isDark(hex){
  const r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16);
  return(r*299+g*587+b*114)/1000<128;
}
function blend(hex,with_,amt){
  const r1=parseInt(hex.slice(1,3),16),g1=parseInt(hex.slice(3,5),16),b1=parseInt(hex.slice(5,7),16);
  const r2=parseInt(with_.slice(1,3),16),g2=parseInt(with_.slice(3,5),16),b2=parseInt(with_.slice(5,7),16);
  return`rgb(${Math.round(r1*(1-amt)+r2*amt)},${Math.round(g1*(1-amt)+g2*amt)},${Math.round(b1*(1-amt)+b2*amt)})`;
}

function slideHtml(p){
  const fs=fontStack(p.font_zh,p.font_en);
  const cardBg=blend(p.bg,isDark(p.bg)?'#ffffff':'#000000',0.07);
  return`<div style="width:100%;height:100%;background:${p.bg};padding:12px 16px;display:flex;flex-direction:column;font-family:${fs};">
  <div style="width:24px;height:2.5px;background:${p.accent};margin-bottom:9px;"></div>
  <div style="font-size:7px;font-weight:700;color:${p.accent};letter-spacing:1.5px;text-transform:uppercase;margin-bottom:5px;">SECTION 02</div>
  <div style="font-size:12px;font-weight:800;color:${p.text};line-height:1.25;margin-bottom:9px;">核心竞争力分析<br>市场份额提升 34%</div>
  <div style="height:1.5px;background:${p.accent};width:28px;margin-bottom:9px;opacity:.5;"></div>
  <div style="display:flex;gap:6px;flex:1;">
    <div style="flex:1;background:${cardBg};border-radius:3px;padding:7px;">
      <div style="font-size:6.5px;font-weight:700;color:${p.accent};margin-bottom:3px;">核心指标</div>
      <div style="font-size:6px;color:${p.text};line-height:1.6;opacity:.85;">增长率 +34%<br>市占率 28%</div>
    </div>
    <div style="flex:1;background:${cardBg};border-radius:3px;padding:7px;">
      <div style="font-size:6.5px;font-weight:700;color:${p.accent};margin-bottom:3px;">趋势</div>
      <div style="font-size:6px;color:${p.text};line-height:1.6;opacity:.85;">持续上升<br>Q4 加速</div>
    </div>
  </div>
  <div style="margin-top:7px;font-size:6px;color:${p.muted};display:flex;justify-content:space-between;"><span>IDC 2024</span><span>03/12</span></div>
</div>`;
}

function cardHtml(p, badge, matchLabel){
  const sel = p.id === selectedId;
  return`<div class="pcard${sel?' selected':''}" data-id="${p.id}" onclick="select_('${p.id}')">
  <div class="slide-wrap">${slideHtml(p)}</div>
  <div class="swatches">
    <div class="sw"><div class="sw-dot" style="background:${p.bg}"></div><div><div class="sw-role">背景</div><div class="sw-hex">${p.bg}</div></div></div>
    <div class="sw"><div class="sw-dot" style="background:${p.text}"></div><div><div class="sw-role">正文</div><div class="sw-hex">${p.text}</div></div></div>
    <div class="sw"><div class="sw-dot" style="background:${p.accent}"></div><div><div class="sw-role">强调</div><div class="sw-hex">${p.accent}</div></div></div>
    <div class="sw"><div class="sw-dot" style="background:${p.muted}"></div><div><div class="sw-role">辅助</div><div class="sw-hex">${p.muted}</div></div></div>
  </div>
  <div class="meta">
    ${badge?`<div style="font-size:10px;font-weight:700;background:#FFF3CD;color:#856404;padding:2px 8px;border-radius:10px;display:inline-block;margin-bottom:5px;">✦ Claude 推荐 · 方案 ${badge}</div>`:''}
    ${matchLabel?`<div class="industry-match">▲ 行业匹配</div>`:''}
    <div class="pname">${p.name}</div>
    <div class="pzh">${p.zh||''}</div>
    <div class="pmood">${p.mood}</div>
    <div class="plock">→ ${p.lock}</div>
  </div>
  <button class="sel-btn" onclick="event.stopPropagation();select_('${p.id}')">${sel?'✓ 已选择':'选择此配色'}</button>
</div>`;
}

function renderIndustry(){
  const el=document.getElementById('industry-display');
  if(DECK_INDUSTRY){
    el.innerHTML=`<span class="industry-tag">行业：${DECK_INDUSTRY}</span>`;
  }
}

function renderRecommended(){
  const el = document.getElementById('recommended-section');
  if(!RECOMMENDED||!RECOMMENDED.length){el.innerHTML='';return;}
  const labels=['A','B','C','D'];
  const header=DECK_INDUSTRY
    ?`<div class="section-title">Claude 推荐（基于行业：${DECK_INDUSTRY}）</div>`
    :`<div class="section-title">Claude 推荐</div>`;
  el.innerHTML=`${header}
  <div class="grid">${RECOMMENDED.map((p,i)=>cardHtml(p,labels[i]||String(i+1),false)).join('')}</div>
  <div class="section-title" style="margin-top:8px;">或从配色库中自由选择</div>`;
}

function renderFilters(){
  document.getElementById('filter-row').innerHTML=
    Object.entries(CATS).map(([k,v])=>
      `<button class="filter-btn${k===activeCat?' active':''}" onclick="setFilter('${k}')">${v}</button>`
    ).join('');
}

function isIndustryMatch(p){
  if(!DECK_INDUSTRY||!p.industries) return false;
  return p.industries.some(i=>i.toLowerCase()===DECK_INDUSTRY.toLowerCase());
}

function renderLibrary(){
  document.getElementById('library-grid').innerHTML=
    LIBRARY.map(p=>{
      const hidden=(activeCat!=='all'&&p.category!==activeCat);
      const match=isIndustryMatch(p);
      return`<div class="pcard${p.id===selectedId?' selected':''}${hidden?' hidden':''}" data-id="${p.id}" onclick="select_('${p.id}')">
  <div class="slide-wrap">${slideHtml(p)}</div>
  <div class="swatches">
    <div class="sw"><div class="sw-dot" style="background:${p.bg}"></div><div><div class="sw-role">背景</div><div class="sw-hex">${p.bg}</div></div></div>
    <div class="sw"><div class="sw-dot" style="background:${p.text}"></div><div><div class="sw-role">正文</div><div class="sw-hex">${p.text}</div></div></div>
    <div class="sw"><div class="sw-dot" style="background:${p.accent}"></div><div><div class="sw-role">强调</div><div class="sw-hex">${p.accent}</div></div></div>
    <div class="sw"><div class="sw-dot" style="background:${p.muted}"></div><div><div class="sw-role">辅助</div><div class="sw-hex">${p.muted}</div></div></div>
  </div>
  <div class="meta">
    ${match?'<div class="industry-match">▲ 行业匹配</div>':''}
    <div class="pname">${p.name}</div>
    <div class="pzh">${p.zh}</div>
    <div class="pmood">${p.mood}</div>
    <div class="plock">→ ${p.lock}</div>
  </div>
  <button class="sel-btn" onclick="event.stopPropagation();select_('${p.id}')">${p.id===selectedId?'✓ 已选择':'选择此配色'}</button>
</div>`;
    }).join('');
}

function setFilter(cat){activeCat=cat;renderFilters();renderLibrary();}

function coverSlideHtml(p){
  const fs=fontStack(p.font_zh,p.font_en);
  return`<div style="width:100%;height:100%;background:${p.bg};padding:18px 24px;display:flex;flex-direction:column;justify-content:space-between;font-family:${fs};">
  <div style="font-size:8px;font-weight:700;color:${p.accent};letter-spacing:2px;text-transform:uppercase;">REPORT · 2024</div>
  <div>
    <div style="width:36px;height:3px;background:${p.accent};margin-bottom:12px;"></div>
    <div style="font-size:18px;font-weight:800;color:${p.text};line-height:1.2;margin-bottom:10px;">AI 基础设施<br>行业全景报告</div>
    <div style="font-size:9px;color:${p.muted};">中国产业研究院 · 2024.Q4</div>
  </div>
  <div style="font-size:7.5px;color:${p.muted};">01 / 18</div>
</div>`;
}

function updateShowcase(p){
  document.getElementById('sc-name').textContent=p.name;
  document.getElementById('sc-zh').textContent=p.zh||'';
  document.getElementById('sc-mood').textContent=p.mood;
  document.getElementById('sc-cover').innerHTML=coverSlideHtml(p);
  document.getElementById('sc-content').innerHTML=slideHtml(p);
  document.getElementById('sc-swatches').innerHTML=
    [['背景',p.bg],['正文',p.text],['强调',p.accent],['辅助',p.muted]]
    .map(([role,hex])=>`<div class="sc-sw">
      <div class="sc-dot" style="background:${hex}"></div>
      <div class="sc-swatch-info"><div class="sc-role">${role}</div><div class="sc-hex">${hex}</div></div>
    </div>`).join('');
  document.getElementById('showcase').classList.add('visible');
  document.getElementById('cbtn').textContent='确认此配色方案 →';
  document.getElementById('cbtn').classList.remove('done');
  document.getElementById('cmsg').classList.remove('show');
}

function closeShowcase(){
  document.getElementById('showcase').classList.remove('visible');
}

function select_(id){
  selectedId=id;
  const all=[...(RECOMMENDED||[]),...LIBRARY];
  const p=all.find(x=>x.id===id);
  renderRecommended();
  renderLibrary();
  updateShowcase(p);
}

function confirm_(){
  if(!selectedId){alert('请先选择一个配色方案');return;}
  const all=[...(RECOMMENDED||[]),...LIBRARY];
  const p=all.find(x=>x.id===selectedId);
  const text=`我选择配色方案：${p.name}（${p.zh||p.id}）`;
  fetch('/confirmed',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id:p.id,name:p.name,zh:p.zh||'',text:text})
  }).then(r=>r.ok?r:Promise.reject()).then(()=>{
    document.getElementById('cbtn').textContent='✓ 已发送至 Claude';
    document.getElementById('cbtn').classList.add('done');
    document.getElementById('cmsg').textContent='✓ 选择已自动发送，Claude 即将继续。';
    document.getElementById('cmsg').classList.add('show');
  }).catch(()=>{
    navigator.clipboard.writeText(text).then(()=>{
      document.getElementById('cbtn').textContent='✓ 已复制（请粘贴到 Claude）';
      document.getElementById('cbtn').classList.add('done');
      document.getElementById('cmsg').classList.add('show');
    });
  });
}

renderIndustry();
renderRecommended();
renderFilters();
renderLibrary();
</script>
</body>
</html>"""


_PALETTE_PORT = 7531
_SEL_FILE = Path("/tmp/deck-palette-selection.json")


class _PaletteHandler(http.server.BaseHTTPRequestHandler):
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
                _PaletteHandler.result = json.loads(body)
            except Exception:
                pass
            threading.Thread(target=_PaletteHandler.done.set, daemon=True).start()
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

    palette_json = assets_dir / "palettes.json"
    recommended: list = []
    deck_industry: str = ""

    if palette_json.exists():
        try:
            raw = json.loads(palette_json.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                recommended = raw
            elif isinstance(raw, dict):
                recommended = raw.get("palettes", [])
                deck_industry = raw.get("deck_industry", "")
        except Exception:
            pass

    html_content = (HTML
                    .replace("RECOMMENDED_JSON", json.dumps(recommended, ensure_ascii=False))
                    .replace("LIBRARY_JSON", json.dumps(PALETTE_LIBRARY, ensure_ascii=False))
                    .replace("DECK_INDUSTRY_JSON", json.dumps(deck_industry, ensure_ascii=False)))

    # Write static fallback file
    out = assets_dir / "palette-preview.html"
    out.write_text(html_content, encoding="utf-8")

    # Find an available port starting from _PALETTE_PORT
    port = _PALETTE_PORT
    for _ in range(20):
        with socket.socket() as sock:
            if sock.connect_ex(('localhost', port)) != 0:
                break
            port += 1

    _PaletteHandler.html = html_content
    _PaletteHandler.done.clear()
    _PaletteHandler.result = {}

    httpd = http.server.HTTPServer(('localhost', port), _PaletteHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    url = f"http://localhost:{port}"
    print(f"✓ 配色预览已启动: {url}")
    print(f"  推荐方案: {len(recommended)} 套  |  配色库: {len(PALETTE_LIBRARY)} 套"
          + (f"  |  行业: {deck_industry}" if deck_industry else ""))
    print("  选择配色后点「确认此配色方案」，选择将自动发送给 Claude。")
    sys.stdout.flush()

    webbrowser.open(url)

    _PaletteHandler.done.wait()
    httpd.shutdown()

    sel = _PaletteHandler.result
    _SEL_FILE.write_text(json.dumps(sel, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"DECK_SELECTION_PALETTE: {json.dumps(sel, ensure_ascii=False)}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
