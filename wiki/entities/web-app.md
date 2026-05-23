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

### Type Consolidation (2026-05-15)

The application underwent a major type safety consolidation to remove `any` and `unknown` in favor of explicit interfaces. Key conventions:
- **JSON Fields**: Use `Record<string, any>` for database JSONB fields (metadata, prompt, response) to ensure compatibility with TanStack Start's serialization layer.
- **Server Functions**: Use `.inputValidator()` and avoid `as unknown` casting to maintain type integrity.
- **Infinite Queries**: Implement the `extends CursorPage` constraint in all list factories.
- **Timestamp Handling**: Gracefully handle `string | null` for all database timestamps.

### Scenario Analysis Parsing (2026-05-20)

To avoid UI inconsistency when parsing varying LLM scenario outputs, all splitting and parsing logic is consolidated into a single, fully-tested utility: `parseScenarios` in `src/lib/parse-scenario-percentages.ts`.
- **Structured Output**: Exposes a unified `ParsedScenario` interface separating `cleanHeader`, `percentage`, `outcome`, `tradingPlan`, and `fullText`.
- **Splitting & Sanitization**: Uses a pattern-matching regex `/(Scenario [A-Z][^:]*:)/` to segment scenario blocks (even when newlines are missing), trims the trailing `**Investable Assets` block, and extracts probability percentages. Splits outcomes from trading plans using `/Trading Plan.*?:/`.
- **Unified Adoption**: Standardized across both `MemoryCard` and `FutureCatalysts` to avoid code duplication and guarantee identical parsing behavior.

### D3 Chart Data Sanitization (2026-05-20)

To resolve spurious rendering artifacts (such as overlapping vertical lines or rendering anomalies) on the D3 performance comparison timelines, defensive input cleaning and boundary controls were implemented:
- **Pruned Memoization Boundaries**: Wrapped incoming data arrays inside `React.useMemo` blocks to filter out any performance or benchmark indices containing invalid dates, `NaN` prices, or null values. This ensures that downstream scales and layout functions never process malformed coordinates.
- **Date Deduplication**: Dynamically groups records by unique dates, preventing duplicate time-series indices which would otherwise cause vertical overlapping lines at the same x-axis coordinate.
- **Defensive Line Generators**: Equipped the D3 line generator with explicit `.defined()` callback boundaries to skip disjoint indices safely and render clean paths.

Features: today (dashboard), portfolios (summary + detail with D3 equity curves), reasoning (LLM audit trail), memories (memory chains), market-overview (correlation heatmap), concepts (PCA concept map), audits (system audit logs).

### PostHog Stealthy Reverse Proxy (2026-05-21)

To prevent client-side analytics and error tracking from being blocked by browser-level ad blockers, a custom same-origin stealthy reverse proxy is configured:
- **Client Route Proxy (`/p`)**: The client-side `PostHogProvider` (in [__root.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/routes/__root.tsx)) routes all telemetry through the relative path `/p`.
- **Local Dev Proxy**: `apps/web/vite.config.ts` proxies `/p/static` and `/p/array` to `https://us-assets.i.posthog.com`, and `/p` to `https://us.i.posthog.com` with origin rewrite.
- **Production Edge Proxy**: `apps/web/netlify.toml` maps matching `/p/*` rules on Netlify Edge CDN with `status = 200` to serve as a server-side rewrite, maintaining full first-party stealth and cookie compliance.
- **Direct Server SDK**: Server-side Node tracking (`apps/web/src/utils/posthog-server.ts`) directly targets `https://us.i.posthog.com` safely, bypassing the CDN rewrite since serverless traffic is immune to ad blockers.


## Design System

"Bloomberg Terminal Meets Wired Magazine" at `packages/ui-design-system/`. Fully adopted across all pages as of 2026-05-14.

- Colors: Electric Blue (primary), Neon Green (BUY), Alert Red (SELL), Deep Purple (AI), Cyber Yellow (catalysts)
- Typography: Space Grotesk headlines, Satoshi body, JetBrains Mono data
- Semantic gradients: electric, success, alert, catalyst, ai
- Primitives: Button (5 variants), Card (5 variants), Badge (3 variants + severity), Table (composable), Input, Select, Skeleton, ErrorBoundary, LoadingSpinner
- Patterns: SectionHeading, SubHeading (with divider support), ConfidenceBar, StatPill, MetricTile, EmptyState, LoadingBoundary, ErrorCard
- Layouts: PageLayout, HeroBackground
- Utilities: cn (clsx-based className merging)
- Motion: slide-up, scale-in, staggered delays (100-500ms), float, pulse-glow — all respect prefers-reduced-motion
- Accessibility: WCAG AA (4.5:1), aria labels, visible focus states

Cross-cutting conventions: all "Load More" buttons use Button with isLoading, all error states use ErrorCard, all loading states use LoadingBoundary, all section titles use SectionHeading. Color palette is consistently zinc-based across all pages.

## Deployment

Netlify (autoresearch.netlify.app) via `@netlify/vite-plugin-tanstack-start`. Env vars: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.

## Testing

Vitest + React Testing Library with colocated `*.test.tsx` files. Feature-colocated component testing, TDD for new features, accessibility-first query patterns.

## Related

- [[entities/engine]] — Python data engine
- [[entities/database]] — Supabase schema
- [[concepts/consensus]] — AI consensus system
- Original design docs: [ARCHITECTURE](../../raw/docs/web/README.md), [DESIGN_SYSTEM](../../raw/docs/web/DESIGN_SYSTEM.md), [TANSTACK_BEST_PRACTICES](../../raw/docs/web/TANSTACK_BEST_PRACTICES.md), [PORTFOLIOS_UI](../../raw/docs/web/portfolios-ui.md), [DEPLOYMENT](../../raw/docs/web/tanstack-start-deploy-official.md), [TESTING](../../raw/docs/web/testing.md)
