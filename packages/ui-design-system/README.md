# @llm-market-bench/ui-design-system

Shared UI design system for the LLM Market Bench monorepo. Homegrown component library powered by Tailwind CSS v4.

## Philosophy

**"Bloomberg Terminal Meets Wired Magazine"** — data-dense but readable, motion with purpose, distinctive typography.

## Exports

### Primitives

| Component | Props |
|-----------|-------|
| `Button` | `variant` (solid/outline/ghost/soft/glass), `size`, `colorScheme`, `rounded` (xl/full), `gradient`, `isLoading`, `leftIcon`, `rightIcon` |
| `Card` | `variant` (default/elevated/outlined/ghost/glass), `padding`, `gradient`, `accentBorder`, `accentBorderColor` |
| `CardHeader` / `CardBody` / `CardFooter` | Composable sub-components |
| `Badge` | `variant` (solid/soft/outline/dot), `size`, `colorScheme`, `severity` (critical/high/medium/low), `radius` (full/lg/md) |
| `Input` / `Label` / `ErrorMessage` | `isError`, `leftAddon`, `rightAddon` |
| `Select` | Standard select with design system styling |
| `Skeleton` | `variant` (rect/circle/text) |
| `ErrorBoundary` | React error boundary with retry |
| `LoadingSpinner` | `size` (xs/sm/md/lg) |

### Patterns

| Component | Props |
|-----------|-------|
| `SectionHeading` | `gradient` (electric/success/catalyst/ai/alert), `children`, `className` |
| `ConfidenceBar` | `label`, `value`, `colorScheme` (accent/success/danger/info/warning), `textStyle` (default/hero), `className` |
| `StatPill` | `label`, `value`, `colorScheme` (accent/success/danger/info/warning/neutral), `isActive`, `onClick`, `className` |
| `MetricTile` | `icon`, `label`, `value`, `className` |
| `EmptyState` | Emoji, title, subtitle, action buttons |
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

## Principles

- **Simplicity over abstraction.** A small inline hex map in a component beats a shared token system that fights the build tool.
- **Use what works.** If `bg-neon-green-500` is provably in the built CSS, use it — no generators, safelists, or duplicate token systems needed.

## Usage

```tsx
import { Button, Card, Badge, SectionHeading, cn } from "@llm-market-bench/ui-design-system"
```

Components accept a `className` prop for overrides.

## Key Files

- `src/index.ts` — Public API barrel file
- `src/primitives/` — Low-level UI atoms
- `src/patterns/` — Composed UI patterns
- `src/layouts/` — Layout components
- `src/lib/cn.ts` — className utility
