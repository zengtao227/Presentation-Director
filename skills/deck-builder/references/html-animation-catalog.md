# HTML Animation Catalog

CSS-only motion guidance for native Reveal.js decks. The source library `lewislulu/html-ppt-skill` ships two distinct animation systems: 27 CSS animations (`assets/animations/animations.css`) and 20 canvas FX modules (`assets/animations/fx/*.js`). Presentation Director internalizes only the CSS motion patterns. Canvas FX remains future capability (see "Canvas FX — out of scope" below).

`Source` legend used in this file: `repo` = the named effect is a verified CSS animation in html-ppt-skill; `general` = standard CSS / Reveal.js motion knowledge. PD implements all of these as local keyframes; it does not import the source CSS.

## Motion Fields

| Field | Purpose | Values |
|-------|---------|--------|
| `html_motion_level` | intensity | `subtle`, `expressive`, `cinematic` |
| `html_motion_profile` | style family | `presenter`, `academic`, `tech`, `pitch`, `product`, `editorial` |
| `html_config.effects_runtime` | implementation boundary | currently `css-only` |

## Levels

| Level | Use When | Allowed Effects | Source |
|-------|----------|-----------------|--------|
| `subtle` | research, executive, source-heavy decks | fade (up/down/left/right), rise-in, optional `.stagger-ok` decorative card rows, opacity-only reveals | repo: `fade-*`, `rise-in`, guarded stagger |
| `expressive` | product, teaching, technical demos | zoom-pop, path-draw, counter-up, gradient-flow, guarded `.stagger-ok` card rows, blur-in | repo: all named |
| `cinematic` | cover, section divider, finale, short pitch | spotlight, shimmer-sweep, perspective-zoom, kenburns, neon-glow, ripple-reveal | repo: all named (CSS keyframes) |

`cinematic` does not mean Canvas/WebGL. It is a stronger CSS-only profile and should be limited to pages where motion supports comprehension or pacing. Every effect named above corresponds to a verified CSS keyframe in the source repo (e.g. `kf-spot`, `kf-shimmer`, `kf-pzoom`, `kf-kenburns`, `kf-neon`, `kf-ripple`) — none requires canvas.

## Verified CSS animation vocabulary (repo)

The source repo's `animations.css` defines exactly these 27 CSS-only animation names (applied via `class="anim-<name>"` or `data-anim="<name>"`). PD reimplements the relevant ones as local keyframes:

- Directional fades: `fade-up`, `fade-down`, `fade-left`, `fade-right`
- Dramatic entries: `rise-in`, `drop-in`, `zoom-pop`, `blur-in`, `glitch-in`
- Text effects: `typewriter`, `neon-glow`, `shimmer-sweep`, `gradient-flow`
- Lists & numbers: `counter-up`; use `.stagger-ok` only for decorative card rows, not lists
- SVG / geometry: `path-draw`, `morph-shape`
- 3D / perspective: `parallax-tilt`, `card-flip-3d`, `cube-rotate-3d`, `page-turn-3d`, `perspective-zoom`
- Ambient / continuous: `marquee-scroll`, `kenburns`, `confetti-burst`, `spotlight`, `ripple-reveal`

All are pure CSS (keyframes + transforms/filters), all disabled under `prefers-reduced-motion: reduce`. Prefer `transform`/`opacity`/`filter`; avoid the infinite-loop ones (`neon-glow`, `gradient-flow`, `marquee-scroll`, `kenburns`, `morph-shape`) on dense content slides.

## Canvas FX — out of scope (future capability)

The source repo also ships 20 **canvas FX** modules (`assets/animations/fx/*.js`, e.g. `particle-burst`, `matrix-rain`, `knowledge-graph`, `neural-net`, `galaxy-swirl`) driven by a `fx-runtime.js` that auto-initializes `[data-fx]` elements on slide enter. These are verified to exist in the source but are **deliberately not adopted**: they require a JS canvas runtime that Presentation Director does not ship, and the `effects_runtime` boundary is `css-only`. Do not catalog or emit any `data-fx` / canvas effect as current capability. (Source: repo `references/animations.md`, "FX (canvas)" section.)

## Profile Heuristics

| Profile | Motion Taste |
|---------|--------------|
| `presenter` | clean slide transitions, sparse element reveals, readable live delivery |
| `academic` | mostly fade/rise, no distracting loops, citation-first |
| `tech` | path-draw for diagrams, terminal cursor accents, measured card-row stagger only when `.stagger-ok` is appropriate |
| `pitch` | big-number counters, section punch, spotlight/zoom on key claims |
| `product` | workflow step reveals, card-row stagger only with `.stagger-ok`, gentle gradient movement |
| `editorial` | page-turn feel, quote reveals, image/caption timing |

## Implementation Snippets

```css
.reveal .slides section.present .rise-in {
  animation: rise-in .55s ease both;
}
@keyframes rise-in {
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: translateY(0); }
}

.reveal .slides section.present .stagger.stagger-ok > * {
  animation: rise-in .5s ease both;
}
.reveal .slides section.present .stagger.stagger-ok > *:nth-child(2) { animation-delay: .08s; }
.reveal .slides section.present .stagger.stagger-ok > *:nth-child(3) { animation-delay: .16s; }
.reveal .slides section.present .stagger.stagger-ok > *:nth-child(4) { animation-delay: .24s; }
```

## Guardrails

- Do not animate body paragraphs one word at a time.
- Do not use bare `.stagger`; use `.stagger.stagger-ok` only on decorative, single-row, uniform horizontal card/tile/metric grids.
- Do not run infinite loops on content slides.
- Do not animate chart axes after labels are already visible; reveal chart and labels together or in meaningful groups.
- Avoid motion that changes layout dimensions after render; use `transform` and `opacity`.
- Presenter notes should work through Reveal.js notes support; do not depend on a custom external presenter runtime. The source repo ships its own presenter mode (`S` key, `BroadcastChannel` sync, `?preview=N` iframe previews); this is verified to exist but is intentionally not used. The Reveal.js Notes plugin is the current path.
