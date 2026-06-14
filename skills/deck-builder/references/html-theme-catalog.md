# HTML Theme Catalog

Theme guidance for Presentation Director HTML decks. The runtime source of truth is the bundled pakco-html copy at `skills/html-deck/pakco-html/`.

## Usage Contract

- Use these keys for `output_format = html-revealjs` or `both`.
- Resolve `theme_key` to `skills/html-deck/pakco-html/assets/themes/<theme_key>.css`.
- Include or inline the bundled pakco assets instead of regenerating a full theme from scratch.
- PPTX generation ignores `html_config`, `html_motion_level`, `html_motion_profile`, `html_transition`, `html_animation`, and `html_gradient`.

## Theme Keys

This is a curated subset of the verified theme keys shipped in bundled pakco-html (`assets/themes/*.css`). Each is a CSS-tokens file overriding shared variables (`--bg`, `--accent`, `--accent-2/3`, `--font-display`, etc.). Use the bundled source files at runtime.

`Source` legend: `bundled` = verified key + tokens in bundled pakco-html; `general` = generic web design knowledge.

| Key | Best For | Visual System (verified tokens) | Source |
|-----|----------|---------------|--------|
| `minimal-white` | teaching, clean explainers, internal updates | white bg `#ffffff`, near-black ink `#0c0d10`, near-black accent `#111216`, Inter display, very low shadow | bundled |
| `editorial-serif` | essays, policy, research narratives | warm paper `#faf7f2`, brick accent `#8a2a1c` / terracotta `#c97a4a`, Playfair Display serif throughout | bundled |
| `swiss-grid` | consulting, structured analysis | white bg, signal-red accent `#d6001c`, Helvetica/Inter, strong grid alignment, low decoration | bundled |
| `corporate-clean` | executive and business reviews | white bg, navy ink `#0a2540`, royal-blue accent `#1d4ed8`, Inter, conservative borders | bundled |
| `academic-paper` | science, medical, literature review | off-white `#fdfcf8`, indigo accent `#1a3a7a` + maroon `#8a1a1a`, serif body (Latin Modern/Playfair), citation-friendly | bundled |
| `blueprint` | architecture, systems, engineering | deep blue bg `#0b3a6f`, white/cyan accents, JetBrains Mono, grid texture, diagram-first | bundled |
| `engineering-whiteprint` | architecture on light backgrounds | white bg, navy ink `#0a1e46`, blue accent `#1e5ac4` + red `#c42a10`, Mono display over Inter body, graph-paper grid | bundled |
| `terminal-green` | developer tools, infra, DevOps | near-black bg `#030a04`, neon-green accent `#00ff88`, JetBrains Mono, glow text | bundled |
| `pitch-deck-vc` | investor or competition decks | white bg, blue to purple to pink accents `#0070f3`/`#7928ca`/`#ff4ecb`, Inter, large whitespace | bundled |
| `news-broadcast` | sports, market updates, live operations | white bg, broadcast-red accent `#e11d2d` + yellow `#ffd100`, Oswald uppercase display, hard shadow | bundled |
| `magazine-bold` | brand storytelling, campaigns | cream bg `#f5efe2`, orange spot `#ea5a1a`, oversized Playfair display over Inter body | bundled |
| `aurora` | science/tech talks that need energy | DARK bg `#06091c`, mint/blue/violet glow accents `#5ef2c6`/`#7aa2ff`/`#c984ff`, gradient + blur, high-contrast text | bundled |
| `glassmorphism` | premium product or SaaS demo | DARK navy bg `#0b1024`, translucent surfaces (white at low alpha), sky/violet accents `#7dd3fc`/`#c084fc`; verify contrast | bundled |
| `cyberpunk-neon` | dramatic developer/AI demos | pure-black bg `#000000`, neon magenta `#ff2bd6` + cyan `#00f0ff` + yellow `#f9f871`, Mono display; use sparingly | bundled |

> Note: `product-launch` was previously listed here as a theme. It is **not** a theme in the source repo — it is a full-deck *template* (`templates/full-decks/product-launch/`). For a launch deck, choose a theme (e.g. `glassmorphism`, `aurora`, `pitch-deck-vc`) and apply launch layouts locally.

### Other verified theme keys (repo, not expanded above)

`soft-pastel`, `sharp-mono`, `arctic-cool`, `sunset-warm`, `catppuccin-latte`, `catppuccin-mocha`, `dracula`, `tokyo-night`, `nord`, `solarized-light`, `gruvbox-dark`, `rose-pine`, `neo-brutalism`, `bauhaus`, `xiaohongshu-white`, `rainbow-gradient`, `memphis-pop`, `y2k-chrome`, `retro-tv`, `japanese-minimal`, `vaporwave`, `midcentury`. (Source: bundled `assets/themes/*.css`.)

## Selection Heuristics

- `research` context: prefer `academic-paper`, `editorial-serif`, or `aurora`.
- `engineering` context: prefer `engineering-whiteprint`, `blueprint`, or `terminal-green`.
- `market` / `pitch`: prefer `pitch-deck-vc` or `magazine-bold` (apply launch *layouts* on top of the theme; there is no `product-launch` theme).
- `sports` / live operations: prefer `news-broadcast`.
- Long source-heavy decks should start from quieter themes; use high-energy themes only for cover, section, and conclusion contrast.

## CSS Token Minimum

Every generated HTML deck should include pakco `assets/base.css` plus the selected theme file. Generated slide CSS should consume these tokens:

```css
:root {
  --bg: #ffffff;
  --surface: #ffffff;
  --surface-2: #f2f2f4;
  --border: rgba(0,0,0,.08);
  --text-1: #111216;
  --text-2: #55596a;
  --accent: #3b6cff;
  --accent-2: #7a5cff;
  --grad: linear-gradient(135deg,#3b6cff,#7a5cff 55%,#ff5c8a);
}
```

Then theme-specific sections should consume those tokens rather than hard-coding one-off colors on every slide.
