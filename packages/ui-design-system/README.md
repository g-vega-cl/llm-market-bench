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

Color-coded elements (ConfidenceBar fill, StatPill dot) use inline `style={{ backgroundColor }}` with values from `semanticTokens` rather than Tailwind `bg-*` classes.

### Layouts

| Component | Purpose |
|-----------|---------|
| `PageLayout` | Standard page wrapper with padding and max-width |
| `HeroBackground` | Gradient hero banner with dot-pattern overlay and animated blur orbs |

### Theme

| Export | Purpose |
|--------|---------|
| `semanticTokens` | Design tokens (colors, fonts, spacing, radii) |
| `rawColors` | Raw color palettes with shade scales |

### Utilities

| Export | Purpose |
|--------|---------|
| `cn` | `clsx`-based className utility |

## Usage

```tsx
import { Button, Card, Badge, SectionHeading, cn } from "@llm-market-bench/ui-design-system"
```

Components accept a `className` prop for overrides. All design tokens are exposed as Tailwind v4 `@theme inline` variables in `apps/web/src/styles/app.css`.

## Key Files

- `src/index.ts` — Public API barrel file
- `src/theme/index.ts` — Design tokens (canonical source)
- `src/theme/globals.css` — Tailwind v4 @theme reference
- `src/primitives/` — Low-level UI atoms
- `src/patterns/` — Composed UI patterns
- `src/layouts/` — Layout components
- `src/lib/cn.ts` — className utility
