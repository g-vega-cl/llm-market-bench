---
trigger: glob
globs: "**/*.tsx, **/*.ts, **/*.css"
description: Canonical Benchify web design specification and styling rules
---

# Benchify Design Specification: CSS-First & Voxel Architecture

This is the canonical source of truth for all web UI design, layout, typography, geometry, color, and interaction patterns across `apps/web` and `@llm-market-bench/ui-design-system`.

---

## 1. CSS-First Layout: Avoid JS for Design

Modern CSS Grid and Flexbox are vastly superior to JavaScript-driven layout math. Layout, responsive wrapping, and visual state belongs strictly to the browser's CSS layout engine.

1. **CSS Grid & Flexbox over JS**:
   - Use declarative CSS utilities (`grid`, `flex`, `flex-wrap`, `items-stretch`, `justify-between`) for all 1D and 2D layouts.
   - Never use JavaScript (`window.innerWidth`, `matchMedia`, or `ResizeObserver`) to calculate column counts, element dimensions, or responsive stacking modes. (Exception: pixel-buffer rendering for HTML5 `<canvas>` or WebGL where coordinate buffers require numeric dimensions).
2. **Zero inline `style={{ ... }}` for layout, typography, or colors**:
   - Never pass layout attributes (`display`, `flex*`, `gridTemplateColumns`, `width`, `height`, `margin`, `padding`, `gap`), typography (`fontSize`, `fontWeight`, `lineHeight`), borders, or color values via React inline `style` objects.
   - Express responsive grids declaratively via Tailwind utilities (e.g. `grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))]`).
   - Express colors using design system semantic tokens (`text-success`, `text-danger`, `text-voxel-muted`, `bg-voxel-trough`).
   - The *only* permitted `style` usage is continuous dynamic data percentages (such as progress bar fills: `style={{ width: `${percent}%` }}`).
3. **CSS pseudo-classes over JS interaction listeners**:
   - Visual states must use CSS `:hover`, `:active`, `:focus-within`, `group` / `group-hover:`, and `.voxel-btn:active`.
   - Never attach `onMouseEnter` / `onMouseLeave` handlers paired with `useState` simply to swap background colors, borders, or opacity.
   - Never calculate per-element JS loops for `animationDelay` or inline styles.

---

## 2. Fluent Responsive Design: Zero Explicit Breakpoints

Components must respond to the space allocated by their parent container rather than the entire browser viewport.

1. **Zero explicit viewport breakpoints**:
   - Do not use Tailwind viewport prefixes (`sm:`, `md:`, `lg:`, `xl:`, `2xl:`) or CSS `@media (min-width: ...)` to switch column counts or toggle flex directions (`flex-col sm:flex-row`). Viewport media queries fail when components are placed inside split views, sidebars, or modal dialogs.
   - Use `flex-wrap` for elements that sit side-by-side when space permits and wrap when space is constrained.
   - Use CSS Grid with `repeat(auto-fit, minmax(min(100%, Xrem), 1fr))` for card catalogs, metric tiles, and dashboards.
2. **Equal-height stretched grids (`items-stretch`)**:
   - All sibling cards inside a grid must share identical height and width using `items-stretch` on the grid parent, paired with `h-full flex flex-col justify-between` on child `Card` components.
   - Never use `items-end` or arbitrary `min-h-[...]` variations to align card bases.
3. **Proportional master-detail layout pattern**:
   ```tsx
   <div className="flex flex-wrap gap-6 items-start min-w-0 w-full">
     {/* Sidebar: compact base */}
     <div className="w-full flex-1 basis-72 min-w-0">...</div>
     {/* Detail: expands to fill available room */}
     <div className="w-full flex-[3] basis-96 min-w-0 flex flex-col gap-4">...</div>
   </div>
   ```
4. **Zero hardcoded layout pixel dimensions**:
   - Avoid fixed widths (`w-[320px]`, `min-w-72`). Use relative `rem` units or token classes (`basis-72`, `basis-96`).
   - Vertical dimensions flow intrinsically from content + padding + container gap.

---

## 3. Parent-Owns-Spacing: Zero Manual Child Margins

1. **No exterior child margins**:
   - Child components must never declare outer margins (`m-*`, `mt-*`, `mb-*`, `ml-*`, `mr-*`) or use `space-y-*` / `space-x-*`.
   - Spacing is strictly owned by parent layout containers using `flex gap-*` and `grid gap-*`.
2. **Strict 3-step gap scale**:
   - `gap-2` (8px): Micro inline elements, tag ribbons, and compact stat pairs.
   - `gap-4` (16px): Intra-card elements, form control stacks, and toolbars.
   - `gap-6` (24px): Inter-card grids and major page section stacks (`gap-8` permitted only on top-level `PageLayout` shells).
3. **Flex edge anchors as the sole margin exception**:
   - `mt-auto`: Used inside cards to pin action buttons or metric footers to the bottom.
   - `ml-auto`: Used inside flex toolbars to push controls or status badges to the right edge.
4. **PageLayout rhythm is opted out, never overridden**: with `withPadding` (default) it emits `px-6 md:px-12 py-8 md:py-12`. A page with its own rhythm passes `withPadding={false}` and writes its complete horizontal and vertical padding itself (as `/renko` and `PortfolioDetailPage` already did). Never pass `p-*`/`px-*`/`py-*`/`pt-*`/`pb-*` via `className` while `withPadding` is true: `cn` is bare clsx, both survive, and stylesheet order wins (`.py-8` follows `.py-6`). Enforced by `page-surface-conventions.test.tsx`.

---

## 4. Strict 3-Combination Typography Budget

The entire interface standardizes on at most 3 font size and boldness combinations across chrome, controls, and content:

| Tier | Tokens & CSS Classes | Usage Scope |
| :--- | :--- | :--- |
| **Tier 1 (Display & Primary Values)** | `text-lg font-bold`, `.type-heading` (18px Bold) | Page titles on **browse surfaces** (see §4a), `h2`, `SectionHeading`, and primary hero metric values (`font-mono tabular-nums`). |
| **Tier 2 (Controls, Titles & Headers)** | `text-sm font-bold`, `.type-control` (14px Bold) | Buttons, card titles, `SubHeading`, `Label`, `Input`, `Select`, table headers (`TableHead`), and `Badge`. |
| **Tier 3 (Body & Telemetry)** | `text-xs font-normal`, `.type-body` (12px Normal) | Body copy, descriptions, table cells (`TableCell`), timestamps, and thought traces. |

**Prohibited Typography**:
- Prohibit `text-2xl`, `text-3xl`, `text-4xl`, `text-5xl`, `text-6xl`, `text-7xl`.
- Prohibit `text-base` (use Tier 2 `text-sm` or Tier 1 `text-lg`).
- Prohibit arbitrary escapes like `text-[9px]` or `text-[10px]`.
- Prohibit font weights `font-black`, `font-extrabold`, `font-semibold`, or `font-medium` (use strictly `font-bold` for Tiers 1–2 and `font-normal` for Tier 3).

### 4a. Page titles

A page's job decides its title:

- **Action surfaces** (`/personality`, `/build`, `/chat`) carry no page-level title block — no eyebrow, no title, no description above the first control. They keep the page name via exactly one `sr-only` `<h1>` matching the route `<title>`, in every render branch the route can reach (a panel that swaps components, or a route that mounts one straight from loader data, needs its own). Section headings below the fold may keep their one-line subtitles.
- **Browse surfaces** keep a visible title — an `h1` or a `SectionHeading` — plus at most one description line.

Enforced by `apps/web/src/test/page-surface-conventions.test.tsx`; edit that test and this section together.

---

## 5. Tactile Matcha & Cedar / Cheddar Voxel Geometry

All surfaces reflect the **Matcha & Cedar / Cheddar Voxel** aesthetic inspired by voxel hardware geometry and tactile physical controls.

1. **Sharp Voxel geometry**:
   - Every surface uses `rounded-none` (0px radius). Never use `rounded-md`, `rounded-xl`, `rounded-2xl`, or `rounded-full`.
   - Raised surfaces (`.voxel-card`) have 2px directional bevels (`border-voxel-bevel-hi` top/left, `border-voxel-bevel-lo` bottom/right) and hard `4px 4px 0px var(--color-voxel-bevel-lo)` offset drop shadows.
   - Recessed cells (`.voxel-trough`) invert the bevels (`border-voxel-bevel-lo` top/left, `border-voxel-bevel-hi` bottom/right) to visually carve into the terrace.
   - Physical press (`.voxel-btn`): 2px bevels, 2px shadow, active depression `translate(2px, 2px)` with shadow reset.
2. **Palette tokens**:
   - Canvas: `bg-voxel-canvas` (`#141c18` Deep Forest Moss)
   - Card Surface: `bg-voxel-surface` (`#1d2822` Stepped Moss Terrace)
   - Spruce Elevated: `bg-voxel-elevated` (`#26362e` Hover Highlight)
   - Trough: `bg-voxel-trough` (`#101713` Carved Slot)
   - Ink: `text-voxel-ink` (`#f2ead3` Warm Tatami Cream)
   - Muted: `text-voxel-muted` (`#9eb0a3` Lichen Sage)
   - Primary Accent: `bg-accent` / `text-accent` (`#f0a830` Cheddar Gold)
   - Signals: `text-success` (`#68d391`), `text-danger` (`#e56b55`), `text-info` (`#7ab89e`)
3. **WCAG AAA high contrast mandate**:
   - Solid cheddar gold (`bg-accent`) tags must always use dark text (`text-voxel-trough`), never white, maintaining $\ge 7:1$ contrast.
   - Status indicators in badges use container gap (`gap-1.5`), never child element margins (`mr-1.5`).
4. **Zero decorative emojis in UI chrome**:
   - Section headers, metric labels, and control buttons use crisp typography and square pixel indicators, never emojis.

---

## 6. Information Density & Layout Budgets

1. **Topbar 3-item budget & uniform button sizing**: The global navigation bar displays strictly 3 items: `B` (Home), `Recipes`, and `Lab`. Zero sidebars. Portfolios is not a topbar item; it is listed in the `/lab` "Audits, Benchmarks & Retired Archives" block. All buttons in the navbar must always be the same size: primary nav items (`B`, `Recipes`, `Lab`) use identical square dimensions (`h-9 w-9`, `inline-flex items-center justify-center`), and the trailing auth button (`Login` / `Logout`) matches the exact same height (`h-9`).
2. **Page 3-block budget**: Any page renders at most 3 major vertical blocks.
3. **Row 3-stat budget**: Every table row or card slot displays at most 3 data points.
4. **Zero cards inside cards**: Raised `.voxel-card` surfaces never nest inside another `.voxel-card`. Inner metrics, code blocks, formula bars, and tables sit inside recessed `.voxel-trough` slots.
5. **Zero collapsibles or accordions**: Content that belongs on a page renders flat and visible immediately. Never hide primary content behind `useState` collapsible toggles. Secondary telemetry lives in `/lab`.

---

## 7. Loading States, CLS Prevention & Zero Spinners

1. **Tiered loading hierarchy (SSR / `keepPreviousData` first)**: Prefer SSR pre-hydration with silent Suspense fallbacks (`fallback={null}`) and TanStack Query `placeholderData: keepPreviousData` on timeframe or tab transitions so hydrated views never unmount or flash during background refetches.
2. **Layout-matched Voxel skeletons over spinners**: When a cold or uncached feed, list, or detail panel must display a loading state, use composable `Skeleton` placeholders (`@llm-market-bench/ui-design-system`) or `LoadingBoundary` (with an optional layout-matched `fallback`) rather than a single centered spinner. Skeleton placeholders are preferable to a single spinner because they preserve the expected layout of the feed—users can start scanning the structure immediately, and real content swaps in with less visual jump.
   - Style skeletons strictly with Voxel tokens (`rounded-none`, `bg-voxel-trough` / `bg-voxel-elevated`, `animate-pulse motion-reduce:animate-none`, `aria-hidden="true"`) and match the target card/row structure and fluid CSS Grid tracks.
   - **Zero spinners**: `LoadingSpinner` and `animate-spin` loaders are prohibited across all feeds, panels, and buttons. Pending actions use `Button[isLoading]` (pulsing Voxel pixel square + `aria-busy="true"`).
3. **Avoid optimistic updates**: Mutations must wait for confirmed server responses with in-flow pending button/status feedback (`Button[isLoading]`) and explicit `ErrorCard` feedback on failure. Do not add speculative `onMutate` cache rewrites or optimistic rollback machinery.
4. **In-memory cache fallback**: Server fetchers retain last valid in-memory payloads to prevent layout wipeouts on transient disconnects.
5. **Anchor stability**: Auxiliary tab panels (e.g. curated manifests) must sit below primary decision tables and hero charts, keeping visual focal points vertically invariant across tab clicks.
6. **Secondary UI query settlement gating**: Secondary action buttons (such as 'Reset to Top 5' or 'Reset Crosshair') and volatile derived badges (such as daily percentage moves) must never flash or render during in-flight fetches, `keepPreviousData` background refetches, or React transition states. Use `isQuerySettled(queries, isTransitionPending)` from `apps/web/src/lib/query-client.tsx` to ensure secondary elements only appear once all relevant page queries and transitions have fully settled, while keeping primary chart and container chrome stably mounted to prevent CLS.
7. **Core Web Vitals targets**: Pair CLS discipline with `LCP <= 2.5s` and `INP <= 200ms` at p75 (`https://web.dev/articles/vitals`) by keeping Tier 1–2 initial JS lean and deferring Tier 3 secondary modules; see `[[concepts/core-web-vitals]]`.

---

## 8. Overflow Prevention & Text Wrapping

1. **Zero minimum content width**: Every flex child and grid track must declare `min-w-0` to override the browser's default `min-content` sizing on `1fr` tracks.
2. **Preformatted text wrapping**: Every `<pre>` tag rendering prompt text, code, or logs must include `whitespace-pre-wrap break-words`.
3. **Unbroken technical tokens**: Snake_case identifiers (such as `tool_names`, prompt variant hashes, or UUIDs) must declare `break-all`.
4. **Formula bars**: Mathematical expressions and equation bars must include `wordBreak: 'break-word'`, `overflowWrap: 'anywhere'`, and `overflowX: 'auto'`.


## 9. Mobile Text Rows (Labels, Timestamps, Handles)

1. **Meta rows wrap**: Any row holding label/value, author/timestamp, or badge text must use `flex flex-wrap items-baseline gap-x-* gap-y-1`. Never combine `justify-between` with `items-center` on a text row without `flex-wrap`; each child group also gets `min-w-0`.
2. **Atomic fragments**: Every label, timestamp, and separator (`•`) is its own span with `whitespace-nowrap`. A line may break between fragments, never inside one. Keep the separator in the same span as the value that follows it so it cannot be stranded at a line end.
3. **Long identifiers**: Handles, emails, and display names must declare `min-w-0 truncate` (or `break-words` where the full text matters).
4. **Mobile verification**: Every UI change touching text rows must be checked at 360px width, and its component test must assert the `flex-wrap` / `whitespace-nowrap` classes.

---

## 10. Zero Floating Tooltips & Popovers (In-Flow Voxel Trough Inspection)

1. **Absolute ban on floating tooltips & hover overlays**:
   - Never implement, propose, or introduce floating tooltips, poppers, popovers, HTML `title` attributes, or SVG `<title>` hovers.
   - *Rationale*: Floating elements obscure adjacent time-series or market data, cause visual jitter and layout flicker, fail completely on touch/mobile devices, and violate WCAG keyboard accessibility standards.
2. **Mandatory in-flow `.voxel-trough` inspection pattern**:
   - Secondary telemetry, details, and point inspections must always render in-flow inside a dedicated recessed `.voxel-trough` slot, contextual inspector bar, or bottom drawer.
   - Interactive elements (e.g. chart markers, data points) must support keyboard navigation (`tabindex="0"`, `role="button"`, `aria-label`, `Enter`/`Space` handlers) and click selection to toggle or view details in the designated trough slot.
3. **Design system precedence during planning & ideation**:
   - Agents and developers must verify UI proposals against this design specification before suggesting interaction models in `/plan` or `/grill-me`.
   - Never propose banned UI patterns (tooltips, modals, accordions) during feature design or user interviews.
   - Never treat legacy code snippets or external library conventions as design canon without cross-checking `.agents/rules/design-spec.md`.

---

## 11. Data-Driven Tables: Alignment, Semantics & Micro-States

1. **Numeric and metric right-alignment (`tabular-nums font-mono text-right`)**:
   - Every table column rendering numeric quantities (prices, returns, percentages, PnL, shares, counts, ratios, dates/timestamps) MUST be right-aligned using `align="right"` or `numeric`.
   - The matching column header (`TableHead`) MUST also be right-aligned (`align="right"` or `numeric`). Never leave a header left-aligned over right-aligned figures.
   - All numeric values must use `tabular-nums font-mono` so figures vertically align place-by-place across stacked rows.
2. **Text and identity left-alignment**:
   - Company names, tickers, model handles, descriptions, and prompt names are left-aligned (`align="left"`).
   - Long strings must declare `truncate` or `break-words` with `min-w-0` to protect table breathing room and prevent cell blowouts.
3. **Bounded categorical states as Badges**:
   - Bounded enum states (trade direction `BUY`/`SELL`, status `ACTIVE`/`HALTED`/`CLOSED`, conviction `HIGH`/`MED`/`LOW`) must render as structured `Badge` primitives, never raw unstyled strings.
4. **Semantic row states (`isInactive`)**:
   - Inactive, halted, archived, or disabled rows must carry the `isInactive` prop on `TableRow` (`opacity-60 text-voxel-muted bg-voxel-trough/30`), disabling hover highlights and visually de-emphasizing stale data relative to active trading rows.
5. **In-flow cell clarification (Zero tooltips)**:
   - When a table cell contains truncated text, shorthand tickers, or compound formulas, clarification is provided via click-to-inspect in an in-flow recessed `.voxel-trough` bar or drawer below the table—never via floating hover tooltips or HTML `title` attributes.

---

## 12. Living Scene Backdrops & Expressive Motion ("Wow" Architecture)

Expressive animated backdrops are permitted across **major page heroes and parallax footers** while preserving legibility, Voxel geometry, and performance. See `[[concepts/living-scene-backdrops]]`.

1. **Modular layered dioramas + ambient life**: Separate sky, midground scenery, and independent procedural micro-entities (clouds, fauna, footer sprites) into discrete layers—never flat looping videos or static baked clips.
2. **Containment & CTA legibility (Zero glassmorphism)**: Clip animated stages inside `SceneStage` / `HeroBackground` (`overflow-hidden isolate`) with hard scroll ceilings so motion never bleeds into data tables. Protect foreground UI either with opaque/semi-opaque Matcha surfaces (`.voxel-btn`, `.scene-scrim` / `.voxel-card`, never `backdrop-blur`) or with extended top atmospheric sky vignettes maintaining accessible contrast (`>= 4.5:1` AA / `>= 7:1` AAA) with central diorama sightlines clear of bright cloud slabs.
3. **Dynamic atmosphere cycles**: Use `.scene-atmosphere-{dawn|daylight|dusk|after-hours}` and `resolveAtmospherePhase(date, mode)` from `@llm-market-bench/ui-design-system` (defaults to US Eastern market session `America/New_York`, optional `'local'` mode; pass a shared SSR timestamp or default `'dusk'`).
4. **Motion roles & bans**: Declare `data-motion-role`: `background` (calm ambient depth), `reactive` (bounded pointer/hover), or `story` (bounded scroll hero/footer). Full-page *"Is the site"* WebGL takeovers and scroll-jacking are prohibited on data routes.
5. **Resize resilience, perf & reduced motion**: Anchor parallax travel to container/`window.innerHeight` with resize invalidation (never document `maxScroll`). Use GPU-composited transforms or offscreen-baked canvas capped at `<= 30fps`, mark backdrops `aria-hidden="true"` + `pointer-events-none`, and honor `prefers-reduced-motion`.



