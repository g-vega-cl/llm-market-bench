---
tags: [design-system, component-library, ui]
category: entity
---

# Design System

The `@llm-market-bench/ui-design-system` package provides the shared UI component library for the web dashboard. It enforces the tactile **Matcha & Cedar / Cheddar Boxel** aesthetic inspired by voxel hardware geometry and editorial clarity.

## Design rules cheat sheet

1. **Topbar 3-item budget**: The global navigation bar in `apps/web/src/routes/__root.tsx` displays strictly 3 items: `B` (Home), `Portfolios`, and `Lab`. Zero sidebars are allowed.
2. **Page 3-block budget**: Any page may render at most 3 major blocks. `Home` renders 2 blocks, `Portfolios` renders 3 blocks, and `Lab` renders 3 category blocks.
3. **Row 3-stat budget**: Every table row or card slot displays at most 3 data points.
4. **Zero cards inside cards**: Raised `.voxel-card` surfaces never nest inside another `.voxel-card`. Inner metrics use recessed `.voxel-trough` slots.
5. **Zero collapsibles or accordions**: Content that belongs on a page renders flat and visible immediately. Secondary telemetry lives in `/lab`.
6. **Zero decorative emojis in UI chrome**: Section headers, metric labels, and buttons use crisp typography and square pixel indicators instead of emojis.
7. **Sharp boxel geometry**: Corners use `rounded-none` with 2px directional bevels (`border-boxel-bevel-hi` on top and left, `border-boxel-bevel-lo` on right and bottom) and hard `4px 4px 0px` offset shadows.
8. **Strict 3-combination typography budget**: The interface standardizes on at most 3 font size and boldness combinations across all chrome and content:
   - **Tier 1 (Display & Headings)**: `18px Bold` (`text-lg font-bold`, `.type-heading`) for page titles (`h1`), `h2`, and `SectionHeading`.
   - **Tier 2 (Controls & Cards)**: `14px Bold` (`text-sm font-bold`, `.type-control`) for buttons, card titles, table headers, badges, and prominent values.
   - **Tier 3 (Content & Telemetry)**: `12px Normal` (`text-xs font-normal`, `.type-body`) for body copy, table cells, timestamps, and thought traces.
9. **Standardized equal box sizing**: All cards inside grids and composite blocks enforce matched dimensions using fluid CSS Grid (`grid grid-cols-[repeat(auto-fit,minmax(theme(spacing.72),1fr))]`) and `items-stretch` so boxes in a section share identical height and width without awkward trailing wraps.
10. **Zero manual child margins ("Flow & Gaps Only")**: Individual elements and components must never declare exterior margins (`m-*`, `mb-*`, `mt-*`, `mr-*`, `ml-*`). Spacing between items is strictly owned by parent containers using `flex gap-*` or `grid gap-*` with a 3-step scale: `gap-2` (8px, micro inline elements), `gap-4` (16px, intra-card/controls), and `gap-6` (24px, inter-card/sections). The only permitted margin utilities are flex edge anchors (`mt-auto` to pin footer blocks to bottom of cards, `ml-auto` to push controls rightward in ribbons).
11. **Zero hardcoded widths and heights ("Intrinsic Fluid Sizing")**: Avoid rigid fixed dimensions (`w-[...]`, `h-[...]`, `min-w-72`). Multi-column card panels size horizontally via fluid CSS Grid tracks (`repeat(auto-fit, minmax(min(100%, 18rem), 1fr))`) and flex wrappers (`flex-1 basis-96 min-w-0`). Vertical dimensions flow intrinsically from content + padding + container gap.
12. **High-contrast indicator and badge semantics**: Contrast between badge text and background must meet or exceed WCAG AAA ($\ge 7:1$). Cheddar Gold (`bg-accent`) solid tags must use dark trough text (`text-boxel-trough`), never white. Status badges with indicators must use flex gap (`gap-1.5`) rather than child element margins (`mr-1.5`), ensuring zero phantom whitespace if an indicator is rendered invisible.

## Matcha & Cedar / Cheddar palette tokens

Defined in `apps/web/src/styles/app.css` via `@theme inline`:

- `--color-boxel-canvas`: `#141c18` Deep Forest Moss page background
- `--color-boxel-surface`: `#1d2822` Stepped Moss Terrace card surface
- `--color-boxel-elevated`: `#26362e` Spruce Highlight hover surface
- `--color-boxel-trough`: `#101713` Dark Carved Slot recessed cell
- `--color-boxel-bevel-hi`: `#3f574a` Top and left 3D voxel highlight edge
- `--color-boxel-bevel-lo`: `#090d0b` Bottom and right 3D voxel shadow edge
- `--color-boxel-ink`: `#f2ead3` Warm Tatami Cream primary text that prevents halation in dark rooms
- `--color-boxel-muted`: `#9eb0a3` Lichen Sage secondary text
- `--color-accent`: `#f0a830` Cheddar Gold primary action and active state
- `--color-success`: `#68d391` Sprout Emerald buy and gain signal
- `--color-danger`: `#e56b55` Terracotta Clay sell and loss signal
- `--color-info`: `#7ab89e` Celadon Sage secondary tag color

## Primitives

Composable base components that handle styling and accessibility:

- **Button**: Tactile `.voxel-btn` primitive with 2px raised bevels, sharp `rounded-none` corners, and physical `translate(2px, 2px)` click depression.
- **Card**: Raised `.voxel-card` block with `rounded-none` geometry, stepped moss surface, and hard offset shadow.
- **Badge**: Sharp `.voxel-badge` tag with optional square pixel dot indicator. The base class carries `gap-1.5` so the dot and label are separated by container gap rather than a child `mr-1.5` margin. Every badge emits a `data-color-scheme` attribute (the resolved `severity ?? colorScheme ?? 'neutral'`) for test and styling hooks. Solid-variant dot colors are resolved from a dedicated `solidDotColors` map so the indicator always contrasts against the solid fill:

  | Scheme | Solid dot color |
  | :--- | :--- |
  | `accent` | `bg-boxel-trough` |
  | `success` | `bg-zinc-950` |
  | `danger` | `bg-white` |
  | `info` | `bg-white` |
  | `warning` | `bg-zinc-950` |
  | `neutral` | `bg-white dark:bg-zinc-950` |
  | `high` | `bg-zinc-950` |
  | `medium` | `bg-white` |

  Non-solid variants keep the standard `dotColors` map. The `accent` solid fill uses `bg-accent text-boxel-trough` (never `text-white`) to satisfy the WCAG AAA contrast rule.
- **Table**: Composable suite (`Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`) inside a recessed `.voxel-trough` container.
- **Input**: Recessed `.voxel-trough rounded-none` wrapper (`bg-boxel-trough`, `border-boxel-bevel-hi`, `focus-within:ring-accent/40`). The inner `<input>` uses `text-sm font-bold text-boxel-ink` with `placeholder:text-boxel-muted`. Error state swaps the border to `border-danger`.
- **Label**: `block text-sm font-bold text-boxel-ink uppercase tracking-wider` (Tier 2 control typography, no `mb-*` — spacing is owned by the parent).
- **Select**: Recessed `.voxel-trough rounded-none` wrapper matching `Input` (`bg-boxel-trough`, `border-boxel-bevel-hi`). The `<select>` uses `text-sm font-bold text-boxel-ink`; `<option>` rows use `bg-boxel-surface text-boxel-ink text-sm font-bold`.
- **LoadingSpinner**: Standard status primitive.

## Patterns

Higher-level compound components for specific UI patterns:

- **SectionHeading**: Uppercase display title paired with a solid square cheddar-gold block marker.
- **SubHeading**: Secondary heading for subsections with optional divider and right element. Carries **no** `mb-*` margin — vertical rhythm is supplied by the parent's `gap`.
- **ConfidenceBar**: 10 discrete block segments (`data-testid="confidence-segment"`) inside a recessed `.voxel-trough` slot.
- **MetricTile**: Recessed `.voxel-trough rounded-none p-3` tile laid out as `flex flex-col justify-between gap-1` (label row + value), with `hover:bg-boxel-elevated`. No child `mb-*` margins.
- **EmptyState**: Centered `flex flex-col items-center gap-4` block. The emoji renders inside a `w-12 h-12 voxel-trough rounded-none` icon box at `text-lg` (no oversized `text-6xl`/`text-7xl` circles). The title is Tier 1 (`text-lg font-bold text-boxel-ink uppercase tracking-tight`) and the subtitle is Tier 3 (`text-xs font-normal text-boxel-muted`), both inside a `gap-1.5` stack with no `mb-*` margins.
- **ErrorCard**: `voxel-card rounded-none` surface with `border-t-danger/70 border-l-danger/70`, laid out as `flex flex-col gap-3`. Title is `text-sm font-bold text-danger`, message is `text-xs font-normal text-boxel-muted`, and the optional Retry action is a `voxel-btn rounded-none text-sm font-bold uppercase tracking-wider` button.
- **StatPill**, **LoadingBoundary**: Shared layout and feedback patterns.

## Layouts

- **PageLayout**: Full-page container with max-width constraints. It accepts a `className` prop so pages can own vertical rhythm declaratively — e.g. `<PageLayout maxWidth="xl" className="flex flex-col gap-6">` or `className="px-4 py-8 flex flex-col gap-8"`. Page headers and sections then carry **no** `mb-*` margins; the parent's `gap` supplies all inter-block spacing.
- **GlobalBackground**: Deep Forest Moss canvas with a subtle warm dot grid matrix.
- **TodayStatusBar**: Slim sticky info bar for the Today view that filters out mechanical `sys-*` portfolios from AI buy and sell counts.

## Gap-only flow in practice

Composite views follow a strict parent-owns-spacing pattern:

- Page shells: `<PageLayout className="flex flex-col gap-6">` (Home) or `gap-8` (Portfolios, Portfolio Detail, Lab).
- Headers: `flex flex-col gap-1` for a title + subtitle stack, replacing `mt-1` / `mt-0.5` on the subtitle.
- Sections: `flex flex-col gap-4` for a heading + content stack, replacing `mb-4` / `mb-6` on the heading row.
- Cards: `Card className="h-full flex flex-col gap-3"` with the metrics block pinned via `mt-auto` (the only permitted margin anchor).
- Inline stat pairs: `flex items-center gap-1.5` around a label + value, replacing `mr-1.5` on the label.
- Card grids: `grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-6 items-stretch` (Lab uses `minmax(min(100%,20rem),1fr)`).

Neutral states use the `neutral` color scheme rather than `accent` — e.g. `LiveAgentConsole` renders a `NEUTRAL` market-direction badge with `colorScheme="neutral"` so it never inherits the Cheddar Gold action fill.

## Page-level boxel migration

Beyond the primitives, the feature pages render through the same boxel tokens and equal-height grids. Representative surfaces:

- **AI Sector Predictor scoreboard** (`AIPredictionsPage.tsx`): the 4-model head-to-head grid uses `grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-6 items-stretch` with `Card` tiles (`h-full flex flex-col justify-between gap-4`), Tier 2 model names, and `text-lg font-bold font-mono tabular-nums` metric values.
- **Leaderboard podium** (`LeaderboardPodium.tsx`): equal-height `items-stretch` grid (no `items-end`, no arbitrary `min-h-[400px]`/`min-h-[350px]`/`min-h-[320px]`), `radius="none"` cards with rank-colored top/left bevels (`border-t-success`, `border-t-accent`, `border-t-warning`).
- **Daily metrics overview** (`DailyMetricsOverview.tsx`): `items-stretch` grid of `Card padding="sm"` tiles with `text-lg font-bold font-mono tabular-nums` values; the active-variant badge is a solid `success` badge reading `ACTIVE` (no emoji).
- **Hero prediction card** (`HeroPredictionCard.tsx`): `bg-boxel-surface rounded-none border-boxel-bevel-hi` card with Tier 1 direction text and Tier 3 rationale.
- **Score calculation** (`ScoreCalculation.tsx`): `bg-boxel-surface` card, recessed `bg-boxel-trough` formula block at `text-lg font-mono font-bold`, and a fluid `minmax(min(100%,14rem),1fr)` explanation grid.
- **Today page** (`TodayPage.tsx`): the 3-column Row 2 grid uses `items-stretch` so `AgentInsights`, `NewsletterFeed`, and `AIFeelingCard` share equal height. `AIFeelingCard` uses `Card padding="md"` with `h-full flex flex-col justify-between gap-4` and a `mt-auto` footer; `NewsletterFeed` renders briefings in a `minmax(min(100%,16rem),1fr)` grid with `Badge`-based sender chips and a `voxel-trough` empty state; `AgentInsights` uses `rounded-none` toggles and Tier 3 telemetry text.
- **Daily predictions** (`DailyPredictionsPage.tsx`, `PredictionsTable.tsx`, `SegmentedPromptInspector.tsx`, `CuratedManifestCard.tsx`, `DailyPostMortemCard.tsx`, `DailyLessonsLedgerCard.tsx`, `AutoresearchMilestoneCards.tsx`): `rounded-none` segmented switchers, `voxel-btn` backtest link, `radius="none"` badges throughout, and `grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] items-stretch` milestone cards.
- **Autoresearch arena** (`AutoresearchPage.tsx`, `ExperimentDetails.tsx`, `ExperimentList.tsx`, `PromptChanges.tsx`, `PromptBlocksCard.tsx`, `CognitiveToolboxCard.tsx`, `ResearchRationaleCard.tsx`, `VolatilityCalculation.tsx`, `BacktestTradesAudit.tsx`): `voxel-btn` track tabs, `voxel-trough` prompt panes, `rounded-none` diff/block/tool cards, and `items-stretch` grids replacing inline `gridTemplateColumns` styles.
- **Daily score audit** (`DailyScoreOverview.tsx`, `DailyProgressionGrid.tsx`, `DailyAuditLedger.tsx`): `items-stretch` metric grids, `voxel-card` ledger surface, and `rounded-none` checkpoint cards with Tier 2/3 typography.
- **Memories & Event Chain** (`MemoryCard.tsx`, `MemoriesList.tsx`, `MemoryFlow.tsx`, `EventChainPage.tsx`): `radius="none"` badges, `rounded-none` panels, `flex flex-col gap-*` stacks replacing `space-y-*`, and Tier 3 body copy.
- **Reasoning audit trail** (`ReasoningPage.tsx`, `HumanFriendlyPrompt.tsx`, `HumanFriendlyResponse.tsx`, `DataCard.tsx`, `FormattedContent.tsx`): `rounded-none` trace cards, `voxel-trough`-style recessed blocks, and `minmax(min(100%,12rem),1fr)` data grids.
- **Concepts tracker** (`ConceptMap.tsx`, `ConceptsPage.tsx`): `radius="none"` velocity/stage/impact badges, `rounded-none` detail panels, and a `minmax(min(100%,18rem),1fr)` legend grid.
- **Earnings audit** (`EarningsAuditPage.tsx`): `Card padding="md"` summary tiles in a `minmax(min(100%,14rem),1fr)` `items-stretch` grid with `text-lg font-bold font-mono tabular-nums` values.
- **Barometer audit** (`BarometerAuditPage.tsx`): `minmax(min(100%,10rem),1fr)` aggregate grid with `border-t-accent border-l-accent` highlight bevels.
- **Market overview** (`MarketOverviewPage.tsx`): sector performance cards in a `minmax(min(100%,18rem),1fr)` `items-stretch` grid using `text-success`/`text-danger` direction glyphs.
- **Backtest arena** (`BacktestAutoresearchPage.tsx`): `voxel-btn` navigation, `bg-boxel-surface rounded-none` formula card, and `voxel-trough` run-count badge.

## Governance and verification protocol

1. **No arbitrary values**: Avoid square-bracket utility escapes in web application code. All styles must use defined theme spacing, typography, and color tokens.
2. **Typecheck gate**: Any update to `@llm-market-bench/ui-design-system` requires running `pnpm run typecheck` across `apps/web` to ensure no downstream breaking changes.
3. **Closed variant props**: Components must accept only design-system-defined variants and color schemes.
4. **Fluent responsive layouts**: Prohibit explicit viewport breakpoints (`sm:`, `md:`, `lg:`, `xl:`, `2xl:`) and raw pixel values for structural layouts. All composite views and multi-card panels must use intrinsic fluid design (`flex-wrap`, proportional `basis-72` and `basis-96`). See [[concepts/fluent-responsive-design]].
5. **Cumulative layout shift prevention**: Enforce silent Suspense fallbacks (`fallback={null}`) and `keepPreviousData` on timeframe queries. See [[concepts/cumulative-layout-shift]].
6. **Enforced by tests**: `apps/web/src/test/design-standardization.test.tsx` asserts the typography tiers, `MetricTile` boxel styling, solid-accent badge contrast (`text-boxel-trough`, no `text-white`), badge `gap-1.5` with no dot `mr-1.5`, `LiveAgentConsole` neutral badge scheme, equal-height stretched grids, intrinsic `minmax(min(100%,20rem),1fr)` tracks, and the absence of `mb-*` margins on page headers. It additionally asserts:
   - `ErrorCard` uses `rounded-none` (no `rounded-xl`), a `text-sm font-bold` title, a `text-xs font-normal` message, and a `text-sm font-bold` Retry button (no `rounded-lg`).
   - `EmptyState` uses a Tier 1 `text-lg font-bold` title (no `text-2xl`/`text-3xl`/`font-black`), a Tier 3 `text-xs font-normal` subtitle, no `text-6xl`/`text-7xl` emoji, and no `mb-*` margins.
   - `Input`/`Select` wrappers use `rounded-none` (no `rounded-xl`) and `Label` uses `text-sm font-bold` (no `font-semibold`).
   - `LeaderboardPodium` renders an `items-stretch` grid (no `items-end`) with no hardcoded `min-h-[...]` height classes.
   - `DailyMetricsOverview` renders an `items-stretch` grid with no `text-2xl` values.
   - `HeroPredictionCard` contains no `text-4xl`, `font-black`, `rounded-2xl`, or `mb-*` classes.
   - `ScoreCalculation` contains no `text-3xl`/`text-2xl`/`rounded-2xl`, and its formula block is `text-lg font-bold`.

## Related

- [[entities/web-app]]
- [[concepts/fluent-responsive-design]]
- [[concepts/cumulative-layout-shift]]
- [[concepts/type-safety]]
- [[sources/web-design-system-source]]
