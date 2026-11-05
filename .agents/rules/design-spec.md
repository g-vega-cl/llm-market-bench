---
description: Canonical Benchify web design specification and styling rules
---

# Benchify Design Specification: CSS-First & Boxel Architecture

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
   - Express colors using design system semantic tokens (`text-success`, `text-danger`, `text-boxel-muted`, `bg-boxel-trough`).
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

---

## 4. Strict 3-Combination Typography Budget

The entire interface standardizes on at most 3 font size and boldness combinations across chrome, controls, and content:

| Tier | Tokens & CSS Classes | Usage Scope |
| :--- | :--- | :--- |
| **Tier 1 (Display & Primary Values)** | `text-lg font-bold`, `.type-heading` (18px Bold) | Page titles (`h1`), `h2`, `SectionHeading`, and primary hero metric values (`font-mono tabular-nums`). |
| **Tier 2 (Controls, Titles & Headers)** | `text-sm font-bold`, `.type-control` (14px Bold) | Buttons, card titles, `SubHeading`, `Label`, `Input`, `Select`, table headers (`TableHead`), and `Badge`. |
| **Tier 3 (Body & Telemetry)** | `text-xs font-normal`, `.type-body` (12px Normal) | Body copy, descriptions, table cells (`TableCell`), timestamps, and thought traces. |

**Prohibited Typography**:
- Prohibit `text-2xl`, `text-3xl`, `text-4xl`, `text-5xl`, `text-6xl`, `text-7xl`.
- Prohibit `text-base` (use Tier 2 `text-sm` or Tier 1 `text-lg`).
- Prohibit arbitrary escapes like `text-[9px]` or `text-[10px]`.
- Prohibit font weights `font-black`, `font-extrabold`, `font-semibold`, or `font-medium` (use strictly `font-bold` for Tiers 1–2 and `font-normal` for Tier 3).

---

## 5. Tactile Matcha & Cedar / Cheddar Boxel Geometry

All surfaces reflect the **Matcha & Cedar / Cheddar Boxel** aesthetic inspired by voxel hardware geometry and tactile physical controls.

1. **Sharp Boxel geometry**:
   - Every surface uses `rounded-none` (0px radius). Never use `rounded-md`, `rounded-xl`, `rounded-2xl`, or `rounded-full`.
   - Raised surfaces (`.voxel-card`) have 2px directional bevels (`border-boxel-bevel-hi` top/left, `border-boxel-bevel-lo` bottom/right) and hard `4px 4px 0px var(--color-boxel-bevel-lo)` offset drop shadows.
   - Recessed cells (`.voxel-trough`) invert the bevels (`border-boxel-bevel-lo` top/left, `border-boxel-bevel-hi` bottom/right) to visually carve into the terrace.
   - Physical press (`.voxel-btn`): 2px bevels, 2px shadow, active depression `translate(2px, 2px)` with shadow reset.
2. **Palette tokens**:
   - Canvas: `bg-boxel-canvas` (`#141c18` Deep Forest Moss)
   - Card Surface: `bg-boxel-surface` (`#1d2822` Stepped Moss Terrace)
   - Spruce Elevated: `bg-boxel-elevated` (`#26362e` Hover Highlight)
   - Trough: `bg-boxel-trough` (`#101713` Carved Slot)
   - Ink: `text-boxel-ink` (`#f2ead3` Warm Tatami Cream)
   - Muted: `text-boxel-muted` (`#9eb0a3` Lichen Sage)
   - Primary Accent: `bg-accent` / `text-accent` (`#f0a830` Cheddar Gold)
   - Signals: `text-success` (`#68d391`), `text-danger` (`#e56b55`), `text-info` (`#7ab89e`)
3. **WCAG AAA high contrast mandate**:
   - Solid cheddar gold (`bg-accent`) tags must always use dark text (`text-boxel-trough`), never white, maintaining $\ge 7:1$ contrast.
   - Status indicators in badges use container gap (`gap-1.5`), never child element margins (`mr-1.5`).
4. **Zero decorative emojis in UI chrome**:
   - Section headers, metric labels, and control buttons use crisp typography and square pixel indicators, never emojis.

---

## 6. Information Density & Layout Budgets

1. **Topbar 3-item budget**: The global navigation bar displays strictly 3 items: `B` (Home), `Portfolios`, and `Lab`. Zero sidebars.
2. **Page 3-block budget**: Any page renders at most 3 major vertical blocks.
3. **Row 3-stat budget**: Every table row or card slot displays at most 3 data points.
4. **Zero cards inside cards**: Raised `.voxel-card` surfaces never nest inside another `.voxel-card`. Inner metrics, code blocks, formula bars, and tables sit inside recessed `.voxel-trough` slots.
5. **Zero collapsibles or accordions**: Content that belongs on a page renders flat and visible immediately. Never hide primary content behind `useState` collapsible toggles. Secondary telemetry lives in `/lab`.

---

## 7. Cumulative Layout Shift (CLS) Prevention

1. **Zero skeletons**: Never render pulsing wireframe skeletons (`CardSkeleton`). Use silent Suspense fallbacks (`fallback={null}`) with SSR pre-hydration.
2. **Stale-while-revalidate**: All query timeframe switches must use `placeholderData: keepPreviousData` so existing views remain rendered during background fetches.
3. **In-memory cache fallback**: Server fetchers retain last valid in-memory payloads to prevent layout wipeouts on transient disconnects.
4. **Anchor stability**: Auxiliary tab panels (e.g. curated manifests) must sit below primary decision tables and hero charts, keeping visual focal points vertically invariant across tab clicks.

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
