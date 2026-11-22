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
- The controls slot (`data-slot="scene-controls"`) is `pointer-events-auto absolute right-3 bottom-3 left-3 z-20 flex flex-wrap items-center justify-end gap-2`, rendered **outside** the `aria-hidden` backdrop layer so HUD buttons stay keyboard- and screen-reader-accessible. It spans the full stage width and wraps, so a multi-button HUD cluster (world switcher, atmosphere switcher, motion toggle) never overflows a narrow viewport.

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

`bakeSky(W, H, dpr, atmosphere = 'dusk')`, `bakeFootFade(W, H, dpr, atmosphere = 'dusk')`, and `paintVoxelLayer(..., atmosphere = 'dusk')` all accept the active phase. `bakeLanternSprite(radius, dpr, glowRgb = [248, 192, 98])` takes the active world's `WORLD_METADATA[worldId].glowRgb` so each diorama's beacon halo is tinted by its own palette (ember orange, bioluminescent teal, brass gold, cedar amber) instead of a single fixed amber.

## Garden Backdrop & Multi-World Dioramas (`GardenBackdrop`)

`apps/web/src/features/home/backdrop/GardenBackdrop.tsx` is a modular multi-world voxel diorama renderer mounted inside `SceneStage`. It renders 5 distinct curated worlds (`sakura-garden`, `magma-forge`, `bioluminescent-reef`, `sky-observatory`, `cedar-sanctuary`) with 5 corresponding particle physics presets (`sakura`, `embers`, `spores`, `star-runes`, `cedar-mist`) across Matcha & Cedar market-session atmospheres (`dawn`, `daylight`, `dusk`, `after-hours`).

### Props

| Prop | Type | Default | Behavior |
|---|---|---|---|
| `className` | `string` | — | Canvas class. |
| `world` | `WorldId` | `'sakura-garden'` | Selects which 3D voxel island generator (`voxel-world.ts`, `garden-world.ts`, `worlds.ts`) renders (`data-world`). |
| `particleMode` | `ParticleMode` | matched to `world` | Overrides particle physics (`sakura`, `embers`, `spores`, `star-runes`, `cedar-mist`) (`data-particle-mode`). |
| `atmosphere` | `AtmospherePhase` | `'dusk'` | Active phase; drives sky, voxel lighting, and micro-life. Emitted as `data-atmosphere` on the canvas. |
| `paused` | `boolean` | — | Optional externally controlled paused state (used when the parent hosts HUD controls). |
| `onPausedChange` | `(paused: boolean) => void` | — | Notifies the parent when the reduced/paused state changes. |
| `showControls` | `boolean` | `true` | Whether to render the floating Pause/Play button inside `GardenBackdrop`. Set `false` when `SceneStage` renders HUD controls in its foreground `controls` slot. |

### Curated Worlds & Investing Personality Mapping

Each diorama pairs 1:1 with a starter recipe in `packages/config/starter-recipes.json` and an investing archetype evaluated by `apps/web/src/features/personality/personality-data.ts` on `/personality`:

| World ID | Particle Mode | Archetype (`PersonalityQuizPage`) | Starter Recipe Match |
|---|---|---|---|
| `sakura-garden` | `sakura` | The Patient Compounder | Quality Value Screener |
| `magma-forge` | `embers` | The Headline Surfer | Trump & Chips News Momentum |
| `bioluminescent-reef` | `spores` | The Contrarian Diver | Contrarian Sentiment Fader |
| `sky-observatory` | `star-runes` | The Catalyst Quant | Earnings Catalyst Hunter |
| `cedar-sanctuary` | `cedar-mist` | The Systems Architect | Claude Agent Portfolio Mirror |

### Homepage & Diagnostic Integration

- `apps/web/src/features/home/pages/HomeCtaPage.tsx` and `apps/web/src/features/personality/PersonalityQuizPage.tsx` share `useDioramaStage.ts` (`apps/web/src/features/home/backdrop/useDioramaStage.ts`) for market-ET atmosphere resolution and reduced-motion pause sync, plus `SceneHudControls.tsx` (`World: <Name>`, `Sky: <Phase>`, `Pause motion`/`Play motion`). `useDioramaStage` also exports `syncUrlSearchParam(key, value)`, a `history.replaceState` helper that rewrites one query param without a router transition.
- `apps/web/src/features/home/pages/HomeCtaPage.tsx` renders on `SceneStage` (`variant="hero"`, `motionRole="reactive"`), restores preferred worlds from `/?world=` or `localStorage` (`benchify.world` via `world-storage.ts`), syncs URL search params when cycling worlds, and links to `/lab`, `/personality`, and `/leaderboard`.
- `apps/web/src/features/personality/PersonalityQuizPage.tsx` (`/personality`, also `?archetype=<id>`) uses a discriminated union (`answering` | `result:quiz` | `result:inspect`), `PersonalityQuizStep.tsx`, and `PersonalityResultPanel.tsx` (`Card variant="outlined"` / `.voxel-trough`, zero nested `.voxel-card`) to run the 10-question 4-axis diagnostic (`Horizon`, `Signal`, `Contrarian`, `Cadence`), live-preview the leading world diorama, reveal top-2 matched starter recipes linking into `/build?idea=...`, and persist matched worlds to the homepage.

### 4-Plane Depth Parallax & Micro-Life

`paintFrame` composites four depth planes back-to-front:

1. **Atmospheric sky** — phase-baked gradient plus `drawZenithParticles` (twinkling stars for dusk/after-hours, drifting sun-motes for dawn/daylight).
2. **Far high-altitude cloud slabs** — slow breeze drift (`sin(time * 0.08)`) plus subtle parallax.
3. **Floating voxel island** — gentle vertical levitation (`sin(time * 0.45)`) plus world-reactive micro-life (water/lava glints, isometric diamond ripples, lantern/forge/crystal glow halos scaled by world glow color, phase-reactive secondary sprites, and world-specific drifters such as falling petals, rising embers, helical spores, orbital star-runes, and valley mist + autumn leaves).
4. **Near perimeter cloud slabs** — faster breeze drift (`sin(time * 0.11 + 1.4)`) plus deeper parallax.

`drawAtmosphericParticles` is decomposed into per-concern passes — `drawSurfaceGlints`, `drawSurfaceRipples`, `drawBeaconHalos`, `drawSecondaryFloaters`, and `drawDriftingParticles` (which dispatches to `drawEmberDrifters`, `drawSporeDrifters`, `drawRuneStreaks`, or `drawLeafOrPetalDrifters`) — all reading colors and kinematics from `PARTICLE_PRESETS` (`particle-presets.ts`) rather than hardcoded hex values. `cedar-mist` additionally paints three drifting valley-mist bands.

`voxel-world.ts`, `particle-presets.ts`, `garden-world.ts`, `worlds.ts`, and `worlds/*.ts` share `createVoxelCanvas`, `extractWorldFaces`, and `stripWorldBuffers` (freeing heavy voxel occupancy arrays after face extraction), preserving deterministic seed geometry across all 5 islands. `worlds/shared-terrain.ts` supplies the shared `fillTerrainVolume`, `buildIslandUndercrust`, and `buildStandardClouds` primitives every non-sakura generator composes. `garden-renderer.ts` exports `disposeCanvas` / `disposeSceneCanvases`, which zero an offscreen canvas's backing store; `GardenBackdrop` calls `disposeSceneCanvases` on unmount and disposes only the layers a change actually invalidates (sky/foot on atmosphere change, lantern sprite and island/cloud slabs on world change), reusing unchanged layers across world/particle switches.

## CSS Foundations (`apps/web/src/styles/app.css`)

- `.voxel-dot-matrix` — radial-gradient dot texture at 20px spacing.
- `.scene-atmosphere-dawn` / `-daylight` / `-dusk` / `-after-hours` — Matcha & Cedar vertical sky gradients.
- `.scene-scrim` — semi-opaque Matcha backing (`rgba(20, 28, 24, 0.88)`), zero `backdrop-blur`.
- `.scene-stage-hero` (`min-height: 20rem`) / `.scene-stage-footer` (`min-height: 11rem`).
- `.scene-stage-hero.home-hero-viewport` — `min-height: calc(100dvh - 3.875rem)` so the homepage hero fills the viewport below the sticky navbar.
- `@media (prefers-reduced-motion: reduce)` disables animation/transition on `.scene-backdrop` and descendants.

## Testing & Verification

- `packages/ui-design-system/src/lib/atmosphere.test.ts` — verifies all four phases, EST/EDT boundaries, local-mode thresholds, and `NaN` fallback to `dusk`.
- `apps/web/src/test/scene-stage.test.tsx` — verifies hero/footer landmarks, default `dusk` atmosphere, `data-motion-role`, `aria-hidden` backdrop, scrim panel without `backdrop-blur`, `HeroBackground` atmosphere/backdrop slots, and that the `controls` slot renders outside `aria-hidden` with `flex-wrap` and `justify-end` so the HUD cluster wraps instead of overflowing.
- `apps/web/src/test/design-standardization.test.tsx` — verifies `SceneStage` containment/scrim invariants and that `HeroBackground` emits no `rounded-full`, `blur-3xl`, viewport breakpoints, inline styles, or legacy color tokens, while rendering `.voxel-dot-matrix`.
- `apps/web/src/features/home/backdrop/GardenBackdrop.test.tsx` — verifies `data-world`, `data-particle-mode`, `data-atmosphere`, all 4 distinct `ATMOSPHERE_PALETTES`, controlled props + `showControls={false}`, reduced-motion toggle, explicit `particleMode` overrides, and that no `requestAnimationFrame` starts when `paused` is true or when reduced motion wins over an initial `paused={false}`.
- `apps/web/src/features/home/backdrop/garden-world.test.ts` — verifies deterministic fireflies (16) and koi (2) anchors, and far/near cloud face extraction with painter's depth order.
- `apps/web/src/features/home/backdrop/worlds.test.ts` — verifies all 5 world generators, unique silhouettes, painter depth order, distinct particle modes, and `localStorage` persistence.
- `apps/web/src/features/home/pages/HomeCtaPage.test.tsx` — verifies the `SceneStage` hero shell, `.scene-scrim .voxel-card` CTA plaque, accessible HUD controls (5-world switcher, 4-phase atmosphere switcher, motion toggle), `localStorage` persistence, `initialWorld` seeding, and `/personality` link.
- `apps/web/src/features/personality/personality-data.test.ts` & `PersonalityQuizPage.test.tsx` — verify the 10-question 4-axis diagnostic scoring engine, full 5-archetype reachability, starter recipe integrity, live world preview, top-2 bot matches linking to `/build?idea=`, and `?archetype=` hydration.

## Related

- [[entities/design-system]] — the shared UI design system and its component inventory
- [[concepts/rendering-strategies]] — SSR, Hybrid SSR, and CSR architecture
- [[concepts/fluent-responsive-design]] — fluid, breakpoint-free layout conventions
- [[entities/personality-quiz]] — the `/personality` diagnostic that drives these worlds
- [[entities/web-app]] — the TanStack Start client dashboard
