# @llm-market-bench/ui-design-system

Shared UI design system for the LLM Market Bench monorepo. Homegrown component library powered by Tailwind CSS v4.

## Philosophy

**"Bloomberg Terminal Meets Wired Magazine"** — data-dense but readable, motion with purpose, distinctive typography.

## Adoption

All web app pages (Today, Portfolios, Portfolio Detail, Market Overview, Memories, Reasoning, Audits, Cause & Effect, Concepts) use the design system as their primary UI vocabulary. No page uses zero design system components.

## Exports

### Primitives

| Component | Props |
|-----------|-------|
| `Button` | `variant` (solid/outline/ghost/soft/glass), `size`, `colorScheme`, `rounded` (xl/full), `gradient`, `isLoading`, `leftIcon`, `rightIcon` |
| `Card` | `variant` (default/elevated/outlined/ghost/glass), `padding`, `gradient`, `accentBorder`, `accentBorderColor` |
| `CardHeader` / `CardBody` / `CardFooter` | Composable sub-components |
| `Badge` | `variant` (solid/soft/outline/dot), `size`, `colorScheme`, `severity` (critical/high/medium/low), `radius` (full/lg/md) |
| `Table` | `containerClassName`, composable sub-components (`TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`) |
| `Input` / `Label` / `ErrorMessage` | `isError`, `leftAddon`, `rightAddon` |
| `Select` | Standard select with design system styling |
| `Skeleton` | `variant` (rect/circle/text) |
| `ErrorBoundary` | React error boundary with retry |
| `LoadingSpinner` | `size` (xs/sm/md/lg) |

### Patterns

| Component | Purpose |
|-----------|---------|
| `SectionHeading` | Section title with gradient decorator bar and gradient text |
| `SubHeading` | Secondary heading for sections within a page, supports optional divider and rightElement |
| `ConfidenceBar` | Percentage bar with label, color scheme, hero variant |
| `StatPill` | Clickable filter pill with colored dot and count |
| `MetricTile` | Compact stat display with icon, label, and value |
| `EmptyState` | Emoji, title, subtitle, action buttons for zero-data states |
| `LoadingBoundary` | Suspense wrapper with loading skeleton |
| `ErrorCard` | Error display card with retry |

### Layouts

| Component | Purpose |
|-----------|---------|
| `PageLayout` | Standard page wrapper with padding and max-width |
| `HeroBackground` | Gradient hero banner with dot-pattern overlay and animated blur orbs |

### Utilities

| Export | Purpose |
|--------|---------|
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
