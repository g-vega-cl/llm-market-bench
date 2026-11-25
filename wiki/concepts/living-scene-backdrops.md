---
tags: [design-system, ui, animation, performance, accessibility, voxel, atmosphere]
category: concept
---

# Living Scene Backdrops & Expressive Motion

Expressive animated backdrops are permitted across **major page heroes and parallax footers** while preserving legibility, Voxel geometry, and performance. The architecture separates sky, midground scenery, and independent procedural micro-entities into discrete layers, clips them inside contained stages, and protects foreground CTAs with opaque Matcha scrims — never glassmorphism blur — or with extended top atmospheric sky vignettes. This concept is codified in `.agents/rules/design-spec.md` §12 and implemented by the `SceneStage` / `HeroBackground` layouts plus the `atmosphere` utility in `packages/ui-design-system`.

## Core Principles

1. **Modular layered dioramas + ambient life** — Separate sky, midground scenery, and independent procedural micro-entities (clouds, fauna, footer sprites) into discrete layers. Never flat looping videos or static baked clips.
2. **Containment & CTA legibility (zero glassmorphism)** — Clip animated stages inside `SceneStage` / `HeroBackground` (`overflow-hidden isolate`) with hard scroll ceilings so motion never bleeds into data tables. Protect foreground UI either with opaque/semi-opaque Matcha surfaces (`.voxel-btn`, `.scene-scrim` / `.voxel-card`, never `backdrop-blur`) or with extended top atmospheric sky vignettes maintaining accessible contrast (`>= 4.5:1` AA / `>= 7:1` AAA) with central diorama sightlines clear of bright cloud slabs.
3. **Zero SSR/CSR flash & CLS invariance** — Route loaders (`apps/web/src/routes/index.tsx`, `apps/web/src/routes/personality.tsx`, `apps/web/src/routes/build.tsx`, `apps/web/src/routes/recipes/$recipeId/index.tsx`, `apps/web/src/routes/recipes/live/$recipeId.tsx`) resolve the US Eastern market atmosphere (`resolveAtmospherePhase(new Date(), 'market-et')`) server-side and pass `initialAtmosphere` into `useDioramaStage(initialAtmosphere)`. CSS `.scene-atmosphere-*` gradients match `ATMOSPHERE_PALETTES` stops pixel-for-pixel, and `<canvas>` cross-fades in cleanly once the first frame paints so SSR and CSR never produce layout shifts or sky flashes. See [[concepts/cumulative-layout-shift]].
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
| `backdrop` | `React.ReactNode` | — | Rendered in a dedicated `aria-hidden` `pointer-events-none` layer behind children. Backdrops implement the shared `SceneBackdropProps` contract (`atmosphere`, `motion`, `className`) so a surface picks a world instead of inventing a prop shape. |
| `controls` | `React.ReactNode` | — | Accessible foreground HUD controls (`data-slot="scene-controls"`) anchored to the bottom-right stage corner outside `aria-hidden`. |
| `children` | `React.ReactNode` | — | Foreground content. |

### Exported Contracts

`SceneStage.tsx` also owns the two types every backdrop and HUD shares, both re-exported from `packages/ui-design-system/src/index.ts`:

- **`SceneMotion`** — `'running' | 'paused' | 'reduced'`. The single derived motion state a scene has. `reduced` means the operating system asked for reduced motion, so the UI must never offer to un-freeze the scene.
- **`SceneBackdropProps`** — `{ atmosphere: AtmospherePhase; motion: SceneMotion; className?: string }`. The contract every `SceneStage` backdrop implements, so a new surface picks a world rather than inventing a third prop shape. `GardenBackdrop` declares its props as `type XProps = SceneBackdropProps`; `CedarRidgeBackdrop` extends it with its own `fauna` axis (see below), which keeps it assignable to the contract while letting the world read one bot fact.

### Structural Guarantees

- Root element carries `data-slot="scene-stage"`, `data-stage-variant`, `data-backdrop-mode`, `data-atmosphere`, and `data-motion-role`, plus `relative isolate overflow-hidden rounded-none`.
- Backdrop layer (`data-slot="scene-backdrop"`) is `aria-hidden="true"`, `pointer-events-none`, `absolute inset-0 z-0 overflow-hidden`, and only rendered when `backdrop` is supplied.
- Foreground content sits in a `relative z-10 mx-auto w-full max-w-7xl min-w-0` wrapper.
- The scrim panel (`data-slot="scene-scrim"`) uses `scene-scrim voxel-card rounded-none p-6 min-w-0` and never `backdrop-blur`.
- The controls slot (`data-slot="scene-controls"`) is `pointer-events-auto absolute right-3 bottom-3 left-3 z-20 flex flex-wrap items-center justify-end gap-2`, rendered **outside** the `aria-hidden` backdrop layer so HUD buttons stay keyboard- and screen-reader-accessible.
- **`backdropMode="page"`** changes three of the four: the stage drops `isolate overflow-hidden` and the viewport band for `relative z-10` + padding only; the backdrop wrapper becomes `fixed inset-0 z-0 overflow-hidden` and carries the `.scene-atmosphere-*` sky (the stage must not paint one); and the controls slot becomes an in-flow `flex … justify-end` row inside the stage, under the card, so a floating HUD can never sit on top of the tab's own content. The host page is then responsible for putting its content in `relative z-10` layers. Bot detail pages do exactly this through `BotSceneShell`, which renders the world, a back link and the sub-nav, and deliberately passes no `controls` slot — the HUD sits in its header row so it does not create a separate band between the sub-nav and the panel.

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

`apps/web/src/features/home/backdrop/garden-renderer.ts` exports `ATMOSPHERE_PALETTES: Record<AtmospherePhase, AtmospherePalette>`, synchronized with `.scene-atmosphere-*` in `apps/web/src/styles/app.css`. Each palette defines the sky stops, horizon glow, top vignette, foot fade, light scale, per-face tints, island fog, cloud haze/tints/light scale, lantern alpha scale, and which zenith/micro-life layers render (`showStars` / `showFireflies` / `showSunMotes`).

## Panoramic Cedar Sanctuary Diorama (`GardenBackdrop`)

`apps/web/src/features/home/backdrop/GardenBackdrop.tsx` renders the panoramic **Cedar Sanctuary** diorama (`cedar-sanctuary`) inside `SceneStage` across Matcha & Cedar market-session atmospheres. It is a single curated world (`CEDAR_WORLD_ID = 'cedar-sanctuary'`), with a `144×144×64` panoramic voxel grid, twin-bluff geometry (left highland lodge, central brook valley, right maple & cascade bluff), flanking under-crust and 6 field-carved cloud puffs, a 4-plane depth parallax (sky + zenith particles, far cloud sprites, panoramic cedar island, near cloud sprites), a single-island SSR→CSR stepped build-in reveal, and calm micro-life (fireflies, brook ripples, lantern halos, drifting haze, autumn leaves, sky motes). Offscreen layers are baked once per mount/resize/atmosphere change and disposed on rebuild; the 30fps-capped rAF loop stops on idle, on `document.hidden`, and for `prefers-reduced-motion` users. Face extraction is cached once per session via `getCedarWorldAndFaces()`.

`GardenBackdrop` is the backdrop for the homepage hero (`HomeCtaPage`) and the `/personality` diagnostic. The homepage stage is a true viewport via `.home-hero-viewport`; `/personality` instead relies on a `min-h-[calc(100dvh-3.875rem)]` utility on `SceneStage`, which loses to `.scene-stage-hero { min-height: 20rem }` — its stage renders content-height (measured 781 px against 938 px available at 1600×1000), so the island is framed by the copy rather than by the viewport. It is **no longer** mounted by the shared bot header: the Recipe Studio surfaces (`/recipes/$recipeId`, `/recipes/$recipeId/edit`, `/recipes/live/$recipeId`) moved to `CedarRidgeBackdrop` in a one-viewport stage, because the canvas world's island composition cropped into a short band read as a floating garden with no horizon and no ground. See [[entities/recipe-studio]].

It is **fully controlled**: `GardenBackdropProps` is `SceneBackdropProps` (`atmosphere`, `motion`, `className`), the canvas carries `data-world`, `data-atmosphere`, and `data-motion`, and the component renders no HUD of its own — the former `paused` / `onPausedChange` / `showControls` props and the internal `Pause motion` button are gone, because a backdrop-owned toggle was a second owner of the same state. The canvas settles when `motion !== 'running'` or when the OS preference is set, and resumes when the host reports `running` again.

## Cedar Ridge Layered Backdrop (`CedarRidgeBackdrop`)

`/build` and the three bot tabs mount a second, canvas-free world inside the same `SceneStage` backdrop slot: `apps/web/src/features/home/backdrop/CedarRidgeBackdrop.tsx` renders six stacked DOM/CSS/SVG planes, so those surfaces pay for no canvas, no GL context and no offscreen baking while still reading as a living landscape. Its composition is deliberately horizon-first — a ground plane pinned to the stage's bottom edge with the fauna walking on it — which is what the bot pages needed: the canvas island cropped into a short band read as a floating garden.

### Composition

| Plane | Contents | `--cr-depth` |
|---|---|---|
| 0 | seven twinkling stars + `CedarMoon` stepped pixel disc | `0.05` |
| 1 | three drifting cloud slabs + a gliding bird | `0.12` |
| 2 | far mountain range with amber horizon haze | `0.20` |
| 3 | pine ridge + lookout tower (ladder, railings, lit cabin) | `0.36` |
| 4 | forest floor: lit band, dot matrix, near-fade gradient, swaying grass | `0.56` |
| 5 | meadow fauna via `CedarMeadowFauna`: lantern-bot, fox, four fireflies | `0.74` |

### Component decomposition

- `CedarRidgeBackdrop.tsx` — the `data-testid="cedar-ridge-backdrop"` root (`data-world="cedar-ridge"`) with the six `.cr-layer` planes, the `RIDGE` paint constant, and `SceneBackdropProps` plus this world's own `fauna?: 'walking' | 'standby'` (default `'walking'`), emitted as `data-fauna` alongside `data-atmosphere` and `data-motion`. Geometry lives in the component; surface colour comes from tokens (`--color-accent`, `--color-voxel-ink`, `--color-voxel-bevel-hi`, `--color-voxel-muted`, `--color-voxel-trough`, `bg-voxel-surface`).
- `CedarMoon.tsx` — a stepped 14×14 pixel moon drawn as `<rect>` rows (not a circle, so the silhouette matches the pixel-art world) with three craters in `--color-accent-dark`, wrapped in a `.cr-moon-halo` soft radial halo; root is `.cr-celestial`, which the atmosphere rules move vertically.
- `CedarMeadowFauna.tsx` — the plane-5 fauna: a left-patrolling lantern-bot (`cr-bot` + `cr-bot-glow`), a right-patrolling fox (`cr-fox` + `cr-fox-glow`), and four `.cr-firefly` dots (two solid `bg-accent`, two `cr-firefly--pale` at `bg-accent/70`) with staggered negative `animation-delay`s. Both SVGs are `aria-hidden` + `focusable="false"`.

### Drift and ambient loops

- `useCedarRidgeDrift.ts` samples the pointer (and page scroll) once per `requestAnimationFrame` and writes only two custom properties, `--cr-px` / `--cr-py`, on the backdrop root. Every plane multiplies them by its own `--cr-depth` in one CSS `transform`, so six planes move from two style writes. Constants: `POINTER_PX = 56` (pointer travel at depth 1, y at half strength), `SCROLL_PX = 18` (extra downward drift at full scroll), `SCROLL_RANGE_PX = 400` (scroll distance to reach full strength). It derives the offset from the last pointer sample plus the current `scrollY` instead of accumulating it, so replaying a scroll event at an unchanged `scrollY` yields the same value, and it settles back to centre while frozen (`motion !== 'running'`), on `prefers-reduced-motion`, and on `visibilitychange` when the tab is hidden.
- Ambient loops and the plane transforms live in `apps/web/src/styles/cedar-ridge.css` (imported by `app.css` directly after Tailwind, wrapped in `@layer utilities` so the global sheet stays under the 800-line ceiling and the scene rules still outrank generated utilities): `cr-drift` (clouds, 96s/132s/168s with negative delays so the bank never starts bunched), `cr-glide` (bird), `cr-patrol-bot` / `cr-patrol-fox` (opposed patrols with a `scaleX` turn) plus their shared `cr-bob` gait, `cr-twinkle`, `cr-firefly`, `cr-sway`.
- Scene paint is token-derived, not retyped: `.cr-horizon-haze`, `.cr-moon-halo`, `.cr-bot-glow`, `.cr-fox-glow` build their radial/linear gradients with `color-mix(in oklab, var(--color-accent) …%, transparent)`; `.cr-near-fade` uses a fixed dark fade; `.cr-firefly` adds a `box-shadow` glow from `--color-accent` and `cr-firefly--pale` from `--color-accent-light`; `.cr-ground` paints the 24px radial dot matrix.
- `data-motion` on the root (`running` / `paused` / `reduced`) sets `animation-play-state: paused` for the whole subtree, so the HUD control freezes the world without unmounting it; the same state also resets `.cr-layer { will-change: auto }` so a frozen scene holds no compositor backing store. `@media (prefers-reduced-motion: reduce)` still kills the loops through the shared `.scene-backdrop` rule (and drops `will-change` on `.cr-layer`).
- `data-fauna` (`walking` / `standby`) is the **bot's own schedule read as motion**, not a second status surface: `standby` pauses the two patrols and their shared `.cr-bob` gait (the `steps(2, end)` hop the bot and fox walk with — it is not a separate ambient loop), drops the two `.cr-beacon` rects (tower window and the bot's antenna light) to `0.35` opacity, and leaves the rest of the world running — clouds, bird, stars, fireflies, grass. A paused bot still reads as a world with weather; only the walk and the beacon stop. No words are rendered here, so the header badge stays the single status owner. The beacon's 600ms opacity fade is itself suppressed under `[data-motion="paused"]`/`reduced`, so a visitor who froze the scene never sees the beacon animate underneath them.
- Atmosphere changes **exposure only** — star opacity (`0.65` default, `0.35` dawn, `0` daylight, `1` after-hours) and moon height (`-2.625rem` after-hours, `-4.5rem` daylight) via `.cedar-ridge[data-atmosphere=…]`, never geometry — so a sky cycle cannot reshuffle the composition.
- `.build-stage-viewport` gives the stage `min-height: calc(100dvh - 3.875rem)` (the `min-h-[…]` utility it replaced lost to `.scene-stage-hero`) and narrows the stage padding to a fluid clamp, which is what keeps the horizon band on screen below the builder card.
- `cedar-ridge.css` also owns the builder stepper's container query: `.build-stepper { container-type: inline-size }` and `@container (max-width: 22rem) { .build-step-subtitle { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap } }` — below 22rem of card width the step descriptions leave the layout but stay in the accessibility tree, so the information loss is width-driven rather than viewport-driven (the design-spec breakpoint ban).

## Motion Ownership (`useDioramaStage`)

`useDioramaStage` owns the only motion state a scene has: it derives `motion: SceneMotion` (`'running' | 'paused' | 'reduced'`) from the visitor's toggle and `prefers-reduced-motion` (via `useSyncExternalStore`, with a `false` server snapshot so hydration matches), and `SceneHudControls` renders from that. `reduced` means the OS asked for it, so the HUD reads "Motion: reduced" and the toggle is inert — offering "Pause motion" over an already-frozen scene is the bug this state removes. The query lives in the hook rather than in a backdrop because every host renders the same HUD; a backdrop that owned it could only fix its own page (that is how `/build` ended up offering "Pause motion" over a frozen scene).

`toggleMotion()` cannot un-freeze a scene the OS froze: when `reduced` is true the setter returns the previous value, so the two sources can never disagree about whether the scene is moving.

`SceneHudControls` (`apps/web/src/features/home/backdrop/SceneHudControls.tsx`) takes `{ atmosphere, motion, onCycleAtmosphere, onTogglePaused }` and renders the sky switcher plus a motion toggle carrying `data-testid="motion-toggle"`, `data-motion={motion}`, and `aria-pressed={motion === 'paused'}`. Its label is `Pause motion` while running, `Play motion` while paused, and `Motion: reduced` (with `disabled`) under the OS preference.

Both backdrops take their **motion** from that prop: `GardenBackdrop` settles its canvas when `motion !== 'running'` and no longer exposes `onPausedChange`/`showControls`, and `CedarRidgeBackdrop` sets `data-motion` so CSS freezes the loops. `CedarRidgeBackdrop` additionally takes its own `fauna` input, which is a bot fact rather than a motion state — the motion prop still outranks it, because a frozen scene pauses everything.

## CSS Foundations (`apps/web/src/styles/app.css`)

- `.voxel-dot-matrix` — radial-gradient dot texture at 20px spacing.
- `.scene-atmosphere-dawn` / `-daylight` / `-dusk` / `-after-hours` — layered Matcha & Cedar CSS backgrounds combining the extended top contrast vignette (to ~86% height), bottom radial horizon glow, and linear sky stops matching `ATMOSPHERE_PALETTES`.
- `.scene-scrim` — semi-opaque Matcha backing (`rgba(20, 28, 24, 0.88)`), zero `backdrop-blur`.
- `.scene-stage-hero` (`min-height: 20rem`) / `.scene-stage-footer` (`min-height: 11rem`).
- `.scene-stage-hero.home-hero-viewport` and `.scene-stage-hero.build-stage-viewport` (declared in `cedar-ridge.css`, two classes deep so they outrank `.scene-stage-hero`) — `min-height: calc(100dvh - 3.875rem)` so the homepage hero and the `/build` stage fill the viewport below the sticky navbar; the build variant adds a `clamp()` top/bottom padding so the builder card gives the ridge band the screen space a phone cannot spare. The bot header deliberately does **not** use a viewport class: it runs `backdropMode="page"` (see above), where the world is a fixed layer and the stage is content-height, so the tab's panel starts 24 px under the card instead of at the fold.
- `.cedar-ridge .cr-layer` — one `translate3d()` per plane built from `--cr-px` / `--cr-py` × `--cr-depth`, with a 180ms follow transition; `.cedar-ridge[data-motion="paused"] *` and `[data-motion="reduced"] *` pause every ambient loop, and the same two selectors reset `.cr-layer { will-change: auto }`.
- `@media (prefers-reduced-motion: reduce)` disables animation/transition on `.scene-backdrop` and descendants.

## Testing & Verification

- `packages/ui-design-system/src/lib/atmosphere.test.ts` — verifies all four phases, EST/EDT boundaries, local-mode thresholds, and `NaN` fallback to `dusk`.
- `apps/web/src/test/scene-stage.test.tsx` — verifies hero/footer landmarks, default `dusk` atmosphere, `data-motion-role`, `aria-hidden` backdrop, scrim panel without `backdrop-blur`, `HeroBackground` atmosphere/backdrop slots, and wrapped `controls` slot.
- `apps/web/src/test/design-standardization.test.tsx` — verifies `SceneStage` containment/scrim invariants and `HeroBackground` token discipline.
- `apps/web/src/features/home/backdrop/useDioramaStage.test.tsx` — verifies the derived motion state: starts `running`, toggles to `paused` and back, the OS preference outranks the visitor toggle (`reduced` survives `toggleMotion()`), and `cycleAtmosphere()` advances the SSR-resolved atmosphere (`dusk` → `after-hours`).
- `apps/web/src/features/home/backdrop/SceneHudControls.test.tsx` — verifies the HUD motion toggle per state: `Pause motion` with `aria-pressed="false"` while running, `Play motion` with `aria-pressed="true"` while paused, and `Motion: reduced` + `disabled` + `data-motion="reduced"` under the OS preference; also asserts the sky switcher label (`Sky: After-Hours`).
- `apps/web/src/features/home/backdrop/CedarRidgeBackdrop.test.tsx` — verifies the six `.cr-layer` planes, `data-world="cedar-ridge"` / `data-atmosphere` / `data-motion`, the moon plus bot, fox and four fireflies, atmosphere passthrough for all four phases, motion passthrough (`running` / `paused` / `reduced`), the fauna axis (defaults to `walking`, flips to `standby`, two `.cr-beacon` rects present), pointer drift written into `--cr-px` / `--cr-py`, no drift and a centred settle while paused or under reduced motion, the derived (non-accumulating) scroll term (`--cr-py` ≈ `-18` at `scrollY = 900`), and the settle-to-centre on `visibilitychange` while hidden.
- `apps/web/src/features/home/backdrop/GardenBackdrop.test.tsx` & `garden-scene.test.ts` — verify `data-world={CEDAR_WORLD_ID}`, `data-atmosphere`, `data-motion`, all 4 distinct `ATMOSPHERE_PALETTES`, the `SceneBackdropProps` contract (no internal HUD button renders), freezing while the host reports a non-running motion and resuming when it runs again, no rAF start when `prefers-reduced-motion` races a `running` host or when the host is frozen, non-zero canvas lifecycle + mid-entrance settle on a host-driven freeze, listener cleanup, portrait mobile `computeCedarFraming` lowering, bounded canvas coordinates, stepped entrance reveal kinematics, and 10 offscreen canvases.
- `apps/web/src/features/home/backdrop/garden-renderer.test.ts` — verifies `computeCloudLane` flank assignment, `cloudAlphaAt` full opacity on frame one and zero at the copy-facing lane end, outward drift direction, gap-free wrap, near clouds faster than far, and full opacity for clouds below the copy band (portrait).
- `apps/web/src/features/home/backdrop/worlds.test.ts` — verifies panoramic `cedar-sanctuary` seed determinism, horizontal `gridToUv` span, puffy stepped cloud silhouettes, and the under→mid→top tone ramp.
- `apps/web/src/features/home/pages/HomeCtaPage.test.tsx` — verifies the `SceneStage` hero shell, `initialAtmosphere` SSR/CSR parity, open-sky 3-CTA stack, HUD atmosphere/motion controls with no `world-switcher` (under the suite's mocked reduced-motion preference the toggle reads `Motion: reduced` and is disabled), and `/personality` link.
- `apps/web/src/features/personality/personality-data.test.ts` & `PersonalityQuizPage.test.tsx` — verify the 16-question 4-axis diagnostic scoring engine, full 16-archetype reachability, starter recipe integrity, top-2 bot matches linking to `/build?idea=`, `?archetype=` hydration, and `cedar-sanctuary` stage parity.
- `apps/web/src/features/recipes/builder/BuilderChatPanel.test.tsx` — verifies the panel renders on `SceneStage` with `CedarRidgeBackdrop` (`cedar-ridge-backdrop` carrying `data-atmosphere`), starter chips, the 3-step stepper, and the signed-out draft hint in the panel footer.

## Related

- [[entities/design-system]] — the shared UI design system and its component inventory
- [[concepts/cumulative-layout-shift]] — zero SSR/CSR divergence and visual stability rules
- [[concepts/rendering-strategies]] — SSR, Hybrid SSR, and CSR architecture
- [[concepts/fluent-responsive-design]] — fluid, breakpoint-free layout conventions
- [[entities/personality-quiz]] — the `/personality` diagnostic rendered over Cedar Sanctuary
- [[entities/recipe-studio]] — the studio, Bot Overview, and `/build` builder that host the two backdrops
- [[entities/web-app]] — the TanStack Start client dashboard
