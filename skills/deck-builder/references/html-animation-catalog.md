# HTML Animation Catalog

CSS-only motion guidance for native Reveal.js decks. Public HTML deck libraries often include both CSS animations and Canvas/WebGL effects; Presentation Director currently internalizes the CSS motion patterns only. Canvas FX remains future capability.

## Motion Fields

| Field | Purpose | Values |
|-------|---------|--------|
| `html_motion_level` | intensity | `subtle`, `expressive`, `cinematic` |
| `html_motion_profile` | style family | `presenter`, `academic`, `tech`, `pitch`, `product`, `editorial` |
| `html_config.effects_runtime` | implementation boundary | currently `css-only` |

## Levels

| Level | Use When | Allowed Effects |
|-------|----------|-----------------|
| `subtle` | research, executive, source-heavy decks | fade, rise-in, light stagger, opacity-only reveals |
| `expressive` | product, teaching, technical demos | zoom-pop, path-draw, counter-up, gradient-flow, stagger-list |
| `cinematic` | cover, section divider, finale, short pitch | spotlight, shimmer-sweep, perspective-zoom, kenburns, neon-glow |

`cinematic` does not mean Canvas/WebGL. It is a stronger CSS-only profile and should be limited to pages where motion supports comprehension or pacing.

## Profile Heuristics

| Profile | Motion Taste |
|---------|--------------|
| `presenter` | clean slide transitions, sparse element reveals, readable live delivery |
| `academic` | mostly fade/rise, no distracting loops, citation-first |
| `tech` | path-draw for diagrams, terminal cursor accents, measured stagger |
| `pitch` | big-number counters, section punch, spotlight/zoom on key claims |
| `product` | workflow step reveals, feature comparison stagger, gentle gradient movement |
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

.reveal .slides section.present .stagger > * {
  animation: rise-in .5s ease both;
}
.reveal .slides section.present .stagger > *:nth-child(2) { animation-delay: .08s; }
.reveal .slides section.present .stagger > *:nth-child(3) { animation-delay: .16s; }
.reveal .slides section.present .stagger > *:nth-child(4) { animation-delay: .24s; }
```

## Guardrails

- Do not animate body paragraphs one word at a time.
- Do not run infinite loops on content slides.
- Do not animate chart axes after labels are already visible; reveal chart and labels together or in meaningful groups.
- Avoid motion that changes layout dimensions after render; use `transform` and `opacity`.
- Presenter notes should work through Reveal.js notes support; do not depend on a custom external presenter runtime.
