# HTML Theme Catalog

Internalized theme guidance for native Reveal.js decks. This catalog is inspired by the public `lewislulu/html-ppt-skill` project, which advertises a broad theme/layout/animation library, but Presentation Director does not depend on that project at runtime.

## Usage Contract

- Use these keys as prompt guidance for `output_format = html-revealjs` or `both`.
- Do not import external theme files from html-ppt-skill.
- Implement the selected direction as local CSS variables in the generated Reveal.js file.
- PPTX generation ignores `html_config`, `html_motion_level`, `html_motion_profile`, `html_transition`, `html_animation`, and `html_gradient`.

## Theme Keys

| Key | Best For | Visual System |
|-----|----------|---------------|
| `minimal-white` | teaching, clean explainers, internal updates | white background, black text, restrained accent, high readability |
| `editorial-serif` | essays, policy, research narratives | serif headlines, warm off-white paper, narrow measure, quiet rules |
| `swiss-grid` | consulting, structured analysis | visible grid rhythm, strong alignment, compact labels, low decoration |
| `corporate-clean` | executive and business reviews | neutral surfaces, concise KPI blocks, conservative accent use |
| `academic-paper` | science, medical, literature review | citation-friendly layout, restrained color, table and annotation support |
| `blueprint` | architecture, systems, engineering | blue technical grid, thin lines, diagram-first composition |
| `engineering-whiteprint` | architecture on light backgrounds | light grid, dark ink, technical diagrams, readable code snippets |
| `terminal-green` | developer tools, infra, DevOps | dark terminal surface, monospace accents, command/status blocks |
| `pitch-deck-vc` | investor or competition decks | high contrast, big numbers, bold section breaks, short copy |
| `product-launch` | product demos and launches | hero media slots, feature comparison, workflow and adoption visuals |
| `news-broadcast` | sports, market updates, live operations | lower-third labels, scorecard rhythm, large current-state metrics |
| `magazine-bold` | brand storytelling, campaigns | oversized editorial type, image-led sections, strong pacing |
| `aurora` | science/tech talks that need energy | light gradient wash, glow accents, animated emphasis, high contrast text |
| `glassmorphism` | premium product or SaaS demo | translucent panels over subtle background, careful contrast checks |
| `cyberpunk-neon` | dramatic developer/AI demos | dark background, neon accents, use sparingly for short decks |

## Selection Heuristics

- `research` context: prefer `academic-paper`, `editorial-serif`, or `aurora`.
- `engineering` context: prefer `engineering-whiteprint`, `blueprint`, or `terminal-green`.
- `market` / `pitch`: prefer `pitch-deck-vc`, `product-launch`, or `magazine-bold`.
- `sports` / live operations: prefer `news-broadcast`.
- Long source-heavy decks should start from quieter themes; use high-energy themes only for cover, section, and conclusion contrast.

## CSS Token Minimum

Every generated HTML deck should define:

```css
:root {
  --deck-bg: #ffffff;
  --deck-ink: #111827;
  --deck-muted: #64748b;
  --deck-accent: #2563eb;
  --deck-accent-2: #f59e0b;
  --deck-line: rgba(15, 23, 42, .16);
}
```

Then theme-specific sections should consume those tokens rather than hard-coding one-off colors on every slide.
