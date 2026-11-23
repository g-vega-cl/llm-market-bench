---
tags: [design-system, ui, animation, performance, accessibility, voxel, atmosphere]
category: concept
---

# Living Scene Backdrops & Expressive Motion

Expressive animated backdrops are permitted across **major page heroes and parallax footers** while preserving legibility, Voxel geometry, and performance. The architecture separates sky, midground scenery, and independent procedural micro-entities into discrete layers, clips them inside contained stages, and protects foreground CTAs with opaque Matcha scrims — never glassmorphism blur — or with extended top atmospheric sky vignettes. This concept is codified in `.agents/rules/design-spec.md` §12 and implemented by the `SceneStage` / `HeroBackground` layouts plus the `atmosphere` utility in `packages/ui-design-system`.

## Core Principles

1. **Modular layered dioramas + ambient life** — Separate sky, midground scenery, and independent procedural micro-entities (clouds, fauna, footer sprites) into discrete layers. Never flat looping videos or static baked clips.
2. **Containment & CTA legibility (zero glassmorphism)** — Clip animated stages inside `SceneStage` / `HeroBackground` (`overflow-hidden isolate`) with hard scroll ceilings so motion never bleeds into data tables. Protect foreground UI either with opaque/semi-opaque Matcha surfaces (`.voxel-btn`, `.scene-scrim` / `.voxel-card`, never `backdrop-blur`) or with extended top atmospheric sky vignettes maintaining accessible contrast (`>= 4.5:1` AA / `>= 7:1` AAA) with central diorama sightlines clear of bright cloud slabs.
3. **Zero SSR/CSR flash & CLS invariance** — Route loaders (`apps/web/src/routes/index.tsx`, `apps/web/src/routes/personality.tsx`) resolve the US Eastern market atmosphere (`resolveAtmospherePhase(new Date(), 'market-et')`) server-side and pass `initialAtmosphere` into `useDioramaStage(initialAtmosphere)`. CSS `.scene-atmosphere-*` gradients match `ATMOSPHERE_PALETTES` stops pixel-for-pixel, and `<canvas>` cross-fades in cleanly once the first frame paints so SSR and CSR never produce layout shifts or sky flashes. See [[concepts/cumulative-layout-shift]].
4. **Motion roles & bans** — Declare `data-motion-role`: `background` (calm ambient depth), `reactive` (bounded pointer/hover), or `story` (bounded scroll hero/footer). Full-page WebGL takeovers and scroll-jacking are prohibited on data routes.
5. **Resize resilience, perf & reduced motion** — Anchor parallax travel to container/`window.innerHeight` with resize invalidation (never document `maxScroll`). Use offscreen-baked canvas capped at `<= 30fps`, mark backdrops `aria-hidden="true"` + `pointer-events-none`, and honor `prefers-reduced-motion`.

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
- The controls slot (`data-slot="scene-controls"`) is `pointer-events-auto absolute right-3 bottom-3 left-3 z-20 flex flex-wrap items-center justify-end gap-2`, rendered **outside** the `aria-hidden` backdrop layer so HUD buttons stay keyboard- and screen-reader-accessible.

## HeroBackground Layout

`packages/ui-design-system/src/layouts/HeroBackground.tsx` is a spatially contained Voxel hero stage built strictly from Matcha & Cedar semantic tokens with sharp 0px geometry, fluid padding (zero viewport breakpoints), a CSS dot-matrix horizon texture, and an optional living-scene backdrop slot.

### Props

| Prop | Type | Default | Behavior |
|---|---|---|---|
| `gradient` | `'electric' \| 'success' \| 'catalyst' \| 'ai'` | `'electric'` | Selects the semantic accent edge (`border-voxel-bevel-hi`, `border-success/40`, `border-accent/40`, `border-info/40`). |
| `atmosphere` | `AtmospherePhase` | — | When set, applies the matching `.scene-atmosphere-*` gradient and suppresses the gradient overlay. |
| `backdrop` | `React.ReactNode` | — | Rendered in a `data-slot="hero-backdrop"` `aria-hidden` layer. |
| `children` | `React.ReactNode` | — | Hero content. |

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

`apps/web/src/features/home/backdrop/garden-renderer.ts` exports `ATMOSPHERE_PALETTES: Record<AtmospherePhase, AtmospherePalette>`, synchronized with `.scene-atmosphere-*` in `apps/web/src/styles/app.css`. Each palette defines:

- `skyStops` — 7+ vertical gradient stops (the zenith top color is unique per phase).
- `horizonGlow` — three-stop radial glow centered behind the ridge silhouette.
- `topVignette` — three-stop extended top atmospheric vignette (spanning ~86% of stage height) tuned for AAA cream-text contrast.
- `footFade` — bottom fade band color.
- `lightScale` — global voxel face brightness multiplier.
- `topTint` / `sideTint` — per-face RGB tint multipliers.
- `islandFog` — depth-fog RGB target for island faces.
- `cloudHaze` — horizon RGB that cloud faces bleach toward, and the colour of the baked horizon haze band; cloud fog is capped (`0.2` far plane, `0.1` near plane) so distance never greys them into the terrain.
- `cloudTopTint` / `cloudSideTint` — cloud-only per-face tint multipliers (warm lit tops, cool shaded flanks); terrain keeps `topTint` / `sideTint`.
- `cloudLightScale` — cloud-only exposure multiplier, so `dusk` and `after-hours` do not render sunlit clouds.
- `lanternAlphaScale` — lantern glow halo intensity.
- `showStars` / `showFireflies` / `showSunMotes` — which zenith and micro-life layers render.

## Panoramic Cedar Sanctuary Diorama (`GardenBackdrop`)

`apps/web/src/features/home/backdrop/GardenBackdrop.tsx` renders the panoramic **Cedar Sanctuary** diorama (`cedar-sanctuary`) inside `SceneStage` across Matcha & Cedar market-session atmospheres (`dawn`, `daylight`, `dusk`, `after-hours`).

### Single-World Architecture

The backdrop is a single curated world. `voxel-world.ts` exports `CEDAR_WORLD_ID = 'cedar-sanctuary'` and `CEDAR_WORLD_META` (`label`, `shortLabel`, `glowRgb`, `description`); `worlds.ts` exposes `getCedarWorldAndFaces()` as the only world entry point. There is no world registry, no `world` prop, no `particleMode` prop, and no visitor world preference — the canvas always carries `data-world={CEDAR_WORLD_ID}`. The HUD exposes only the atmosphere switcher and the motion toggle.

### Props

| Prop | Type | Default | Behavior |
|---|---|---|---|
| `className` | `string` | — | Canvas class. |
| `atmosphere` | `AtmospherePhase` | `'dusk'` | Active phase; drives sky, voxel lighting, and micro-life (`data-atmosphere`). |
| `paused` | `boolean` | — | Optional externally controlled paused state (used when the parent hosts HUD controls). |
| `onPausedChange` | `(paused: boolean) => void` | — | Notifies the parent when the reduced/paused state changes. |
| `showControls` | `boolean` | `true` | Whether to render the floating Pause/Play button inside `GardenBackdrop`. Set `false` when `SceneStage` renders HUD controls in its foreground `controls` slot. |

### Geometry & Camera Framing

- **Panoramic Voxel Grid (`voxel-world.ts`)**: `144×144×64` (`RU = 84`, `RV = 42`) with `uvToGrid` / `gridToUv` camera-space projection helpers so the floating cedar ridge stretches horizontally across wide viewports (`computeCedarFraming` in `garden-scene.ts`: ~90% desktop width at `scale = Math.min(W / 92, H / 46)`, anchoring desktop/landscape `originY = 0.68 * H` while smoothly lowering `originY` toward `0.82 * H` on portrait mobile aspect ratios `W < H` so hero CTAs stay clear above the trees) with crisp isometric tile proportions (`HW = scale * 0.5`, `HH = scale * 0.34`, `ZH = scale * 0.46`). The `createVoxelCanvas` builder exposes `putUV(u, v, z, m, glow?)` alongside `put`/`box`/`cyl`/`sphere` so world geometry can be authored in camera-aligned `(u, v)` space.
- **Twin-Bluff Cedar Sanctuary (`worlds/cedar-sanctuary.ts`)**:
  - *Left Highland Bluff*: two-story timber lodge on dressed granite foundation with warm paper windows (`windowGlow`), stone chimney, gable eaves, porch sconces, and tall Douglas pines.
  - *Central Brook Valley*: gently recessed terrain keeping foreground CTA copy readable while exposing a winding brook, arched cedar footbridge with lanterns, and an elevated timber aqueduct trestle.
  - *Right Maple & Cascade Bluff*: crimson/amber autumn maple grove, east cedar torii gate, granite path lanterns, and a cliffside waterfall plunge (`carveCliffWaterfall`).
- **Flanking Under-crust & Clouds (`worlds/shared-terrain.ts`)**: `buildPanoramicUndercrust` tapers the underside granite cone and hanging roots across `RU`/`RV`, and `buildStandardClouds` places 6 field-carved cloud puffs (3–4 overlapping lobe domes each, flat bottomed) across the open-sky flanks, clear of the CTA corridor. Every cloud registers its own material group (`cloudGroupOf`), so `bakeCloudSprites` can crop each one into an individual canvas. `createVoxelCanvas` exposes `cloudPuff(u, v, z0, halfU, halfV, mats, plane)` (replacing the old rectangular `cloudSlab`) and `cloudMat(hex, far, group)` which records each cloud's material group in `cloudGroupOf`.

### Homepage & Diagnostic Integration

- `apps/web/src/features/home/pages/HomeCtaPage.tsx`, `apps/web/src/features/personality/PersonalityQuizPage.tsx`, and `apps/web/src/features/recipes/builder/BuilderChatPanel.tsx` (Steps 1–2 of `/build`) share `useDioramaStage(initialAtmosphere)` (`apps/web/src/features/home/backdrop/useDioramaStage.ts`) initialized synchronously from route loaders (avoiding SSR/CSR flicker) plus `SceneHudControls.tsx` (`Sky: <Phase>`, `Pause motion`/`Play motion`). Once compiled, `CompiledBotWorkspace.tsx` transitions onto the fixed dot-matrix `GlobalBackground` inside `PageLayout`.
- **Single-Island SSR -> CSR Stepped Build-In**: `GardenBackdrop` matches the SSR atmospheric sky immediately, then animates the single `sortKey`-sorted `island` canvas via [`computeIslandRevealFrame`](apps/web/src/features/home/backdrop/garden-scene.ts) — clipping upwards in quantized isometric voxel block columns (`stepPx = Math.max(4, Math.round(scale * 2.2))`) over `1.1s` (`ENTRANCE_DURATION_S`) with zero painter-order seams and zero extra GPU canvas buffers before settling cleanly into unclipped steady-state rendering. Clouds and particles fade in over the upper half (`computeAmbientEntranceAlpha`). `GardenBackdrop` tracks reveal lifecycle via a discrete `EntranceState` union (`'animating' | 'settled'`), skipping straight to `'settled'` under `prefers-reduced-motion` or explicit pause.

### 4-Plane Depth Parallax & Micro-Life

`drawCedarSceneFrame` (`apps/web/src/features/home/backdrop/garden-scene.ts`) composites four depth planes back-to-front:

1. **Atmospheric sky** — phase-baked gradient plus `drawZenithParticles` (twinkling stars for dusk/after-hours, drifting sun-motes for dawn/daylight).
2. **Far cloud sprites** — one cropped canvas per cloud, drifting outward from the copy at `CLOUD_DRIFT_SPEED.far` (`3px/s`) with subtle parallax.
3. **Panoramic cedar island** — gentle vertical levitation (`sin(time * 0.45)`) plus surface water glints (`drawSurfaceGlints`), brook/pool ripples (`drawSurfaceRipples`), warm amber lantern glow halos (`drawBeaconHalos`), dusk/night fireflies (`drawFireflies`), soft drifting haze wisps (`drawCedarMistAndLeaves`), and falling autumn maple leaves (`drawCedarMistAndLeaves`).
4. **Near cloud sprites** — faster outward drift (`7px/s`) plus deeper parallax; `cloudAlphaAt` dissolves any cloud that shares the hero copy's rows before its lane reaches the copy column, so a drifting cloud is never readable behind the headline, and `cloudAlphaAt` returns `1` for every cloud on portrait viewports where the band sits below the copy.

Offscreen layers are built by `buildCedarScene` (`garden-scene.ts`) once per mount/resize/atmosphere change and disposed on rebuild. `getCedarWorldAndFaces()` (`worlds.ts`) caches face extraction and calls `stripWorldBuffers` to free raw occupancy buffers once extracted. `disposeCanvas` / `disposeSceneCanvases` (`garden-renderer.ts`) zero offscreen canvas storage on rebuild and unmount.

### Cloud Sprite System (`garden-renderer.ts`)

Each cloud is baked into its own cropped canvas so it can drift and fade independently instead of sharing one full-stage layer with five neighbours:

- `bakeCloudSprites(faces, world, dims, project, atmosphere)` groups cloud faces by `world.cloudGroupOf` (material id → cloud group index, registered by `cloudMat(hex, far, group)`), sorts groups, and calls `bakeOneCloud` per group. `bakeOneCloud` measures the screen-space bounding box (`measureBounds`), crops a padded canvas, and paints faces with `traceVoxelFace` + `shadeFaceRgb`.
- `computeCloudLane(x, y, width, height, stageWidth, stageHeight)` returns a `CloudLane { min, max, fadeAt }`. A cloud whose rows overlap `CLOUD_CLEAR_CORRIDOR` (`minX 0.33`, `maxX 0.67`, `minY 0.08`, `maxY 0.55`) gets the flank it already sits on and `fadeAt` pointing at the copy edge; a cloud clear of the copy rows (all of them on portrait) gets the full stage with `fadeAt: null`.
- `cloudDriftAt(lane, speed, phase, time)` wraps position within the lane span; flank clouds get a signed speed (`-baseSpeed` for left, `+baseSpeed` for right) so they drift outward from the copy.
- `cloudAlphaAt(sprite, lane, x)` dissolves over the last `max(24, min(48, width * 0.12))` px before the copy-facing lane end, returning `1` everywhere when `fadeAt` is null.
- `CLOUD_DRIFT_SPEED` is `{ far: 3, near: 7 }` CSS px/s; `CloudSprite` carries `canvas`, `x`, `y`, `width`, `height`, `lane`, `phase`, `speed`, `parallax` (far `1.4`, near `2.6`).

`Scene.cloudsFar` / `Scene.cloudsNear` are `CloudSprite[]`; `disposeSceneCanvases` disposes every sprite canvas.

### Cedar Particle Palette

`garden-renderer.ts` owns the single authoritative particle color set for the Cedar Sanctuary world:

```ts
const CEDAR_PARTICLE_COLORS = {
    driftColors: ['#e89648', '#f2c86b', '#d96b34'],
    floaterColors: ['#c6f2bd', '#ffd880'],
    glintHex: '#d6ecea',
    rippleHex: '#cceae4',
};
```

`pickCedarDriftColor(index)` cycles the three autumn leaf tints and `pickCedarFloaterColor(index)` cycles the two firefly tints, so `GardenBackdrop` layer baking and the canvas particle renderer draw from one palette instead of a per-world preset registry. Ripple kinematics are fixed (`time * 0.58`), and lantern halos scale directly from the palette's `lanternAlphaScale`.

## CSS Foundations (`apps/web/src/styles/app.css`)

- `.voxel-dot-matrix` — radial-gradient dot texture at 20px spacing.
- `.scene-atmosphere-dawn` / `-daylight` / `-dusk` / `-after-hours` — layered Matcha & Cedar CSS backgrounds combining the extended top contrast vignette (to ~86% height), bottom radial horizon glow, and linear sky stops matching `ATMOSPHERE_PALETTES`.
- `.scene-scrim` — semi-opaque Matcha backing (`rgba(20, 28, 24, 0.88)`), zero `backdrop-blur`.
- `.scene-stage-hero` (`min-height: 20rem`) / `.scene-stage-footer` (`min-height: 11rem`).
- `.scene-stage-hero.home-hero-viewport` — `min-height: calc(100dvh - 3.875rem)` so the homepage hero fills the viewport below the sticky navbar.
- `@media (prefers-reduced-motion: reduce)` disables animation/transition on `.scene-backdrop` and descendants.

## Testing & Verification

- `packages/ui-design-system/src/lib/atmosphere.test.ts` — verifies all four phases, EST/EDT boundaries, local-mode thresholds, and `NaN` fallback to `dusk`.
- `apps/web/src/test/scene-stage.test.tsx` — verifies hero/footer landmarks, default `dusk` atmosphere, `data-motion-role`, `aria-hidden` backdrop, scrim panel without `backdrop-blur`, `HeroBackground` atmosphere/backdrop slots, and wrapped `controls` slot.
- `apps/web/src/test/design-standardization.test.tsx` — verifies `SceneStage` containment/scrim invariants and `HeroBackground` token discipline.
- `apps/web/src/features/home/backdrop/GardenBackdrop.test.tsx` & `apps/web/src/features/home/backdrop/garden-scene.test.ts` — verify `data-world={CEDAR_WORLD_ID}`, `data-atmosphere`, all 4 distinct `ATMOSPHERE_PALETTES`, controlled props + `showControls={false}`, reduced-motion toggle, non-zero canvas lifecycle + mid-entrance settle, listener cleanup, portrait mobile `computeCedarFraming` lowering, bounded canvas coordinates (`computeIslandVerticalBounds`), stepped entrance reveal kinematics, and 10 offscreen canvases (sky, foot, island, lantern sprite + one cropped canvas per cloud).
- `apps/web/src/features/home/backdrop/garden-renderer.test.ts` — verifies `computeCloudLane` flank assignment (left `fadeAt: 'end'`, right `fadeAt: 'start'`, full-stage `fadeAt: null` for clouds clear of the copy rows), `cloudAlphaAt` full opacity on frame one and zero at the copy-facing lane end, no flank cloud ever overlapping the copy column across its cycle, outward drift direction, gap-free wrap, near clouds faster than far, and full opacity for clouds below the copy band (portrait).
- `apps/web/src/features/home/backdrop/worlds.test.ts` — verifies panoramic `cedar-sanctuary` seed determinism, horizontal `gridToUv` span (`>= RU * 1.8`), puffy stepped cloud silhouettes (crown inset `<= 0.75` of base, crown bbox fill `<= 0.92`, base `z >= 24`, no cloud within 3 voxels of terrain), and the under→mid→top tone ramp (top `<= 0.3`, mid `>= 0.45`, under `<= 0.35`).
- `apps/web/src/features/home/pages/HomeCtaPage.test.tsx` — verifies the `SceneStage` hero shell, `initialAtmosphere` SSR/CSR parity, open-sky 3-CTA stack (`home-cta-actions`, zero `.scene-scrim` card container or trust bullets), HUD atmosphere/motion controls with no `world-switcher`, and `/personality` link.
- `apps/web/src/features/personality/personality-data.test.ts` & `apps/web/src/features/personality/PersonalityQuizPage.test.tsx` — verify the 16-question 4-axis diagnostic scoring engine, full 16-archetype reachability, starter recipe integrity, top-2 bot matches linking to `/build?idea=`, `?archetype=` hydration, and `cedar-sanctuary` stage parity.

## Related

- [[entities/design-system]] — the shared UI design system and its component inventory
- [[concepts/cumulative-layout-shift]] — zero SSR/CSR divergence and visual stability rules
- [[concepts/rendering-strategies]] — SSR, Hybrid SSR, and CSR architecture
- [[concepts/fluent-responsive-design]] — fluid, breakpoint-free layout conventions
- [[entities/personality-quiz]] — the `/personality` diagnostic rendered over Cedar Sanctuary
- [[entities/web-app]] — the TanStack Start client dashboard
