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
- **Badge**: Sharp `.voxel-badge` tag with optional square pixel dot indicator.
- **Table**: Composable suite (`Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`) inside a recessed `.voxel-trough` container.
- **Input**, **Label**, **Select**, **LoadingSpinner**: Standard form and status primitives.

## Patterns

Higher-level compound components for specific UI patterns:

- **SectionHeading**: Uppercase display title paired with a solid square cheddar-gold block marker.
- **SubHeading**: Secondary heading for subsections with optional divider and right element.
- **ConfidenceBar**: 10 discrete block segments (`data-testid="confidence-segment"`) inside a recessed `.voxel-trough` slot.
- **StatPill**, **MetricTile**, **EmptyState**, **LoadingBoundary**, **ErrorCard**: Shared layout and feedback patterns.

## Layouts

- **PageLayout**: Full-page container with max-width constraints.
- **GlobalBackground**: Deep Forest Moss canvas with a subtle warm dot grid matrix.
- **TodayStatusBar**: Slim sticky info bar for the Today view that filters out mechanical `sys-*` portfolios from AI buy and sell counts.

## Governance and verification protocol

1. **No arbitrary values**: Avoid square-bracket utility escapes in web application code. All styles must use defined theme spacing, typography, and color tokens.
2. **Typecheck gate**: Any update to `@llm-market-bench/ui-design-system` requires running `pnpm run typecheck` across `apps/web` to ensure no downstream breaking changes.
3. **Closed variant props**: Components must accept only design-system-defined variants and color schemes.
4. **Fluent responsive layouts**: Prohibit explicit viewport breakpoints (`sm:`, `md:`, `lg:`, `xl:`, `2xl:`) and raw pixel values for structural layouts. All composite views and multi-card panels must use intrinsic fluid design (`flex-wrap`, proportional `basis-72` and `basis-96`). See [[concepts/fluent-responsive-design]].
5. **Cumulative layout shift prevention**: Enforce silent Suspense fallbacks (`fallback={null}`) and `keepPreviousData` on timeframe queries. See [[concepts/cumulative-layout-shift]].

## Related

- [[entities/web-app]]
- [[concepts/fluent-responsive-design]]
- [[concepts/cumulative-layout-shift]]
- [[concepts/type-safety]]
- [[sources/web-design-system-source]]
