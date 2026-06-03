# HTML Theme Catalog

Internalized theme guidance for native Reveal.js decks. This catalog is inspired by the public `lewislulu/html-ppt-skill` project, which advertises a broad theme/layout/animation library, but Presentation Director does not depend on that project at runtime.

## Usage Contract

- Use these keys as prompt guidance for `output_format = html-revealjs` or `both`.
- Do not import external theme files from html-ppt-skill.
- Implement the selected direction as local CSS variables in the generated Reveal.js file.
- PPTX generation ignores `html_config`, `html_motion_level`, `html_motion_profile`, `html_transition`, `html_animation`, and `html_gradient`.

## Theme Keys

This is a curated subset of the 36 verified theme keys shipped by `lewislulu/html-ppt-skill` (`assets/themes/*.css`). Each is a CSS-tokens file overriding shared variables (`--bg`, `--accent`, `--accent-2/3`, `--font-display`, etc.). Hex and font values below are read directly from the repo's theme files (verified facts, not copyrightable). Reproduce the *direction* as local Reveal.js CSS variables; do not import the source files.

`Source` legend: `repo` = verified key + tokens in html-ppt-skill; `general` = generic Reveal.js / web design knowledge.

| Key | Best For | Visual System (verified tokens) | Source |
|-----|----------|---------------|--------|
| `minimal-white` | teaching, clean explainers, internal updates | white bg `#ffffff`, near-black ink `#0c0d10`, near-black accent `#111216`, Inter display, very low shadow | repo |
| `editorial-serif` | essays, policy, research narratives | warm paper `#faf7f2`, brick accent `#8a2a1c` / terracotta `#c97a4a`, Playfair Display serif throughout | repo |
| `swiss-grid` | consulting, structured analysis | white bg, signal-red accent `#d6001c`, Helvetica/Inter, strong grid alignment, low decoration | repo |
| `corporate-clean` | executive and business reviews | white bg, navy ink `#0a2540`, royal-blue accent `#1d4ed8`, Inter, conservative borders | repo |
| `academic-paper` | science, medical, literature review | off-white `#fdfcf8`, indigo accent `#1a3a7a` + maroon `#8a1a1a`, serif body (Latin Modern/Playfair), citation-friendly | repo |
| `blueprint` | architecture, systems, engineering | deep blue bg `#0b3a6f`, white/cyan accents, JetBrains Mono, grid texture, diagram-first | repo |
| `engineering-whiteprint` | architecture on light backgrounds | white bg, navy ink `#0a1e46`, blue accent `#1e5ac4` + red `#c42a10`, Mono display over Inter body, graph-paper grid | repo |
| `terminal-green` | developer tools, infra, DevOps | near-black bg `#030a04`, neon-green accent `#00ff88`, JetBrains Mono, glow text | repo |
| `pitch-deck-vc` | investor or competition decks | white bg, blue→purple→pink accents `#0070f3`/`#7928ca`/`#ff4ecb`, Inter, large whitespace | repo |
| `news-broadcast` | sports, market updates, live operations | white bg, broadcast-red accent `#e11d2d` + yellow `#ffd100`, Oswald uppercase display, hard shadow | repo |
| `magazine-bold` | brand storytelling, campaigns | cream bg `#f5efe2`, orange spot `#ea5a1a`, oversized Playfair display over Inter body | repo |
| `aurora` | science/tech talks that need energy | DARK bg `#06091c`, mint/blue/violet glow accents `#5ef2c6`/`#7aa2ff`/`#c984ff`, gradient + blur, high-contrast text | repo |
| `glassmorphism` | premium product or SaaS demo | DARK navy bg `#0b1024`, translucent surfaces (white at low alpha), sky/violet accents `#7dd3fc`/`#c084fc`; verify contrast | repo |
| `cyberpunk-neon` | dramatic developer/AI demos | pure-black bg `#000000`, neon magenta `#ff2bd6` + cyan `#00f0ff` + yellow `#f9f871`, Mono display; use sparingly | repo |

> Note: `product-launch` was previously listed here as a theme. It is **not** a theme in the source repo — it is a full-deck *template* (`templates/full-decks/product-launch/`). For a launch deck, choose a theme (e.g. `glassmorphism`, `aurora`, `pitch-deck-vc`) and apply launch layouts locally.

### Other verified theme keys (repo, not expanded above)

`soft-pastel`, `sharp-mono`, `arctic-cool`, `sunset-warm`, `catppuccin-latte`, `catppuccin-mocha`, `dracula`, `tokyo-night`, `nord`, `solarized-light`, `gruvbox-dark`, `rose-pine`, `neo-brutalism`, `bauhaus`, `xiaohongshu-white`, `rainbow-gradient`, `memphis-pop`, `y2k-chrome`, `retro-tv`, `japanese-minimal`, `vaporwave`, `midcentury`. (Source: repo `assets/themes/*.css`. Reproduce direction locally; do not import.)

## Selection Heuristics

- `research` context: prefer `academic-paper`, `editorial-serif`, or `aurora`.
- `engineering` context: prefer `engineering-whiteprint`, `blueprint`, or `terminal-green`.
- `market` / `pitch`: prefer `pitch-deck-vc` or `magazine-bold` (apply launch *layouts* on top of the theme; there is no `product-launch` theme).
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
