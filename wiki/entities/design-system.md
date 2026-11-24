---
tags: [design-system, component-library, ui]
category: entity
---

# Design System

The `@llm-market-bench/ui-design-system` package provides the shared UI component library for the web dashboard. It enforces the tactile **Matcha & Cedar / Cheddar Voxel** aesthetic inspired by voxel hardware geometry and editorial clarity.

## Design rules cheat sheet

1. **CSS-first layout (Avoid JS for design)**: All 1D and 2D layouts must use declarative CSS Grid and Flexbox (`grid`, `flex`, `flex-wrap`, `items-stretch`). Never use JavaScript (`window.innerWidth`, `matchMedia`, `ResizeObserver`) to calculate column counts, dimensions, or responsive stacking modes. Zero inline `style={{ ... }}` objects for layout, typography, or colors (only dynamic data percentage bars permitted). See [`.agents/rules/design-spec.md`](file:///home/cv/Documents/Code/llm-market-bench/.agents/rules/design-spec.md).
2. **Topbar 3-item budget & uniform button sizing**: The global navigation bar in `apps/web/src/routes/__root.tsx` displays strictly 3 items: `B` (Home), a briefcase SVG icon (Portfolios), and a conical flask SVG icon (Lab). Zero sidebars are allowed. Rule #7 (zero decorative emojis) applies — icons are inline SVG, not emoji. All buttons in the navbar must always be the same size: primary nav items use identical square dimensions (`h-9 w-9`, `inline-flex items-center justify-center`), and the trailing auth button (`Login` / `Logout`) matches the exact same square dimensions (`h-9 w-9 shrink-0`) and renders an inline SVG icon (`LoginIcon` / `LogoutIcon`) with `aria-label` and `title` instead of visible text.
3. **Page 3-block budget**: Any page may render at most 3 major blocks. `Home` renders 2 blocks, `Portfolios` renders 3 blocks, and `Lab` renders 3 category blocks.
4. **Row 3-stat budget**: Every table row or card slot displays at most 3 data points.
5. **Zero cards inside cards**: Raised `.voxel-card` surfaces never nest inside another `.voxel-card`. Inner metrics use recessed `.voxel-trough` slots.
6. **Zero collapsibles or accordions**: Content that belongs on a page renders flat and visible immediately. Secondary telemetry lives in `/lab`.
7. **Zero decorative emojis in UI chrome**: Section headers, metric labels, and buttons use crisp typography and square pixel indicators instead of emojis.
8. **Sharp Voxel geometry**: Corners use `rounded-none` with 2px directional bevels (`border-voxel-bevel-hi` on top and left, `border-voxel-bevel-lo` on right and bottom) and hard `4px 4px 0px` offset shadows.
9. **Strict 3-combination typography budget**: The interface standardizes on at most 3 font size and boldness combinations across all chrome and content:
   - **Tier 1 (Display & Headings)**: `18px Bold` (`text-lg font-bold`, `.type-heading`) for page titles (`h1`), `h2`, and `SectionHeading`.
   - **Tier 2 (Controls & Cards)**: `14px Bold` (`text-sm font-bold`, `.type-control`) for buttons, card titles, table headers, badges, and prominent values.
   - **Tier 3 (Content & Telemetry)**: `12px Normal` (`text-xs font-normal`, `.type-body`) for body copy, table cells, timestamps, and thought traces.
10. **Standardized equal box sizing**: All cards inside grids and composite blocks enforce matched dimensions using fluid CSS Grid (`grid grid-cols-[repeat(auto-fit,minmax(theme(spacing.72),1fr))]`) and `items-stretch` so boxes in a section share identical height and width without awkward trailing wraps.
11. **Zero manual child margins ("Flow & Gaps Only")**: Individual elements and components must never declare exterior margins (`m-*`, `mb-*`, `mt-*`, `mr-*`, `ml-*`). Spacing between items is strictly owned by parent containers using `flex gap-*` or `grid gap-*` with a 3-step scale: `gap-2` (8px, micro inline elements), `gap-4` (16px, intra-card/controls), and `gap-6` (24px, inter-card/sections). The only permitted margin utilities are flex edge anchors (`mt-auto` to pin footer blocks to bottom of cards, `ml-auto` to push controls rightward in ribbons).
12. **Zero hardcoded widths and heights ("Intrinsic Fluid Sizing")**: Avoid rigid fixed dimensions (`w-[...]`, `h-[...]`, `min-w-72`). Multi-column card panels size horizontally via fluid CSS Grid tracks (`repeat(auto-fit, minmax(min(100%, 18rem), 1fr))`) and flex wrappers (`flex-1 basis-96 min-w-0`). Vertical dimensions flow intrinsically from content + padding + container gap.
13. **High-contrast indicator and badge semantics**: Contrast between badge text and background must meet or exceed WCAG AAA ($\ge 7:1$). Cheddar Gold (`bg-accent`) solid tags must use dark trough text (`text-voxel-trough`), never white. Status badges with indicators must use flex gap (`gap-1.5`) rather than child element margins (`mr-1.5`), ensuring zero phantom whitespace if an indicator is rendered invisible.
14. **Mobile text rows wrap atomically**: Any row holding label/value, author/timestamp, or badge text uses `flex flex-wrap items-baseline gap-x-* gap-y-1` with `min-w-0` on each child group. Never combine `justify-between` with `items-center` on a text row without `flex-wrap`. Every label, timestamp, and `•` separator is its own `whitespace-nowrap` span (the separator stays in the same span as the value that follows it so it cannot be stranded at a line end), and handles, emails, and display names declare `min-w-0 truncate` (or `break-words` where the full text matters). Every UI change touching text rows must be verified at 360px width, and its component test must assert the `flex-wrap` / `whitespace-nowrap` classes. See section 9 of `.agents/rules/design-spec.md` and [[concepts/fluent-responsive-design]].
15. **Zero floating tooltips & popovers (in-flow inspection)**: Never implement, propose, or introduce floating tooltips, poppers, popovers, HTML `title` attributes, or SVG `<title>` hovers. Secondary telemetry, details, and point inspections render in-flow inside a dedicated recessed `.voxel-trough` slot, contextual inspector bar, or bottom drawer. Interactive markers must be keyboard-operable (`tabindex="0"`, `role="button"`, `aria-label`, `Enter`/`Space` handlers) and drive the trough slot by click selection. See section 10 of `.agents/rules/design-spec.md` and [[concepts/in-flow-inspection]].
16. **Data-driven tables (numeric alignment & semantic row states)**: Numeric columns (prices, returns, shares, ratios) and their matching headers MUST be right-aligned (`align="right"` or `numeric`) using `tabular-nums font-mono` so stacked digits vertically align by place value. Text/identifiers are left-aligned with `truncate`/`min-w-0`. Bounded categorical data uses `Badge`. Inactive or deactivated rows carry `isInactive` (`opacity-60 text-voxel-muted bg-voxel-trough/30`), muting non-live entries and disabling hover elevation. See section 11 of `.agents/rules/design-spec.md`.
17. **Loading states, CLS prevention & zero spinners**: Prefer SSR pre-hydration with silent Suspense (`fallback={null}`) and `keepPreviousData` on transitions. Cold/uncached feeds render layout-matched Voxel `Skeleton` placeholders (never a spinner). `LoadingSpinner` and `animate-spin` are prohibited across all feeds, panels, and buttons; pending actions use `Button[isLoading]` (pulsing Voxel pixel square + `aria-busy="true"`). Mutations must not use optimistic updates. See section 7 of `.agents/rules/design-spec.md` and [[concepts/cumulative-layout-shift]].
18. **Living scene backdrops & expressive motion**: Multi-layered animated dioramas and bounded pointer/scroll parallax are permitted in major **hero** and **footer** stages (`SceneStage` / `HeroBackground`), strictly clipped (`overflow-hidden isolate`) so motion never bleeds into analytical tables or cards. Living scenes separate sky, midground scenery, and independent ambient micro-entities rather than using flat looping videos; foreground CTAs are protected either by opaque/semi-opaque Matcha scrim panels (`.scene-scrim` / `.voxel-card`, zero `backdrop-blur`) or by extended top atmospheric sky vignettes maintaining accessible contrast (`>= 4.5:1` AA / `>= 7:1` AAA) with central diorama sightlines clear of bright cloud slabs; atmosphere cycles (`dawn`, `daylight`, `dusk`, `after-hours`) default to the US Eastern market session clock via `resolveAtmospherePhase`; and full-page *"Is the site"* WebGL takeovers are prohibited on data routes. See section 12 of `.agents/rules/design-spec.md` and [[concepts/living-scene-backdrops]].
19. **Primary action front & center (above-the-fold ordering)**: Put the most important input, active prompt, and primary CTA at the very top of the page (preceded only by a compact status strip or error/active-prompt banner) so mobile users never scroll past roadmaps, template chips, or prior message history to act. Multi-step roadmaps (`BuilderStepper`), starter chips, message history, and secondary guidance links sit **below** the primary CTA across every step and sub-state. See section 4b of `.agents/rules/design-spec.md` and [[concepts/page-surface-conventions]].

## Matcha & Cedar / Cheddar palette tokens

Defined in `apps/web/src/styles/app.css` via `@theme inline`:

- `--color-voxel-canvas`: `#141c18` Deep Forest Moss page background
- `--color-voxel-surface`: `#1d2822` Stepped Moss Terrace card surface
- `--color-voxel-elevated`: `#26362e` Spruce Highlight hover surface
- `--color-voxel-trough`: `#101713` Dark Carved Slot recessed cell
- `--color-voxel-bevel-hi`: `#3f574a` Top and left 3D voxel highlight edge
- `--color-voxel-bevel-lo`: `#090d0b` Bottom and right 3D voxel shadow edge
- `--color-voxel-ink`: `#f2ead3` Warm Tatami Cream primary text that prevents halation in dark rooms
- `--color-voxel-muted`: `#9eb0a3` Lichen Sage secondary text
- `--color-accent`: `#f0a830` Cheddar Gold primary action and active state
- `--color-success`: `#68d391` Sprout Emerald buy and gain signal
- `--color-danger`: `#e56b55` Terracotta Clay sell and loss signal
- `--color-info`: `#7ab89e` Celadon Sage secondary tag color

## Primitives

Composable base components that handle styling and accessibility:

- **Button**: Tactile `.voxel-btn` primitive with 2px raised bevels, sharp `rounded-none` corners, and physical `translate(2px, 2px)` click depression. `isLoading` renders an inline pulsing Voxel pixel square (`data-slot="button-pending-dot"`, `w-2 h-2 rounded-none bg-current animate-pulse motion-reduce:animate-none`) and sets `aria-busy="true"` (no SVG spinner).
- **Card**: Raised `.voxel-card` block with `rounded-none` geometry, stepped moss surface, and hard offset shadow.
- **Badge**: Sharp `.voxel-badge` tag with optional square pixel dot indicator. The base class carries `gap-1.5` so the dot and label are separated by container gap rather than a child `mr-1.5` margin. Every badge emits a `data-color-scheme` attribute (the resolved `severity ?? colorScheme ?? 'neutral'`) for test and styling hooks. Solid-variant dot colors are resolved from a dedicated `solidDotColors` map so the indicator always contrasts against the solid fill:

  | Scheme | Solid dot color |
  | :--- | :--- |
  | `accent` | `bg-voxel-trough` |
  | `success` | `bg-zinc-950` |
  | `danger` | `bg-white` |
  | `info` | `bg-white` |
  | `warning` | `bg-zinc-950` |
  | `neutral` | `bg-white dark:bg-zinc-950` |
  | `high` | `bg-zinc-950` |
  | `medium` | `bg-white` |

  Non-solid variants keep the standard `dotColors` map. The `accent` solid fill uses `bg-accent text-voxel-trough` (never `text-white`) to satisfy the WCAG AAA contrast rule.
- **Table**: Composable suite (`Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`) inside a recessed `.voxel-trough` container. Supports `numeric` prop on `TableHead` and `TableCell` for automatic `text-right tabular-nums font-mono` alignment, and `isInactive` prop on `TableRow` to shade out halted, archived, or disabled rows (`opacity-60 text-voxel-muted bg-voxel-trough/30`). `TableCell` owns its own styling and exposes a closed set of overrides: `tone="positive" | "negative" | "muted"` (`text-success` / `text-danger` / `text-voxel-muted`, exported as `TABLE_CELL_TONES`), and `align` for `left | center | right` (weight is fixed at Tier 3 `font-normal`; there is no bold-cell variant). Those props are the only supported way to restyle a cell: `cn()` is plain clsx (no tailwind-merge), so a primitive-owned class passed through `className` is either inert (base `text-voxel-ink`, `text-xs`, `font-normal`, `px-4`, `py-3` are emitted after every semantic colour and after `font-bold`/`text-sm`, and `p-*` shorthand is emitted before `px-*`/`py-*`) or a coincidence of stylesheet order. `apps/web/src/test/table-cell-tone.test.tsx` therefore fails the build on any `TableCell` carrying a primitive-owned class (colour, size, weight, alignment, decoration, any `p-*`, `px-*`/`py-*` at or below the base, arbitrary escapes, viewport prefixes) or a dynamic `className`, and on any `tone` outside the three-value budget. A tone also wins over an `isInactive` row's mute, so a vivid cell inside a de-emphasised row is a caller error. Signed metrics map through `signTone()` / `signToneOrMuted()` (`apps/web/src/lib/sign-tone.ts`): gains positive, losses negative, a flat zero muted, and null / `"N/A"` / blank input downgraded to the neutral ink default (or to muted with the `OrMuted` variant) rather than painted as a gain. `PositionsTable` P/L columns render `+$100.00` / `-$250.00` with an em dash for a missing value; colour flows through `tone` in `PositionsTable` and `TradesTable` P/L, `PredictionsTable` direction, `EarningsAuditPage` SUE / revenue surprise / consensus upside, `EarningsArenaTab` return, the autoresearch score columns and `UncorrelatedPairs` return columns — the last keeps correlation uncoloured (ink below 0.3, muted at or above) so that success green never stands for "low correlation". Secondary columns that previously leaned on `text-zinc-300/400` now use `tone="muted"`.
- **Input**: Recessed `.voxel-trough rounded-none` wrapper (`bg-voxel-trough`, `border-voxel-bevel-hi`, `focus-within:ring-accent/40`). The inner `<input>` uses `text-sm font-bold text-voxel-ink` with `placeholder:text-voxel-muted`. Error state swaps the border to `border-danger`.
- **Label**: `block text-sm font-bold text-voxel-ink uppercase tracking-wider` (Tier 2 control typography, no `mb-*` — spacing is owned by the parent).
- **Select**: Recessed `.voxel-trough rounded-none` wrapper matching `Input` (`bg-voxel-trough`, `border-voxel-bevel-hi`). The `<select>` uses `text-sm font-bold text-voxel-ink`; `<option>` rows use `bg-voxel-surface text-voxel-ink text-sm font-bold`.
- **Skeleton**: Sharp `rounded-none` Voxel trough placeholder that preserves feed geometry during cold loads without spinners. Props: `variant` (`'text' | 'block' | 'card'`, default `'block'`) and `lines` (default `3`). Every variant renders `aria-hidden="true"` with `data-slot="skeleton"`; `card` renders a `voxel-trough rounded-none bg-voxel-trough p-4 flex flex-col gap-3` surface with `lines` child bars (`data-slot="skeleton-line"`, `h-3 rounded-none bg-voxel-elevated animate-pulse motion-reduce:animate-none`, widths cycling `w-2/3` / `w-full` / `w-4/5` / `w-5/6`); `text` renders one or more bare bars; `block` renders a `h-24 w-full` trough block. The legacy `.skeleton` shimmer CSS class in `apps/web/src/styles/app.css` has been removed — `Skeleton` is the single implementation.

> [!IMPORTANT]
> `LoadingSpinner` has been **removed** from the package. `animate-spin` loaders are prohibited across feeds, panels, and buttons. Cold loads use `Skeleton` / `LoadingBoundary`; pending actions use `Button[isLoading]`.

## Patterns

Higher-level compound components for specific UI patterns:

- **SectionHeading**: Uppercase display title paired with a solid square cheddar-gold block marker.
- **SubHeading**: Secondary heading for subsections with optional divider and right element. Carries **no** `mb-*` margin — vertical rhythm is supplied by the parent's `gap`. Its `withDivider` rule is `border-t border-voxel-bevel-hi`.
- **ConfidenceBar**: 10 discrete block segments (`data-testid="confidence-segment"`) inside a recessed `.voxel-trough` slot.
- **MetricTile**: Recessed `.voxel-trough rounded-none p-3` tile laid out as `flex flex-col justify-between gap-1` (label row + value), with `hover:bg-voxel-elevated`. No child `mb-*` margins.
- **EmptyState**: Centered `flex flex-col items-center gap-4` block. The emoji renders inside a `w-12 h-12 voxel-trough rounded-none` icon box at `text-lg` (no oversized `text-6xl`/`text-7xl` circles). The title is Tier 1 (`text-lg font-bold text-voxel-ink uppercase tracking-tight`) and the subtitle is Tier 3 (`text-xs font-normal text-voxel-muted`), both inside a `gap-1.5` stack with no `mb-*` margins.
- **ErrorCard**: `voxel-card rounded-none` surface with `border-t-danger/70 border-l-danger/70`, laid out as `flex flex-col gap-3`. Title is `text-sm font-bold text-danger`, message is `text-xs font-normal text-voxel-muted`, and the optional Retry action is a `voxel-btn rounded-none text-sm font-bold uppercase tracking-wider` button.
- **StatPill**, **LoadingBoundary** (renders a layout-preserving Voxel `Skeleton` grid — three `Skeleton variant="card" lines={3}` tiles in a `repeat(auto-fit,minmax(min(100%,18rem),1fr))` `items-stretch` grid — or a caller-supplied layout-matched `fallback` slot when `isLoading` is true; the wrapper carries `role="status"`, `aria-busy="true"`, and `aria-label={loadingText ?? 'Loading content'}` and never emits an SVG spinner): Shared layout and feedback patterns.

## Layouts & Utilities

- **PageLayout**: Full-page container with max-width constraints. With `withPadding` (default) it owns the padding — `px-6 md:px-12 py-8 md:py-12`. A page with its own rhythm passes `withPadding={false}` and writes its complete padding itself (`className="px-6 md:px-12 py-6 ..."`, as `/renko`, `PortfolioDetailPage`, `/today`, the memories header bands, `/autoresearch` and `/market-overview` do); never pass `p-*`/`py-*`/`pt-*`/`pb-*` through `className` while `withPadding` is true, because `cn` is bare clsx and the stylesheet order picks the winner (`.py-8` is emitted after `.py-6`). Page headers and sections carry **no** `mb-*` margins; the parent's `gap` supplies all inter-block spacing.
- **Page titles**: action surfaces (`/personality`, `/build`, `/chat`) open with no visible title — no eyebrow, no description — and carry exactly one `sr-only` `<h1>` matching the route `<title>`; browse surfaces keep a visible `h1`. Both rules live in `.agents/rules/design-spec.md` §4a and §3 item 4, and are enforced by `apps/web/src/test/page-surface-conventions.test.tsx`.
- **GlobalBackground**: Deep Forest Moss canvas with a subtle warm dot grid matrix.
- **SceneStage**: Spatially contained Voxel stage for multi-layered living-scene heroes (`variant="hero"`, `<section>`) and parallax footers (`variant="footer"`, `<footer>`). Renders a clipped `overflow-hidden isolate rounded-none` container with Matcha & Cedar atmospheric sky phases (`dawn` | `daylight` | `dusk` | `after-hours` via `.scene-atmosphere-*`), a dedicated `aria-hidden` `pointer-events-none` `backdrop` slot, an explicit `data-motion-role` (`background` | `reactive` | `story`), an optional `controls` slot (`data-slot="scene-controls"`, `pointer-events-auto absolute right-3 bottom-3 left-3 z-20 flex flex-wrap items-center justify-end gap-2`) for accessible foreground HUD controls rendered outside `aria-hidden` — the slot spans the stage width and wraps so a multi-button HUD cluster never overflows a narrow viewport — and an optional `scrim="panel"` wrapper (`.scene-scrim voxel-card`, zero `backdrop-blur`) to protect CTAs over animated layers.
- **HeroBackground**: Modernized Voxel hero banner with sharp `rounded-none` geometry, CSS `.voxel-dot-matrix` horizon texture, fluid container padding (zero viewport breakpoints and zero inline `style` objects), semantic Matcha `overlayMap` gradients (`from-voxel-elevated/95`, `from-success-dark/95`, `from-warning-dark/95`, `from-info-dark/95`), and optional `atmosphere` / `backdrop` slots for layered scenes.
- **resolveAtmospherePhase** (`packages/ui-design-system/src/lib/atmosphere.ts`): Pure DST-aware utility returning `'dawn' | 'daylight' | 'dusk' | 'after-hours'`. Defaults to the US Eastern market session clock (`America/New_York`: pre-market dawn `04:00–09:29`, regular daylight `09:30–15:59`, close/golden dusk `16:00–19:59`, overnight after-hours `20:00–03:59` ET) with an optional `'local'` visitor-timezone mode.
- **TodayStatusBar**: Slim sticky info bar for the Today view that filters out mechanical `sys-*` portfolios from AI buy and sell counts.

## Living scene backdrops & atmosphere

Section 12 of `.agents/rules/design-spec.md` codifies four "wow" design pillars derived from multi-layered animated scene research ([[sources/animated-scene-backgrounds-source]]):

1. **Modular layered dioramas + ambient life**: Separate atmospheric sky, midground voxel/illustrated scenery, and independent procedural micro-entities (clouds, fauna, footer characters) instead of flat looping videos.
2. **Bounded hero/footer containment & CTA legibility**: Clip animated layers inside `SceneStage` or `HeroBackground` with clear scroll ceilings, and protect foreground CTAs either with opaque/semi-opaque Matcha panels (`.scene-scrim` / `.voxel-card`, never `backdrop-blur`) or with extended top atmospheric sky vignettes maintaining accessible contrast (`>= 4.5:1` AA / `>= 7:1` AAA) with central diorama sightlines clear of bright cloud slabs.
3. **Dynamic atmosphere cycles**: Use `resolveAtmospherePhase` and `.scene-atmosphere-{dawn|daylight|dusk|after-hours}` utilities so living stages reflect the live US market session (or visitor local time) deterministically across SSR and hydration.
4. **Motion role & perf/resize guardrails**: Tag scenes with `background`, `reactive`, or bounded `story` roles; ban full-page *"Is the site"* WebGL takeovers on data routes; anchor parallax travel to viewport/stage height with resize invalidation; cap continuous canvas stages at `<= 30fps`; and honor `prefers-reduced-motion`. See [[concepts/living-scene-backdrops]].

## Gap-only flow in practice

Composite views follow a strict parent-owns-spacing pattern:

- Page shells: `<PageLayout className="flex flex-col gap-6">` (Home) or `gap-8` (Portfolios, Portfolio Detail, Lab).
- Headers: `flex flex-col gap-1` for a title + subtitle stack, replacing `mt-1` / `mt-0.5` on the subtitle.
- Sections: `flex flex-col gap-4` for a heading + content stack, replacing `mb-4` / `mb-6` on the heading row.
- Cards: `Card className="h-full flex flex-col gap-3"` with the metrics block pinned via `mt-auto` (the only permitted margin anchor).
- Inline stat pairs: `flex items-center gap-1.5` around a label + value, replacing `mr-1.5` on the label.
- Card grids: `grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-6 items-stretch` (Lab uses `minmax(min(100%,20rem),1fr)`).

Neutral states use the `neutral` color scheme rather than `accent`. The `LiveAgentConsole` header ribbon renders its market bias and action telemetry inside a recessed `voxel-trough` (`data-testid="console-telemetry-trough"`) as compact `text-xs font-mono` text — a square pixel dot plus `BIAS:`/`ACT:` labels — rather than `Badge` elements, so the header never inherits the Cheddar Gold action fill. Direction and action colors are resolved from `DIRECTION_COLOR_MAP` (`BULLISH` → `text-success`/`bg-success`, `BEARISH` → `text-danger`/`bg-danger`, `NEUTRAL` → `text-voxel-ink`/`bg-voxel-muted`) and `ACTION_COLOR_MAP` (`BUY` → `text-success`, `SELL` → `text-danger`, `HOLD` → `text-voxel-muted`).

## In-flow inspection (no floating overlays)

Section 10 of `.agents/rules/design-spec.md` bans floating tooltips, poppers, popovers, HTML `title` attributes, and SVG `<title>` hovers outright. The rationale is concrete: floating elements obscure adjacent time-series or market data, cause visual jitter and layout flicker, fail completely on touch/mobile devices, and violate WCAG keyboard accessibility standards.

Secondary telemetry, details, and point inspections therefore always render **in-flow**:

- inside a dedicated recessed `.voxel-trough` slot (the same carved-slot surface used by `MetricTile`, `ConfidenceBar`, and formula blocks),
- inside a contextual inspector bar adjacent to the visualization, or
- inside a bottom drawer for larger payloads.

Interactive elements that drive the inspector — chart markers, data points, table cells — must be keyboard-operable: `tabindex="0"`, `role="button"`, an `aria-label`, and `Enter`/`Space` handlers, with click selection toggling or updating the trough slot. Nothing floats above the canvas. See [[concepts/in-flow-inspection]].

## Page-level Voxel migration

Beyond the primitives, the feature pages render through the same Voxel tokens and equal-height grids. Representative surfaces:

- **AI Sector Predictor scoreboard** (`AIPredictionsPage.tsx`): the 4-model head-to-head grid uses `grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-6 items-stretch` with `Card` tiles (`h-full flex flex-col justify-between gap-4`), Tier 2 model names, and `text-lg font-bold font-mono tabular-nums` metric values. Every segmented control (timeframe, status, view mode, tab) is a `Button` with `variant={active ? 'solid' : 'outline'}` and `colorScheme={active ? 'accent' : 'neutral'}` inside a `gap-1` trough.
- **Leaderboard podium** (`LeaderboardPodium.tsx`): equal-height `items-stretch` grid (no `items-end`, no arbitrary `min-h-[400px]`/`min-h-[350px]`/`min-h-[320px]`), `radius="none"` cards with rank-colored top/left bevels (`border-t-success`, `border-t-accent`, `border-t-warning`).
- **Daily metrics overview** (`DailyMetricsOverview.tsx`): `items-stretch` grid of `Card padding="sm"` tiles with `text-lg font-bold font-mono tabular-nums` values; the active-variant badge is a solid `success` badge reading `ACTIVE` (no emoji).
- **Hero prediction card** (`HeroPredictionCard.tsx`): `bg-voxel-surface rounded-none border-voxel-bevel-hi` card with Tier 1 direction text and Tier 3 rationale.
- **Score calculation** (`ScoreCalculation.tsx`): `bg-voxel-surface` card, recessed `bg-voxel-trough` formula block at `text-lg font-mono font-bold`, and a fluid `minmax(min(100%,14rem),1fr)` explanation grid.
- **Today page** (`TodayPage.tsx`): the 3-column Row 2 grid uses `items-stretch` so `AgentInsights`, `NewsletterFeed`, and `AIFeelingCard` share equal height. `AIFeelingCard` uses `Card padding="md"` with `h-full flex flex-col justify-between gap-4` and a `mt-auto` footer; `NewsletterFeed` renders briefings in a `minmax(min(100%,16rem),1fr)` grid with `Badge`-based sender chips and a `voxel-trough` empty state; `AgentInsights` uses `rounded-none` toggles and Tier 3 telemetry text.
- **Daily predictions** (`DailyPredictionsPage.tsx`, `PredictionsTable.tsx`, `SegmentedPromptInspector.tsx`, `CuratedManifestCard.tsx`, `DailyPostMortemCard.tsx`, `DailyLessonsLedgerCard.tsx`, `AutoresearchMilestoneCards.tsx`): `rounded-none` segmented switchers, `voxel-btn` backtest link, `radius="none"` badges throughout, and `grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] items-stretch` milestone cards. `SegmentedPromptInspector` marks the frozen header/footer with `Badge variant="soft" colorScheme="warning"` and the mutable strategy band with `colorScheme="success"`.
- **Autoresearch arena** (`AutoresearchPage.tsx`, `ExperimentDetails.tsx`, `ExperimentList.tsx`, `PromptChanges.tsx`, `PromptBlocksCard.tsx`, `CognitiveToolboxCard.tsx`, `ResearchRationaleCard.tsx`, `VolatilityCalculation.tsx`, `BacktestTradesAudit.tsx`): `voxel-btn` track tabs, `voxel-trough` prompt panes, `rounded-none` diff/block/tool cards, and `items-stretch` grids replacing inline `gridTemplateColumns` styles.
- **Daily score audit** (`DailyScoreOverview.tsx`, `DailyProgressionGrid.tsx`, `DailyAuditLedger.tsx`): `items-stretch` metric grids, `voxel-card` ledger surface, and `rounded-none` checkpoint cards with Tier 2/3 typography. `DailyProgressionGrid` derives each checkpoint's `Button` `colorScheme` from state (`neutral` for future, `warning` for in-progress, `success`/`danger` for a selected or final active checkpoint) instead of composing raw border/background class strings.
- **Memories & Event Chain** (`MemoryCard.tsx`, `MemoriesList.tsx`, `MemoryFlow.tsx`, `EventChainPage.tsx`): `radius="none"` badges, `rounded-none` panels, `flex flex-col gap-*` stacks replacing `space-y-*`, and Tier 3 body copy. Cold-load placeholders use `Skeleton` (`MemoryCard` source citations render `Skeleton variant="card" lines={2}` inside an `aria-busy` wrapper; `EventChainPage` renders a `role="status"` `aria-label="Loading other memories in this chain..."` region containing a `Skeleton variant="card" lines={2}`).
- **Reasoning audit trail** (`ReasoningPage.tsx`, `HumanFriendlyPrompt.tsx`, `HumanFriendlyResponse.tsx`, `DataCard.tsx`, `FormattedContent.tsx`): `rounded-none` trace cards, `voxel-trough`-style recessed blocks, and `minmax(min(100%,12rem),1fr)` data grids. Background refetches render `Skeleton variant="card" lines={2}`; the empty trace viewer renders a `Skeleton variant="card" lines={3}` above its select-a-trace hint.
- **Audits** (`AuditsPage.tsx`): background refetches render `Skeleton variant="card" lines={3}` instead of a spinner.
- **Concepts tracker** (`ConceptMap.tsx`, `ConceptsPage.tsx`): `radius="none"` velocity/stage/impact badges, `rounded-none` detail panels, and a `minmax(min(100%,18rem),1fr)` legend grid.
- **Earnings audit** (`EarningsAuditPage.tsx`): `Card padding="md"` summary tiles in a `minmax(min(100%,14rem),1fr)` `items-stretch` grid with `text-lg font-bold font-mono tabular-nums` values.
- **Barometer audit** (`BarometerAuditPage.tsx`): `minmax(min(100%,10rem),1fr)` aggregate grid with `border-t-accent border-l-accent` highlight bevels.
- **Market overview** (`MarketOverviewPage.tsx`): sector performance cards in a `minmax(min(100%,18rem),1fr)` `items-stretch` grid using `text-success`/`text-danger` direction glyphs. `CorrelationHistoryExplorer` renders `Skeleton variant="block" className="h-64"` plus `Skeleton variant="text" lines={2}` inside an `aria-busy` wrapper while fetching pair history. `CorrelationHeatmap` maps correlation strength onto a dark-only ramp (`bg-rose-600` → `bg-rose-900` for positive, `bg-voxel-elevated` at zero, `bg-blue-950` → `bg-blue-600` for negative) with a single `text-voxel-ink` label color, so no cell ever renders dark text on a dark cell.
- **Backtest arena** (`BacktestAutoresearchPage.tsx`): `voxel-btn` navigation, `bg-voxel-surface rounded-none` formula card, and `voxel-trough` run-count badge.
- **Personality diagnostic** (`PersonalityQuizStep.tsx`, `PersonalityResultPanel.tsx`): the quiz card and result plaque are `.scene-scrim .voxel-card` surfaces whose children are recessed `Card variant="outlined"` / `.voxel-trough` blocks (zero nested `.voxel-card`), with a single `border-2` border style and only two typography combinations (`text-xs font-normal`, `text-sm font-bold`).

## Governance and verification protocol

1. **No arbitrary values**: Avoid square-bracket utility escapes in web application code. All styles must use defined theme spacing, typography, and color tokens.
2. **Typecheck gate**: Any update to `@llm-market-bench/ui-design-system` requires running `pnpm run typecheck` across `apps/web` to ensure no downstream breaking changes.
3. **Closed variant props**: Components must accept only design-system-defined variants and color schemes.
4. **Fluent responsive layouts**: Prohibit explicit viewport breakpoints (`sm:`, `md:`, `lg:`, `xl:`, `2xl:`) and raw pixel values for structural layouts. All composite views and multi-card panels must use intrinsic fluid design (`flex-wrap`, proportional `basis-72` and `basis-96`). See [[concepts/fluent-responsive-design]].
5. **Loading states, CLS prevention & zero spinners**: Enforce SSR/`keepPreviousData`/`fallback={null}` first, layout-matched Voxel `Skeleton` placeholders over spinners for cold feeds, zero `LoadingSpinner`/`animate-spin` loaders, and zero optimistic updates. See [[concepts/cumulative-layout-shift]] and [[concepts/tanstack-query]].
6. **No floating overlays**: Tooltips, popovers, poppers, `title` attributes, and SVG `<title>` hovers are prohibited; detail renders in-flow in a `.voxel-trough` slot with keyboard-operable triggers. See [[concepts/in-flow-inspection]].
7. **Enforced by tests**: `apps/web/src/test/design-standardization.test.tsx` asserts the typography tiers, `MetricTile` Voxel styling, solid-accent badge contrast (`text-voxel-trough`, no `text-white`), badge `gap-1.5` with no dot `mr-1.5`, `LiveAgentConsole` rendering NEUTRAL/HOLD telemetry inside a recessed `voxel-trough` (`data-testid="console-telemetry-trough"`) with zero `.voxel-badge` elements, equal-height stretched grids, intrinsic `minmax(min(100%,20rem),1fr)` tracks, and the absence of `mb-*` margins on page headers. It additionally asserts:
   - `ErrorCard` uses `rounded-none` (no `rounded-xl`), a `text-sm font-bold` title, a `text-xs font-normal` message, and a `text-sm font-bold` Retry button (no `rounded-lg`).
   - `EmptyState` uses a Tier 1 `text-lg font-bold` title (no `text-2xl`/`text-3xl`/`font-black`), a Tier 3 `text-xs font-normal` subtitle, no `text-6xl`/`text-7xl` emoji, and no `mb-*` margins.
   - `Input`/`Select` wrappers use `rounded-none` (no `rounded-xl`) and `Label` uses `text-sm font-bold` (no `font-semibold`).
   - `LeaderboardPodium` renders an `items-stretch` grid (no `items-end`) with no hardcoded `min-h-[...]` height classes.
   - `DailyMetricsOverview` renders an `items-stretch` grid with no `text-2xl` values.
   - `HeroPredictionCard` contains no `text-4xl`, `font-black`, `rounded-2xl`, or `mb-*` classes.
   - `ScoreCalculation` contains no `text-3xl`/`text-2xl`/`rounded-2xl`, and its formula block is `text-lg font-bold`.
   - `ConsoleQueueCard.test.tsx` asserts the answered-turn meta row carries `flex-wrap` and no `items-center`, the `Question` label is `whitespace-nowrap`, and the author handle is `truncate` (mobile text-row rule).
   - **Voxel Skeleton & zero-spinner loading states**: `Skeleton variant="card" lines={3}` renders `aria-hidden="true"`, `rounded-none`, `voxel-trough`, exactly 3 `[data-slot="skeleton-line"]` bars carrying `motion-reduce:animate-none`; `LoadingBoundary isLoading` renders `aria-busy="true"` with a `[data-slot="skeleton"]` and **zero** `svg` / `.animate-spin` elements; `LoadingBoundary` honours a custom layout-matched `fallback`; and `Button[isLoading]` is disabled, carries `aria-busy="true"`, renders a `[data-slot="button-pending-dot"]` with `animate-pulse`, and contains no `svg` or `.animate-spin`.
   - **Living scene stages & modernized HeroBackground**: `SceneStage` enforces clipped `overflow-hidden rounded-none` containment for `hero` (`<section>`) and `footer` (`<footer>`) variants, maps all four `.scene-atmosphere-*` classes, marks its backdrop slot `aria-hidden="true"` and `pointer-events-none`, renders its `controls` slot outside `aria-hidden` with `flex-wrap` + `justify-end` so the HUD cluster wraps instead of overflowing, and wraps protected CTAs in `.scene-scrim voxel-card` with zero `backdrop-blur`; `HeroBackground` contains zero `rounded-full` blur orbs, zero explicit viewport breakpoints (`md:`), zero inline `style` objects, and zero retired palette orb classes; and `packages/ui-design-system/src/lib/atmosphere.test.ts` covers `resolveAtmospherePhase` across EST/EDT US market sessions and local-timezone boundaries.
   - **Site-wide contrast & primitive color prop invariant**: Because `packages/ui-design-system/src/lib/cn.ts` uses `clsx` without `tailwind-merge`, callers must pass explicit `variant` and `colorScheme` props on `Button` and `Badge` rather than overriding `bg-*` or `text-*` via `className` (where Tailwind v4 CSS order causes dark `text-voxel-trough` or `bg-accent` collisions). `apps/web/src/test/contrast-audit.test.tsx` enforces zero unbacked `text-voxel-trough`/`text-accent-ink`, zero dark `-500`..`-950` text shades, zero legacy light backgrounds, zero undefined tokens, zero duplicate stripped-`dark:` color classes, and zero `className` color overrides on `Button` and `Badge`.
8. **Legacy palette migration is complete**: every `zinc-*`, `slate-*`, `gray-*`, `neutral-*`, `stone-*`, and retired accent (`electric-blue-*`, `deep-purple-*`, `cyber-yellow-*`, `neon-green-*`, `alert-red-*`) utility class has been replaced by a Voxel token across `apps/web` and `packages/ui-design-system`. The single dark theme has no light-mode counterpart, so `.glass` in `apps/web/src/styles/app.css` is defined once (`rgba(29, 40, 34, 0.85)`) with no `.dark` override, and `.card-lift:hover` carries a single dark shadow. `contrast-audit.test.tsx` fails the build if any of those legacy classes reappear.

## Related

- [[entities/web-app]]
- [[concepts/living-scene-backdrops]]
- [[sources/animated-scene-backgrounds-source]]
- [[concepts/design-variant-budget]]
- [[concepts/fluent-responsive-design]]
- [[concepts/in-flow-inspection]]
- [[concepts/cumulative-layout-shift]]
- [[concepts/type-safety]]
- [[entities/personality-quiz]]
