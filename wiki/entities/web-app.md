---
tags: [web, frontend, typescript, tanstack]
category: entity
---

# Web App

A TanStack Start dashboard at `apps/web/` that visualizes real-time portfolio
data, trade audit trails, and LLM cognitive synthesis. Built with React,
TypeScript, and TanStack Query.

## Key Pages

- **Today** — Market status hero, LLM market feeling, daily trades
- **Portfolios** — Per-agent performance, positions, P&L
- **Market Overview** — Correlation heatmap, uncorrelated pairs, sector grid
- **Reasoning Trace** — Full LLM conversation history with tabbed JSON inspection

## Tech Stack

- **Framework**: TanStack Start (SSR + client routing)
- **Data Fetching**: TanStack Query with centralized query options factory, hybrid SSR + `useSuspenseQuery`, cursor-based pagination
- **Charts**: D3.js for equity curves with benchmark overlay; Recharts for heatmaps and concept maps
- **Design System**: Custom UI primitives ("Bloomberg Terminal Meets Wired Magazine"), Space Grotesk/Satoshi/JetBrains Mono typography, semantic color system with dark mode

## Architecture

Feature-sliced monorepo with three layers:

- **Feature Slices** (`src/features/<feature>/`) — Self-contained vertical slices (API, queries, components, pages, tests)
- **Route Shells** (`src/routes/`) — Thin delegation, zero business logic
- **Design System** (`packages/ui-design-system/`) — Pure UI primitives

Features: today (dashboard), portfolios (summary + detail with D3 equity curves), reasoning (LLM audit trail), memories (memory chains), market-overview (correlation heatmap), concepts (PCA concept map), audits (system audit logs).

## Design System

"Bloomberg Terminal Meets Wired Magazine" at `packages/ui-design-system/`. Fully adopted across all pages as of 2026-05-14.

- Colors: Electric Blue (primary), Neon Green (BUY), Alert Red (SELL), Deep Purple (AI), Cyber Yellow (catalysts)
- Typography: Space Grotesk headlines, Satoshi body, JetBrains Mono data
- Semantic gradients: electric, success, alert, catalyst, ai
- Primitives: Button (5 variants), Card (5 variants), Badge (3 variants + severity), Input, Select, Skeleton, ErrorBoundary, LoadingSpinner
- Patterns: SectionHeading, ConfidenceBar, StatPill, MetricTile, EmptyState, LoadingBoundary, ErrorCard
- Layouts: PageLayout, HeroBackground
- Utilities: cn (clsx-based className merging)
- Motion: slide-up, scale-in, staggered delays (100-500ms), float, pulse-glow — all respect prefers-reduced-motion
- Accessibility: WCAG AA (4.5:1), aria labels, visible focus states

Cross-cutting conventions: all "Load More" buttons use Button with isLoading, all error states use ErrorCard, all loading states use LoadingBoundary, all section titles use SectionHeading. Color palette is consistently zinc-based across all pages.

## Deployment

Netlify (benchify.netlify.app) via `@netlify/vite-plugin-tanstack-start`. Env vars: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.

## Testing

Vitest + React Testing Library with colocated `*.test.tsx` files. Feature-colocated component testing, TDD for new features, accessibility-first query patterns.

## Related

- [[entities/engine]] — Python data engine
- [[entities/database]] — Supabase schema
- [[concepts/consensus]] — AI consensus system
- Original design docs: [ARCHITECTURE](../../raw/docs/web/README.md), [DESIGN_SYSTEM](../../raw/docs/web/DESIGN_SYSTEM.md), [TANSTACK_BEST_PRACTICES](../../raw/docs/web/TANSTACK_BEST_PRACTICES.md), [PORTFOLIOS_UI](../../raw/docs/web/portfolios-ui.md), [DEPLOYMENT](../../raw/docs/web/tanstack-start-deploy-official.md), [TESTING](../../raw/docs/web/testing.md)
