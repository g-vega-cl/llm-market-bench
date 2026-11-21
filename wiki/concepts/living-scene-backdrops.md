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
| `controls` | `React.ReactNode` | — | Accessible foreground HUD controls (`data-slot="scene-controls"`) anchored to the bottom-right stage corner outside `aria-hidden`. |
| `children` | `React.ReactNode` | — | Foreground content. |

### Structural Guarantees

- Root element carries `data-slot="scene-stage"`, `data-stage-variant`, `data-atmosphere`, and `data-motion-role`, plus `relative isolate overflow-hidden rounded-none`.
- Backdrop layer (`data-slot="scene-backdrop"`) is `aria-hidden="true"`, `pointer-events-none`, `absolute inset-0 z-0 overflow-hidden`, and only rendered when `backdrop` is supplied.
- Foreground content sits in a `relative z-10 mx-auto w-full max-w-7xl min-w-0` wrapper.
- The scrim panel (`data-slot="scene-scrim"`) uses `scene-scrim voxel-card rounded-none p-6 min-w-0` and never `backdrop-blur`.
- The controls slot (`data-slot="scene-controls"`) is `pointer-events-auto absolute right-3 bottom-3 z-20 flex items-center gap-2`, rendered **outside** the `aria-hidden` backdrop layer so HUD buttons stay keyboard- and screen-reader-accessible.

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

### Atmosphere Palettes (`ATMOSPHERE_PALETTES`)

`apps/web/src/features/home/backdrop/garden-renderer.ts` exports `ATMOSPHERE_PALETTES: Record<AtmospherePhase, AtmospherePalette>`, giving each phase a distinct Matcha & Cedar sky and lighting treatment. Each palette defines:

- `skyStops` — 7+ vertical gradient stops (the zenith top color is unique per phase).
- `horizonGlow` — three-stop radial glow behind the island silhouette.
- `topVignette` — two-stop top atmospheric vignette tuned for AAA cream-text contrast.
- `footFade` — bottom fade band color.
- `lightScale` — global voxel face brightness multiplier.
- `topTint` / `sideTint` — per-face RGB tint multipliers.
- `islandFog` / `cloudFog` — depth-fog RGB targets for island and cloud faces.
- `lanternAlphaScale` — lantern glow halo intensity.
- `showStars` / `showFireflies` / `showSunMotes` — which zenith and micro-life layers render.

`bakeSky(W, H, dpr, atmosphere = 'dusk')`, `bakeFootFade(W, H, dpr, atmosphere = 'dusk')`, and `paintVoxelLayer(..., atmosphere = 'dusk')` all accept the active phase.

## Garden Backdrop (Homepage Living Diorama)

`apps/web/src/features/home/backdrop/GardenBackdrop.tsx` is the homepage's multi-layered voxel garden island, rendered as a `SceneStage` backdrop. It floats across the dynamic Matcha & Cedar market-session atmospheres with 4-plane depth parallax and phase-reactive micro-life.

### Props

| Prop | Type | Default | Behavior |
|---|---|---|---|
| `className` | `string` | — | Canvas class. |
| `atmosphere` | `AtmospherePhase` | `'dusk'` | Active phase; drives sky, voxel lighting, and micro-life. Emitted as `data-atmosphere` on the canvas. |
| `paused` | `boolean` | — | Optional externally controlled paused state (used when the parent hosts HUD controls). |
| `onPausedChange` | `(paused: boolean) => void` | — | Notifies the parent when the reduced/paused state changes. |
| `showControls` | `boolean` | `true` | Whether to render the floating Pause/Play button inside `GardenBackdrop`. Set `false` when `SceneStage` renders HUD controls in its foreground `controls` slot. |

### 4-Plane Depth Parallax

`paintFrame` composites four depth planes back-to-front:

1. **Atmospheric sky** — phase-baked gradient plus `drawZenithParticles` (twinkling stars for dusk/after-hours, drifting sun-motes for dawn/daylight).
2. **Far high-altitude cloud slabs** — slow breeze drift (`sin(time * 0.08)`) plus subtle parallax.
3. **Floating voxel island** — gentle vertical levitation (`sin(time * 0.45)`) plus island micro-life (glints, koi ripples, lantern halos, fireflies, petals).
4. **Near perimeter cloud slabs** — faster breeze drift (`sin(time * 0.11 + 1.4)`) plus deeper parallax.

### Deterministic Micro-Life

All particle anchors are generated deterministically from index-based formulas (no `Math.random`), so SSR and hydration match and tests stay stable:

- `petals` — drifting cherry blossom petals.
- `glints` — pond water glints.
- `lamps` — stone & torii lantern glow halos (scaled by `lanternAlphaScale`).
- `fireflies` — 16 phase-reactive rising fireflies at 4 hubs (bamboo grove, arched wooden bridge, torii clearing, stone lantern path), shown in dusk & after-hours.
- `koi` — 2 koi swimming water ripple diamonds in the pond.
- `skyMotes` — 26 zenith stars (dusk/after-hours) or sun motes (dawn/daylight).

`garden-world.ts` splits the 6 cloud slabs into `cloudsFar` / `cloudsNear` face buckets via `extractWorldFaces`, and `garden-renderer.ts` bakes each plane with the active atmosphere palette.

### Homepage Integration (`HomeCtaPage`)

`apps/web/src/features/home/pages/HomeCtaPage.tsx` renders on `SceneStage` (`variant="hero"`, `motionRole="reactive"`):

- Auto-resolves the US Eastern market session atmosphere (`resolveAtmospherePhase(new Date(), 'market-et')`) on mount after a deterministic `'dusk'` SSR render.
- Passes `GardenBackdrop` into the `backdrop` slot with `showControls={false}`.
- Renders foreground HUD `controls`: an atmosphere switcher (`Sky: <Phase>`, `data-testid="atmosphere-switcher"`) that cycles all four phases, plus a Pause/Play motion toggle.
- Houses the CTA cluster and trust strip inside a compact `.scene-scrim .voxel-card rounded-none` plaque (`data-testid="home-cta-plaque"`, zero `backdrop-blur`).

## CSS Foundations (`apps/web/src/styles/app.css`)

- `.voxel-dot-matrix` — radial-gradient dot texture at 20px spacing.
- `.scene-atmosphere-dawn` / `-daylight` / `-dusk` / `-after-hours` — Matcha & Cedar vertical sky gradients.
- `.scene-scrim` — semi-opaque Matcha backing (`rgba(20, 28, 24, 0.88)`), zero `backdrop-blur`.
- `.scene-stage-hero` (`min-height: 20rem`) / `.scene-stage-footer` (`min-height: 11rem`).
- `.scene-stage-hero.home-hero-viewport` — `min-height: calc(100dvh - 3.875rem)` so the homepage hero fills the viewport below the sticky navbar.
- `@media (prefers-reduced-motion: reduce)` disables animation/transition on `.scene-backdrop` and descendants.

## Testing & Verification

- `packages/ui-design-system/src/lib/atmosphere.test.ts` — verifies all four phases, EST/EDT boundaries, local-mode thresholds, and `NaN` fallback to `dusk`.
- `apps/web/src/test/scene-stage.test.tsx` — verifies hero/footer landmarks, default `dusk` atmosphere, `data-motion-role`, `aria-hidden` backdrop, scrim panel without `backdrop-blur`, `HeroBackground` atmosphere/backdrop slots, and that the `controls` slot renders outside `aria-hidden`.
- `apps/web/src/test/design-standardization.test.tsx` — verifies `SceneStage` containment/scrim invariants and that `HeroBackground` emits no `rounded-full`, `blur-3xl`, viewport breakpoints, inline styles, or legacy color tokens, while rendering `.voxel-dot-matrix`.
- `apps/web/src/features/home/backdrop/GardenBackdrop.test.tsx` — verifies the `data-atmosphere` attribute, all 4 distinct `ATMOSPHERE_PALETTES` (7+ sky stops, 4 distinct zenith tops), controlled `atmosphere` + `showControls={false}`, and the reduced-motion Play/Pause toggle.
- `apps/web/src/features/home/backdrop/garden-world.test.ts` — verifies deterministic fireflies (16) and koi (2) anchors, and far/near cloud face extraction with painter's depth order.
- `apps/web/src/features/home/pages/HomeCtaPage.test.tsx` — verifies the `SceneStage` hero shell (`data-slot="scene-stage"`, `data-stage-variant="hero"`, `data-motion-role="reactive"`, `.scene-atmosphere-*`), the `.scene-scrim .voxel-card` CTA plaque without `backdrop-blur`, and the accessible HUD controls (atmosphere switcher cycling all 4 phases + motion toggle) outside `aria-hidden`.

## Related

- [[entities/design-system]] — the shared UI design system and its component inventory
- [[concepts/rendering-strategies]] — SSR, Hybrid SSR, and CSR architecture
- [[concepts/fluent-responsive-design]] — fluid, breakpoint-free layout conventions
- [[entities/web-app]] — the TanStack Start client dashboard
