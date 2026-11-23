// Builds an editable PPTX from a deck-spec v1 file that engine/deck_spec.py has already validated.
// Usage: node generate.mjs <spec.json> <out.pptx>
import { readFileSync } from "node:fs";
import pptxgen from "pptxgenjs";

const W = 13.333;
const H = 7.5;
const M = 0.6;
const BODY_W = W - 2 * M;

const hex = (c) => c.replace(/^#/, "").toUpperCase();

function mix(a, b, t) {
  const pa = [0, 2, 4].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [0, 2, 4].map((i) => parseInt(b.slice(i, i + 2), 16));
  return pa.map((v, i) => Math.round(v + (pb[i] - v) * t).toString(16).padStart(2, "0")).join("").toUpperCase();
}

function palette(theme) {
  const bg = hex(theme.background);
  const text = hex(theme.text);
  return {
    bg,
    text,
    accent: hex(theme.accent),
    accent2: hex(theme.accent2),
    muted: mix(text, bg, 0.45),
    card: mix(bg, text, 0.06),
    line: mix(bg, text, 0.15),
    font: theme.font_face,
  };
}

function base(pres, c, lang) {
  return { fontFace: c.font, color: c.text, lang };
}

function addTitle(slide, s, c, t) {
  slide.addText(s.title, { ...t, x: M, y: 0.4, w: BODY_W, h: 0.9, fontSize: 28, bold: true, valign: "bottom", margin: 0 });
  slide.addShape("rect", { x: M, y: 1.38, w: 0.8, h: 0.06, fill: { color: c.accent }, line: { color: c.accent } });
}

function addFooter(slide, deckTitle, n, total, c, t) {
  slide.addText(deckTitle, { ...t, x: M, y: H - 0.5, w: 8, h: 0.3, fontSize: 10, color: c.muted, margin: 0 });
  slide.addText(`${n} / ${total}`, { ...t, x: W - M - 2, y: H - 0.5, w: 2, h: 0.3, fontSize: 10, color: c.muted, align: "right", margin: 0 });
}

function addTakeaway(slide, text, y, c, t) {
  if (!text) return;
  slide.addShape("rect", { x: M, y, w: BODY_W, h: 0.6, fill: { color: c.card }, line: { color: c.card } });
  slide.addShape("rect", { x: M, y, w: 0.08, h: 0.6, fill: { color: c.accent }, line: { color: c.accent } });
  slide.addText(text, { ...t, x: M + 0.3, y, w: BODY_W - 0.4, h: 0.6, fontSize: 16, bold: true, valign: "middle", margin: 0 });
}

function bulletRuns(items, fontSize, t, spaceAfter = 10) {
  return items.map((text) => ({ text, options: { ...t, fontSize, bullet: { indent: 18 }, paraSpaceAfter: spaceAfter, breakLine: true } }));
}

const layouts = {
  cover(slide, s, c, t) {
    slide.addShape("rect", { x: 0, y: 0, w: 0.35, h: H, fill: { color: c.accent }, line: { color: c.accent } });
    slide.addText(s.title, { ...t, x: 1.0, y: 2.2, w: 11.3, h: 1.5, fontSize: 40, bold: true, valign: "bottom", margin: 0 });
    if (s.subtitle) slide.addText(s.subtitle, { ...t, x: 1.0, y: 3.85, w: 11.3, h: 0.7, fontSize: 20, color: c.muted, margin: 0 });
    if (s.footnote) slide.addText(s.footnote, { ...t, x: 1.0, y: 6.3, w: 11.3, h: 0.4, fontSize: 12, color: c.muted, margin: 0 });
  },

  bullets(slide, s, c, t) {
    addTitle(slide, s, c, t);
    slide.addText(bulletRuns(s.bullets, 24, t, 20), { x: M + 0.1, y: 1.9, w: BODY_W - 0.2, h: 4.8, valign: "top", margin: 0 });
  },

  two_column(slide, s, c, t) {
    addTitle(slide, s, c, t);
    const colW = (BODY_W - 0.35) / 2;
    // Card height follows the longer column so short lists do not sit in a mostly empty box.
    const rows = Math.max(s.left.bullets.length, s.right.bullets.length);
    const cardH = Math.min(1.35 + rows * 0.62, 4.8);
    [s.left, s.right].forEach((col, i) => {
      const x = M + i * (colW + 0.35);
      slide.addShape("rect", { x, y: 1.8, w: colW, h: cardH, fill: { color: c.card }, line: { color: c.card } });
      slide.addText(col.heading, { ...t, x: x + 0.35, y: 2.0, w: colW - 0.7, h: 0.6, fontSize: 20, bold: true, color: i === 0 ? c.accent : c.accent2, margin: 0 });
      slide.addText(bulletRuns(col.bullets, 18, t, 12), { x: x + 0.35, y: 2.75, w: colW - 0.7, h: cardH - 1.15, valign: "top", margin: 0 });
    });
  },

  chart(slide, s, c, t, pres) {
    addTitle(slide, s, c, t);
    const ch = s.chart;
    const data = ch.series.map((se) => ({ name: se.name, labels: ch.categories, values: se.values }));
    const type = { bar: pres.charts.BAR, line: pres.charts.LINE, pie: pres.charts.PIE }[ch.type];
    const fmt = ch.unit ? `0"${ch.unit.replace(/"/g, "")}"` : "General";
    const colors = [c.accent, c.accent2, c.muted, c.line];
    const opts = {
      x: M, y: 1.7, w: BODY_W, h: s.takeaway ? 4.45 : 5.1,
      chartColors: ch.type === "pie" ? [c.accent, c.accent2, c.muted, c.line, mix(c.accent, c.bg, 0.5), mix(c.accent2, c.bg, 0.5)] : colors,
      showLegend: ch.type === "pie" || ch.series.length > 1,
      legendPos: ch.type === "pie" ? "r" : "b",
      legendFontFace: c.font, legendFontSize: 14, legendColor: c.text,
      showValue: ch.type !== "pie", showPercent: ch.type === "pie",
      dataLabelFontFace: c.font, dataLabelFontSize: 12, dataLabelColor: c.text, dataLabelFormatCode: fmt,
      catAxisLabelFontFace: c.font, catAxisLabelFontSize: 14, catAxisLabelColor: c.text,
      valAxisLabelFontFace: c.font, valAxisLabelFontSize: 12, valAxisLabelColor: c.muted, valAxisLabelFormatCode: fmt,
      valGridLine: { color: c.line, size: 0.5 }, catGridLine: { style: "none" },
      barGrouping: "clustered", barGapWidthPct: 60,
      lineDataSymbol: "circle", lineDataSymbolSize: 8, lineSize: 3,
    };
    slide.addChart(type, data, opts);
    addTakeaway(slide, s.takeaway, 6.3, c, t);
  },

  table(slide, s, c, t) {
    addTitle(slide, s, c, t);
    const tb = s.table;
    const head = tb.header.map((h) => ({ text: h, options: { ...t, bold: true, color: "FFFFFF", fill: { color: c.accent } } }));
    const body = tb.rows.map((row, r) => row.map((cell) => ({ text: cell, options: { ...t, fill: { color: r % 2 === 0 ? c.bg : c.card } } })));
    const rowH = 0.55;
    slide.addTable([head, ...body], {
      x: M, y: 1.8, w: BODY_W, rowH, fontSize: 15, valign: "middle", margin: [0, 0.12, 0, 0.12],
      border: { type: "solid", pt: 0.5, color: c.line }, autoPage: false,
    });
    const y = Math.min(1.8 + rowH * (tb.rows.length + 1) + 0.35, 6.3);
    addTakeaway(slide, s.takeaway, y, c, t);
  },

  closing(slide, s, c, t) {
    addTitle(slide, s, c, t);
    s.items.forEach((item, i) => {
      const y = 2.0 + i * 0.95;
      slide.addShape("ellipse", { x: M + 0.1, y, w: 0.6, h: 0.6, fill: { color: c.accent }, line: { color: c.accent } });
      slide.addText(String(i + 1), { ...t, x: M + 0.1, y, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
      slide.addText(item, { ...t, x: M + 1.0, y, w: BODY_W - 1.0, h: 0.6, fontSize: 22, valign: "middle", margin: 0 });
    });
  },
};

export async function build(spec, outPath) {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = spec.title;
  pres.lang = spec.language;
  const c = palette(spec.theme);
  const t = base(pres, c, spec.language);
  const total = spec.slides.length;
  spec.slides.forEach((s, i) => {
    const slide = pres.addSlide();
    slide.background = { color: c.bg };
    layouts[s.layout](slide, s, c, t, pres);
    if (s.layout !== "cover") addFooter(slide, spec.title, i + 1, total, c, t);
    if (s.notes) slide.addNotes(s.notes);
  });
  await pres.writeFile({ fileName: outPath, compression: true });
}

if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith("generate.mjs")) {
  const [specPath, outPath] = process.argv.slice(2);
  if (!specPath || !outPath) {
    console.error("usage: node generate.mjs <spec.json> <out.pptx>");
    process.exit(64);
  }
  await build(JSON.parse(readFileSync(specPath, "utf8")), outPath);
  console.log(outPath);
}
