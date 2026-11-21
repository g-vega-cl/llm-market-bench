---
tags: [design-system, ui, animation, performance, accessibility, voxel, atmosphere]
category: concept
---

# Living Scene Backdrops & Expressive Motion

Expressive animated backdrops are permitted across **major page heroes and parallax footers** while preserving legibility, Voxel geometry, and performance. The architecture separates sky, midground scenery, and independent procedural micro-entities into discrete layers, clips them inside contained stages, and protects foreground CTAs with opaque Matcha scrims — never glassmorphism blur. This concept is codified in `.agents/rules/design-spec.md` §12 and implemented by the `SceneStage` / `HeroBackground` layouts plus the `atmosphere` utility in `packages/ui-design-system`.

## Core Principles

1. **Modular layered dioramas + ambient life** — Separate sky, midground scenery, and independent procedural micro-entities (clouds, fauna, footer sprites) into discrete layers. Never flat looping videos or static baked clips.
2. **Containment & CTA scrims (zero glassmorphism)** — Clip animated stages inside `SceneStage` / `HeroBackground` (`overflow-hidden isolate`) with hard scroll ceilings so motion never bleeds into data tables. Protect CTAs with opaque/semi-opaque Matcha backing panels (`.scene-scrim` / `.voxel-card`, never `backdrop-blur`).
3. **Dynamic atmosphere cycles** — Use `.scene-atmosphere-{dawn|daylight|dusk|after-hours}` and `resolveAtmospherePhase(date, mode)` from `@llm-market-bench/ui-design-system` (defaults to US Eastern market session `America/New_York`, optional `'local'` mode; pass a shared SSR timestamp or default `'dusk'`).
4. **Motion roles & bans** — Declare `data-motion-role`: `background` (calm ambient depth), `reactive` (bounded pointer/hover), or `story` (bounded scroll hero/footer). Full-page *"Is the site"* WebGL takeovers and scroll-jacking are prohibited on data routes.
5. **Resize resilience, perf & reduced motion** — Anchor parallax travel to container/`window.innerHeight` with resize invalidation (never document `maxScroll`). Use GPU-composited transforms or offscreen-baked canvas capped at `<= 30fps`, mark backdrops `aria-hidden="true"` + `pointer-events-none`, and honor `prefers-reduced-motion`.

## SceneStage Layout Primitive

`packages/ui-design-system/src/layouts/SceneStage.tsx` is a spatially contained Voxel stage for multi-layered living-scene heroes and parallax footers. It enforces strict foreground/background separation.

### Props

| Prop | Type | Default | Behavior |
|---|---|---|---|
| `variant` | `'hero' \| 'footer'` | `'hero'` | Renders a `<section>` for heroes or a `<footer>` landmark for parallax footers. |
| `atmosphere` | `AtmospherePhase` | `'dusk'` | Applies the matching `.scene-atmosphere-*` sky gradient. |
| `motionRole` | `'background' \| 'reactive' \| 'story'` | `'background'` | Emitted as `data-motion-role` for the motion taxonomy. |
| `scrim` | `'none' \| 'panel'` | `'none'` | When `'panel'`, wraps children in a `.scene-scrim .voxel-card` CTA protection panel. |
| `backdrop` | `React.ReactNode` | — | Rendered in a dedicated `aria-hidden` `pointer-events-none` layer behind children. |
| `children` | `React.ReactNode` | — | Foreground content. |

### Structural Guarantees

- Root element carries `data-slot="scene-stage"`, `data-stage-variant`, `data-atmosphere`, and `data-motion-role`, plus `relative isolate overflow-hidden rounded-none`.
- Backdrop layer (`data-slot="scene-backdrop"`) is `aria-hidden="true"`, `pointer-events-none`, `absolute inset-0 z-0 overflow-hidden`, and only rendered when `backdrop` is supplied.
- Foreground content sits in a `relative z-10 mx-auto w-full max-w-7xl min-w-0` wrapper.
- The scrim panel (`data-slot="scene-scrim"`) uses `scene-scrim voxel-card rounded-none p-6 min-w-0` and never `backdrop-blur`.

## HeroBackground Layout

`packages/ui-design-system/src/layouts/HeroBackground.tsx` is a spatially contained Voxel hero stage built strictly from Matcha & Cedar semantic tokens with sharp 0px geometry, fluid padding (zero viewport breakpoints), a CSS dot-matrix horizon texture, and an optional living-scene backdrop slot.

### Props

| Prop | Type | Default | Behavior |
|---|---|---|---|
| `gradient` | `'electric' \| 'success' \| 'catalyst' \| 'ai'` | `'electric'` | Selects the semantic accent edge (`border-voxel-bevel-hi`, `border-success/40`, `border-accent/40`, `border-info/40`). |
| `atmosphere` | `AtmospherePhase` | — | When set, applies the matching `.scene-atmosphere-*` gradient and suppresses the gradient overlay. |
| `backdrop` | `React.ReactNode` | — | Rendered in a `data-slot="hero-backdrop"` `aria-hidden` layer. |
| `children` | `React.ReactNode` | — | Hero content. |

### Modernization Notes

The prior implementation used `gradient-*` utility classes, inline `style` dot patterns, and animated `rounded-full blur-3xl` orbs. The current implementation:

- Uses the CSS `.voxel-dot-matrix` texture instead of inline styles.
- Removes all `rounded-full` / `blur-3xl` orbs and viewport breakpoints (`md:px-12`, `md:py-24`).
- Uses fluid padding (`px-6 py-12`) and `rounded-none` geometry.
- Emits `data-slot="hero-background"` and `data-atmosphere`.

## Atmosphere Phases

`packages/ui-design-system/src/lib/atmosphere.ts` resolves the Matcha & Cedar atmospheric sky phase for a timestamp.

### Exports

- `ATMOSPHERE_PHASES` — `['dawn', 'daylight', 'dusk', 'after-hours'] as const`.
- `AtmospherePhase` — union type of the four phases.
- `AtmosphereClockMode` — `'market-et' | 'local'`.
- `resolveAtmospherePhase(date = new Date(), mode = 'market-et')` — returns the phase.

### Thresholds

**`market-et` (default, US Eastern via `Intl.DateTimeFormat` with `America/New_York`):**

| Phase | Window |
|---|---|
| `dawn` | 04:00–09:29 ET (pre-market) |
| `daylight` | 09:30–15:59 ET (regular session) |
| `dusk` | 16:00–19:59 ET (close & golden-hour twilight) |
| `after-hours` | 20:00–03:59 ET (overnight) |

**`local` (visitor timezone):**

| Phase | Window |
|---|---|
| `dawn` | 05:00–08:59 |
| `daylight` | 09:00–16:59 |
| `dusk` | 17:00–20:59 |
| `after-hours` | 21:00–04:59 |

Invalid `Date` values fall back deterministically to `'dusk'` in both modes. The ET formatter respects EST/EDT transitions.

## CSS Foundations (`apps/web/src/styles/app.css`)

- `.voxel-dot-matrix` — radial-gradient dot texture at 20px spacing.
- `.scene-atmosphere-dawn` / `-daylight` / `-dusk` / `-after-hours` — Matcha & Cedar vertical sky gradients.
- `.scene-scrim` — semi-opaque Matcha backing (`rgba(20, 28, 24, 0.88)`), zero `backdrop-blur`.
- `.scene-stage-hero` (`min-height: 20rem`) / `.scene-stage-footer` (`min-height: 11rem`).
- `@media (prefers-reduced-motion: reduce)` disables animation/transition on `.scene-backdrop` and descendants.

## Testing & Verification

- `packages/ui-design-system/src/lib/atmosphere.test.ts` — verifies all four phases, EST/EDT boundaries, local-mode thresholds, and `NaN` fallback to `dusk`.
- `apps/web/src/test/scene-stage.test.tsx` — verifies hero/footer landmarks, default `dusk` atmosphere, `data-motion-role`, `aria-hidden` backdrop, scrim panel without `backdrop-blur`, and `HeroBackground` atmosphere/backdrop slots.
- `apps/web/src/test/design-standardization.test.tsx` — verifies `SceneStage` containment/scrim invariants and that `HeroBackground` emits no `rounded-full`, `blur-3xl`, viewport breakpoints, inline styles, or legacy color tokens, while rendering `.voxel-dot-matrix`.

## Related

- [[entities/design-system]] — the shared UI design system and its component inventory
- [[concepts/rendering-strategies]] — SSR, Hybrid SSR, and CSR architecture
- [[concepts/fluent-responsive-design]] — fluid, breakpoint-free layout conventions
- [[entities/web-app]] — the TanStack Start client dashboard
