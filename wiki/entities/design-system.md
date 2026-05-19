---
tags: [design-system, component-library, ui]
category: entity
---

# Design System

The `@llm-market-bench/ui-design-system` package provides the shared UI component library for the web dashboard. It enforces the "Bloomberg Terminal meets Wired" aesthetic with consistent dark mode support.

## Primitives

Composable base components that handle styling, dark mode, and accessibility:

- **Button** — 5 variants (solid, soft, outline, ghost, glass), loading state
- **Card** — 5 variants (default, elevated, outlined, ghost, glass) with gradient, accent border, and composable sub-components (`CardHeader`, `CardBody`, `CardFooter`)
- **Badge** — 3 variants (solid, soft, outline, dot) with severity levels (critical, high, medium, low) and radius options
- **Table** — Composable suite (`Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`) with built-in dark mode, alignment (`left`/`center`/`right`), optional hover on rows, and `containerClassName` for the wrapper
- **Input**, **Label**, **ErrorMessage** — Form controls with error state and addon support
- **Select** — Standard select styled to match the design system
- **Skeleton** — 3 variants (rect, circle, text) for loading states
- **ErrorBoundary** — React error boundary with fallback UI
- **LoadingSpinner** — Spinner with size variants

## Patterns

Higher-level compound components for specific UI patterns:

- **SectionHeading** — Primary section title with gradient decorator bar and gradient text
- **SubHeading** — Secondary heading for subsections, with optional `withDivider` (horizontal rule), `uppercase` (smaller tracking-wider style), and `rightElement` (e.g., count badges)
- **ConfidenceBar** — Percentage bar with label, color scheme, and hero variant
- **StatPill** — Clickable filter pill with colored dot and count
- **MetricTile** — Compact stat display with icon, label, and value
- **EmptyState** — Standardized empty state with icon and message
- **LoadingBoundary** — Suspense wrapper with skeleton loading
- **ErrorCard** — Error display with retry action

## Layouts

- **PageLayout** — Full-page container with max-width constraints
- **HeroBackground** — Decorative background for hero sections

## Utilities

- **cn** — clsx-based className merging utility

## Design Tokens

- **Colors**: Electric Blue (primary), Neon Green (BUY), Alert Red (SELL), Deep Purple (AI), Cyber Yellow (catalysts)
- **Typography**: Space Grotesk headlines, Satoshi body, JetBrains Mono data
- **Semantic Gradients**: electric, success, alert, catalyst, ai
- **Motion**: slide-up, scale-in, staggered delays (100-500ms), float, pulse-glow — all respect `prefers-reduced-motion`

## Usage

All web app pages (Today, Portfolios, Portfolio Detail, Market Overview, Memories, Audits) import from this package. Components handle their own dark mode via Tailwind's `dark:` variants, assuming the `dark` class is on the root `<html>` element.

## Related

- [[entities/web-app]] — The dashboard that consumes this design system
- [[concepts/type-safety]] — All components are strictly typed without `any`
- [[sources/web-design-system-source]] — Original design spec
