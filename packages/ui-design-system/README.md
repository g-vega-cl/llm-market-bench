# @llm-market-bench/ui-design-system

Shared UI design system for the LLM Market Bench monorepo. Homegrown component library powered by Tailwind CSS v4 and the **Matcha & Cedar / Cheddar Boxel** aesthetic.

> [!IMPORTANT]
> The full design system rules, typography scale, responsive invariants, and layout guidelines are codified in [`.agents/rules/design-spec.md`](../../.agents/rules/design-spec.md) and [`wiki/entities/design-system.md`](../../wiki/entities/design-system.md).

## Philosophy

- **CSS-First Layout (Avoid JS for design)**: All layouts use declarative CSS Grid and Flexbox (`grid`, `flex`, `flex-wrap`, `items-stretch`). Zero JavaScript layout math (`ResizeObserver`, `window.innerWidth`). Zero inline `style={{ ... }}` objects for layout, typography, or colors.
- **Matcha & Cedar / Cheddar Boxel**: Tactile voxel hardware geometry (`rounded-none`, 2px directional bevels, hard 4px offset shadows, recessed `.voxel-trough` slots, and physical press `.voxel-btn`).
- **Strict 3-Combination Typography Budget**: Tier 1 (`18px Bold`), Tier 2 (`14px Bold`), and Tier 3 (`12px Normal`).
- **Parent-Owns-Spacing**: Zero manual child margins (`m-*`, `mb-*`, `mt-*`, `mr-*`, `ml-*`). Parents supply rhythm with `flex gap-*` and `grid gap-*` (`gap-2`, `gap-4`, `gap-6`).
- **WCAG AAA Contrast**: Solid Cheddar Gold tags use dark trough text (`text-boxel-trough`, never white).

## Adoption

All web app pages (Today, Portfolios, Portfolio Detail, Market Overview, Memories, Reasoning, Audits, Cause & Effect, Concepts, Daily Predictions) use the design system as their primary UI vocabulary.

## Exports

### Primitives

| Component | Props & Behavior |
|---|---|
| `Button` | Tactile `.voxel-btn` with 2px raised bevels and physical `translate(2px, 2px)` click depression. Tier 2 typography. |
| `Card` | Raised `.voxel-card` block with `rounded-none` geometry, stepped moss surface, and hard offset drop shadow. |
| `CardHeader` / `CardBody` / `CardFooter` | Composable sub-components |
| `Badge` | Sharp `.voxel-badge` tag with optional square pixel dot indicator. Built-in `gap-1.5` container spacing. |
| `Table` | Composable suite (`Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`) inside a recessed `.voxel-trough` container. |
| `Input` / `Label` / `ErrorMessage` | Recessed `.voxel-trough rounded-none` wrapper (`bg-boxel-trough`, `border-boxel-bevel-hi`). Tier 2 control typography. |
| `Select` | Recessed `.voxel-trough rounded-none` wrapper with design system styling and Tier 2 typography. |
| `ErrorBoundary` | React error boundary with retry |
| `LoadingSpinner` | `size` (xs/sm/md/lg) |

### Patterns

| Component | Purpose |
|---|---|
| `SectionHeading` | Tier 1 display title with cheddar-gold square marker. |
| `SubHeading` | Tier 2 secondary heading with optional divider and right element. Zero manual margins. |
| `ConfidenceBar` | 10 discrete block segments inside a recessed `.voxel-trough` slot. |
| `StatPill` | Clickable filter pill with colored dot, label, and count. |
| `MetricTile` | Recessed `.voxel-trough rounded-none p-3` tile (`flex flex-col justify-between gap-1`). |
| `EmptyState` | Centered zero-data state with Tier 1 title, Tier 3 subtitle, and square icon box. |
| `LoadingBoundary` | Suspense wrapper with silent fallback (zero layout shift). |
| `ErrorCard` | Tactile error display card with Tier 2 title, Tier 3 message, and retry button. |

### Layouts

| Component | Purpose |
|---|---|
| `PageLayout` | Full-page container with max-width and declarative `flex flex-col gap-6` / `gap-8` spacing. |
| `GlobalBackground` | Deep Forest Moss canvas with subtle warm dot grid matrix. |

### Utilities

| Export | Purpose |
|---|---|
| `cn` | `clsx`-based className utility |

## Usage Patterns

### Pages

- **Today**: HeroBackground, Card, Badge, ConfidenceBar, SectionHeading, MetricTile, StatPill, EmptyState
- **Portfolios**: Card, Badge, SectionHeading, MetricTile
- **Portfolio Detail**: Card, MetricTile, SectionHeading, Badge
- **Market Overview**: HeroBackground, Card, Badge, ConfidenceBar, SectionHeading, EmptyState
- **Memories**: SectionHeading, Button, ErrorCard, LoadingBoundary
- **Audits**: SectionHeading, Button, ErrorCard, LoadingBoundary, LoadingSpinner
- **Reasoning**: zinc palette alignment (SectionHeading/Button for controls)
- **Cause & Effect**: SectionHeading
- **Root Layout**: Button, Badge, cn

### Cross-cutting

- All "Load More" buttons use `Button` with `isLoading` for pending state
- All error states use `ErrorCard` with title + message
- All loading states use `LoadingBoundary` wrapper
- All section titles use `SectionHeading` with semantic gradients
- Color palette is consistently zinc-based across all pages

## Principles

- **Prefer Default System Styles**: Always favor using standard props (like `colorScheme`, `variant`, `size`, `radius`) to achieve the desired styling rather than passing custom `className` override utility classes. Centralized styles prevent visual fragmentation, guarantee correct contrast/accessibility natively, and simplify future styling adjustments.
- **Single Unified Theme**: The system is fully standardized under a single premium high-contrast dark theme ("Bloomberg Terminal meets Wired"). Primitives do not include any light/dark state conditional logic (`dark:`, media queries, or root class overrides).
- **Simplicity over abstraction**: A small inline hex map in a component beats a shared token system that fights the build tool.
- **Use what works**: If `bg-neon-green-500` is provably in the built CSS, use it — no generators, safelists, or duplicate token systems needed.

## Usage

```tsx
import { Button, Card, Badge, SectionHeading, cn } from "@llm-market-bench/ui-design-system"
```

While components accept a `className` prop for occasional layout/positional adjustments (e.g. margin, spacing), it should not be used to override base styling tokens like text colors, background colors, borders, or hover styles.

## Key Files

- `src/index.ts` — Public API barrel file
- `src/primitives/` — Low-level UI atoms
- `src/patterns/` — Composed UI patterns
- `src/layouts/` — Layout components
- `src/lib/cn.ts` — className utility
