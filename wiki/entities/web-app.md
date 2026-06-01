---
tags: [web, frontend, typescript, tanstack]
category: entity
---

# Web App

A TanStack Start dashboard at `apps/web/` that visualizes real-time portfolio
data, trade audit trails, and LLM cognitive synthesis. Built with React,
TypeScript, and TanStack Query.

## Key Pages

- **Today** — Market status hero, LLM market feeling, daily trades, and the premium **Global Macro & Index Volatility Statistics** panel
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

### Scenario Ticker Mapping (2026-05-29)

To solve the disjoint between memories scenario analysis and thematic stock beneficiaries, a "Gold Standard" mapping pipeline was introduced:
- **Backend Refactoring**: The Gemini synthesis schema was updated to return a list of structured `scenarios` (cleanHeader, percentage, outcome, tradingPlan) instead of a raw text string.
- **Targeted Discovery Loop**: `consensus.py` triggers FMP company screening and web searches specifically for each scenario's individual trading plan, nesting verified assets directly under the respective scenario in `metadata.scenarios`.
- **Strict Structured UI**: To maximize code cleanliness, the memories UI (`MemoryCard.tsx`) was refactored to standardise 100% on the typed `scenarios` list directly, removing all text-regex parsing and fuzzy asset-matching fallbacks in favor of explicit backend mappings. The backend continues to populate the flat string `scenario_analysis` fallback in the database to ensure legacy consumer pages (e.g. `FutureCatalysts.tsx`) remain fully operational.



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

### Historical Progression Explorer & D3 Chart Refinements (2026-05-22)

To unlock historical correlation data and trailing returns timeline exploration, a dedicated tabbed explorer page was introduced:
- **Resilient Bidirectional Queries**: The Supabase data engine queries the chronological weekly records using a bidirectional `.or` filter (`ticker_a`/`ticker_b` match check), mapping and aligning the `returns_a_90d` and `returns_b_90d` values in-memory to perfectly match the user's selected ticker display order.
- **Interactive Cursor Metrics status board**: Plotted using a custom D3 line chart displaying Pearson/Spearman coefficients and 90D returns with vibrant HSL design system tokens. Instead of using high, obstructive floating HTML tooltips, active hover states are driven through a clean **Cursor Metrics Board** positioned directly above the chart, which falls back to the latest weekly data point upon pointer exit.
- **ETF Description Clarity**: Integrates descriptive ETF names (e.g. `QQQ — Invesco QQQ Trust (NASDAQ 100)`) next to bare tickers inside searchable select dropdown elements for increased readability.

### Global Macro & Volatility Regime Statistics (2026-05-27)

To ground both users and LLM agents in the exact same market regime context, a premium "Global Macro & Index Statistics" panel is integrated directly on the main dashboard page.
- **Dynamic Category Mapping**: The static top row of SPY, QQQ, IWM, VIXY highlight cards was replaced with a new, fully dynamic `'Market'` tab displayed as the default landing view. Features `SPY`, `TLT` (for Bond Yields representation), `IWM`, and `VIXY` exclusively. Relocated `QQQ` into `'Equities'` for high readability.
- **Price History Date Filtering & Deduplication**: To resolve a calculation bug causing stale price baselines (such as the -8.44% OIL/USO bug), the server-side price update script `update_prices.py` was updated to keep the EOD price history of all 23 macro tickers fresh daily. On the frontend, `buildHistoryGroup` filters out today's ET date and deduplicates multiple intraday ticks per unique calendar date, ensuring calculations are robust against intraday snapshots.
- **Computational Parity**: Replicates the dynamic 30-day standard deviation and volatility regime shift formulas ($1.5\sigma$ for `❗ UNUSUAL`, $2.0\sigma$ for `⚠️ HIGHLY UNUSUAL`) from `apps/engine/core/macro_tracker.py` into a type-safe frontend library (`macro-tickers.ts`), executing calculations on the server fetching layer to ensure 100% computational parity with the LLM agents' `{macro_context}` prompt injection.
- **Bonds & Yields Inverse Relationships**: Features custom explanation banners under the Bonds & Treasury Yields category tab explaining the inverse price-to-yield mechanics (explaining that a drop in the `IEF` or `TLT` ETF prices indicates rising government treasury rates).
- **Premium HSL Badges & Volatility Bars**: Visualizes daily returns and standard deviations via color-coded glowing status badges (Neon Red for Regime Shift, Amber for Unusual, Neutral for Normal) and interactive visual threshold range lines.

### Automatic "How It Works" Documentation Sync (2026-05-28)

To keep the web app's documentation in perfect harmony with the project's living markdown wiki, an automated compilation pipeline is integrated into the build and git hook lifecycles.
- **Python Markdown Compiler**: Implemented `compile_how_it_works.py` under `apps/engine/scripts/` to parse `wiki/entities/pipeline.md` (which maps the 7-phase daily pipeline lifecycle), extract headers, structured metadata tokens (`*   **Icon**:`, `*   **Badge**:`, `*   **Tags**:`), and markdown bullet descriptions, compiling them into a single type-safe `how-it-works.json` file.
- **Dynamic Frontend Integration**: Refactored `apps/web/src/routes/how-it-works.tsx` to natively import `how-it-works.json` and dynamically render the premium glowing timeline interface using the designated phase-specific HSL gradient themes (blue, indigo, purple, teal, amber, emerald, pink). Bullets starting with key headers (e.g. `Layer 1`, `Atomic Settlement`, `DeepSeek Thinking Mode`) are dynamically styled and bolded using strict type-safe token lists.
- **Git Pre-Commit Compilation Strategy**: Because cloud/serverless build environments like Netlify lack Python virtualenv runtimes, compilation is executed strictly locally. The Git pre-commit hook in `scripts/auto-wiki.sh` runs `compile_how_it_works.py` locally upon staged code changes, compiles the latest `how-it-works.json`, and automatically stages the compiled JSON into the git commit. Netlify then bundles the pre-compiled, committed JSON module natively with zero risk of cloud environment conflicts.
- **Git Hook Integration**: Added a compilation hook to the pre-commit script `scripts/auto-wiki.sh`. Staged changes automatically compile the fresh JSON file and re-stage it before final commit.
- **TDD Verification**: Covered by robust Python unit tests in `test_compile_how_it_works.py` and Vitest UI tests in `-how-it-works.test.tsx` to guarantee parsing integrity and dynamic React mapping correctness.

### Homepage Performance Optimization (2026-06-01)

To raise the homepage Lighthouse Performance score from 0.82 to ≥0.90 and clear the CI gate, ten surgical fixes were shipped across caching, bundle hygiene, SSR, and accessibility. The full architecture and code references for these fixes are documented in [[concepts/performance-auditing-strategy]] and [[concepts/posthog-stealth-proxy]]. High-level summary of the integrated changes:

- **Hero Loader Split**: `fetchTodayHeroData` (`src/features/today/api/fetch-today-hero-data.ts`) is a one-query, 60 s in-memory-cached Supabase loader returning only the `market_feeling` row and ET date math. The route's `loader` runs it in parallel with `fetchTodayData` via `Promise.all`, so the MarketStatusHero block streams to the client before the full payload finishes.
- **Server-Side Price History Dedup**: `latest_per_ticker_per_day(p_tickers, p_days)` Supabase RPC returns pre-deduped one-row-per-(ticker, calendar-day) results, replacing the 5000-row raw `price_history` query in `fetchTodayData`. See [[concepts/performance-auditing-strategy]] for the migration.
- **CSS Preload + Non-Blocking Stylesheet**: `getRootHead()` exports a `rel="preload" as="style"` link paired with a `media="print"` stylesheet that flips to `all` on `onLoad`. This keeps the bundled CSS out of the render-blocking critical path.
- **Devtools Gated to DEV**: `TanStackRouterDevtools` is `lazy(() => import.meta.env.PROD ? noop : import('@tanstack/react-router-devtools'))` and the JSX is wrapped in `{import.meta.env.DEV && …}`, so the devtools package is never fetched in production.
- **Lazy PostHog with Custom Context**: `posthog-client.tsx` was rewritten to drop the static `import { usePostHog } from '@posthog/react'` (which pulls `posthog-js` into the main bundle) in favor of a custom React context. `initPostHog()` dynamically imports `posthog-js` on `requestIdleCallback` (with `setTimeout(2000)` fallback) and `useAnalytics()` returns a noop until init resolves. All 7 call sites were migrated to `useAnalytics()`. Result: `main-*.js` dropped from 554 KB to 376 KB and PostHog scripts (`exception-autocapture`, `dead-clicks-autocapture`, `web-vitals`) are no longer in the main bundle.
- **Public Auth via useCurrentUser**: Removed `beforeLoad` from `__root.tsx` (which previously called `supabase.auth.getUser()` on every page load including the homepage). The new `useCurrentUser` is a client-only `useQuery` whose server fn `getCurrentUser` runs only on navigation, and auth gates are now applied in `_authed.tsx`. Result: homepage SSR is Supabase-free.
- **Color Contrast (a11y)**: `MarketStatusHero`'s stale badge uses `text-amber-100` instead of `text-amber-300` for WCAG AA contrast on the dark glass surface.
- **Cache Headers**: `public/_headers` and `netlify.toml` add `s-maxage=60, stale-while-revalidate=300` for `/`, `max-age=31536000, immutable` for `/assets/*`, and `private, no-store` for `/_authed/*`. Validated by 3 Vitest cases in `src/test/netlify-config.test.ts`.
- **In-Memory Data Cache**: Both `fetchTodayData` and `fetchTodayHeroData` maintain a 60 s module-scoped cache keyed on the ET date string. Repeat hits within the window make zero Supabase calls.
- **TDD Coverage**: 18 new test cases across `posthog-client.test.ts` (5), `fetch-today-hero-data.test.ts` (4), `fetch-today-data.test.ts` (2 zero-load + 1 cache), `MarketStatusHero.test.tsx` (1), `__root.test.tsx` (2), and `netlify-config.test.ts` (3). All 234 Vitest tests pass.


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
- **Performance Auditing**: Integrates post-deployment Lighthouse CI audits triggered on deployment success. Strict budgets of `>= 90` are enforced on `performance`, `accessibility`, `best-practices`, and `seo` across all 12 public routes, blocking merges on violation. See [[concepts/performance-auditing-strategy]].

## Testing

Vitest + React Testing Library with colocated `*.test.tsx` files. Feature-colocated component testing, TDD for new features, accessibility-first query patterns.
- **Configuration Integrity**: Validates Netlify deployment configurations and ensures the incompatible build-time performance plugins are absent through a Vitest suite in `src/test/netlify-config.test.ts` to prevent regressions.

## Related

- [[entities/engine]] — Python data engine
- [[entities/database]] — Supabase schema
- [[entities/macro-tracker]] — 23-ticker global macro regime monitoring
- [[concepts/consensus]] — AI consensus system
- [[concepts/performance-auditing-strategy]] — Cloud-native Lighthouse budgets and the 10-fix homepage optimization
- [[concepts/posthog-stealth-proxy]] — Same-origin analytics + lazy posthog-js bundling
- [[concepts/hero-loader-split]] — Pattern: minimal hero loader runs in parallel with full payload
- Original design docs: [ARCHITECTURE](../../raw/docs/web/README.md), [DESIGN_SYSTEM](../../raw/docs/web/DESIGN_SYSTEM.md), [TANSTACK_BEST_PRACTICES](../../raw/docs/web/TANSTACK_BEST_PRACTICES.md), [PORTFOLIOS_UI](../../raw/docs/web/portfolios-ui.md), [DEPLOYMENT](../../raw/docs/web/tanstack-start-deploy-official.md), [TESTING](../../raw/docs/web/testing.md)
