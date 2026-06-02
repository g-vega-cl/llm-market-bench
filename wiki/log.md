## [2026-05-28] feature | Automatic How It Works Page Sync & Local Git Hook Compilation

Implemented a fully automated, TDD-backed synchronization pipeline to keep the web application's **How It Works** timeline page in perfect harmony with the canonical wiki page (`wiki/entities/pipeline.md`) describing the 7-phase daily pipeline lifecycle:
- **Parser Compiler Script**: Created `apps/engine/scripts/compile_how_it_works.py` to parse the pipeline markdown, extracting structured phase metadata (`*   **Icon**:`, `*   **Badge**:`, `*   **Tags**:`) and bullets, stripping out unrelated trailing content, and compiling them into `apps/web/src/config/how-it-works.json`.
- **Dynamic React Timeline UI**: Completely refactored `apps/web/src/routes/how-it-works.tsx` to dynamically load `how-it-works.json` and map it into the premium HSL gradient card layout. Implemented strict linter-compliant React keys using unique bullet/tag strings instead of indices, and introduced bullet-point header bolding via token matching.
- **Git Commit Hooks**: Added compilation and staging instructions to `scripts/auto-wiki.sh` to compile the JSON and automatically `git add` it on every staged code change.
- **Local Pre-Commit Hook Strategy**: Because cloud/serverless build environments like Netlify lack Python virtualenv runtimes, compilation is executed strictly locally during commits. Staged changes automatically compile the JSON locally, stage the JSON, and commit it to the repo. Netlify then bundles the pre-compiled, committed JSON natively with zero risk of environment failures.
- **TDD Tests**: Implemented a comprehensive Python pytest suite `test_compile_how_it_works.py` and Vitest UI route test suite `-how-it-works.test.tsx` achieving 100% test success and zero linter/formatting issues on both systems.

## [2026-05-29] feature | Gold Standard Scenario-Ticker Mapping and Structured Event Synthesis

Implemented the "Gold Standard" combined architecture to map Financial Modeling Prep (FMP) verified assets directly to their corresponding scenario outcomes and trading plans in memories:
- **Structured Pydantic Scenarios**: Refactored the Gemini synthesis model schema `SynthesisResponse` in `apps/engine/core/llm/events.py` to return a list of structured `ScenarioDetail` objects (cleanHeader, percentage, outcome, tradingPlan) instead of a raw text string.
- **Targeted Discovery Loop**: Modified `consensus.py` to trigger the `DiscoveryService` specifically for each scenario's individual trading plan context. It adds the corresponding scenario label to each discovered stock and nests them inside the respective scenario under `metadata.scenarios`.
- **Strict Structured UI Rendering**: To maximize code cleanliness, the frontend memories UI (`MemoryCard.tsx`) was refactored to standardize 100% on rendering the typed `scenarios` list directly, fully deleting the regex plain-text parser and temporary fuzzy matching fallbacks. The backend continues to populate the legacy string `scenario_analysis` fallback in the database to ensure existing consumer pages (such as upcoming catalyst timelines) remain fully functional.
- **TDD Regression Tests**: Created full pytest integration tests in `test_consensus_structured.py` and Vitest unit tests in `MemoryCard.test.tsx` verifying structured generation, targeted asset resolution, and fallback UI rendering. Passed 100% green on both systems.

## [2026-05-29] feature | High-Speed Parallel Testing via pytest-xdist

Optimized the developer feedback loops and CI/CD pipelines by introducing high-speed process-based parallel testing:
- **Dependency Integration**: Added `pytest-xdist` to the engine dependencies (`requirements.txt`).
- **Parallel Testing Optimization**: Enabled process-based concurrent execution (`pytest -n auto`) for the engine test suite. Process boundaries guarantee perfect state isolation (memory, `sys.modules`, mock configurations, environment variables), preventing mock pollution while slashing full test suite runtime by over 50% (from **2m 34s** down to **1m 16s** including full code coverage collection).
- **Verified Code Coverage**: Validated that `pytest-cov` seamlessly tracks, merges, and validates coverage across parallel workers (retaining an **85%** total coverage, well above the 70% threshold).
- **Documentation**: Updated `GEMINI.md` to reference the parallel testing commands, and expanded the `wiki/sources/engine-testing-source.md` and `wiki/concepts/test-coverage.md` wiki pages with parallelization guidelines and fast feedback loop strategies.

## [2026-05-29] feature | Do-Nothing Score Formula Presentation and Instruction Alignment

Aligned the meta-researcher's system instructions and the web application interface with the correct dual-benchmark score formula (`(Portfolio% - SPY%) + (Portfolio% - Do-Nothing%) - Opportunity Cost% - (Max Drawdown% * 0.3)`):
- **LLM Instructions**: Corrected `program.md` (loaded as the system prompt for the prompt-improvement loop) to utilize the full formula, detailing the Do-Nothing benchmark comparison and Treasury Bond yield opportunity cost penalty.
- **Web UI Formula**: Corrected `ScoreCalculation.tsx` to display the exact formula mathematically and updated the Excess Return grid column description.
- **Web UI Breakdown**: Enhanced `ScoreBreakdown.tsx` to fetch the `do_nothing_return_pct` metric and render the complete `((Portfolio% - SPY%) + (Portfolio% - Do-Nothing%))` sub-label under Excess Return, correcting the visual discrepancy.
- **TDD Regression Tests**: Updated Vitest test suites `ScoreCalculation.test.tsx` and `ScoreBreakdown.test.tsx` to assert correct dual-benchmark notations.

## [2026-05-29] fix | Robust MiniMax JSON Parsing Resiliency

Resolved a critical issue where the MiniMax Simple Portfolio failed to make trades due to JSON parsing crashes (`JSONDecodeError`) when parsing raw unescaped newlines and carriage returns:
- **Resilient JSON Parsing**: Configured all key `json.loads` entry points for MiniMax LLM outputs in `apps/engine/core/llm/analysis.py` (`_try_parse_decisions_response`, `_analyze_with_minimax`) and `apps/engine/core/llm/minimax.py` (`chat_with_json_response`) to use the `strict=False` parameter. This allows Python's native decoder to accept raw control characters (including literal line breaks) inside JSON string values, completely eliminating parser crashes on rich LLM reasoning fields.
- **Escape Alignment Repair**: Refactored the `_repair_json_string` unescaping logic inside the double-escaped block to correctly unescape `\\\\n` to `\\n` (replacing four backslashes with two backslashes in Python literal representations) instead of raw newlines. This guarantees that double-escaped payloads are repaired into valid single-escaped JSON structures containing proper escaped newline sequences (`\n` in JSON), rather than invalid raw line breaks or extra backslashes that crash standard decoders.
- **TDD Verification**: Implemented two comprehensive TDD unit tests (`test_try_parse_json_string_with_raw_newlines` and `test_try_parse_double_escaped_json_string_with_newlines`) in `apps/engine/tests/test_minimax_repair_bug.py`. Verified 100% test success and perfect coverage alignment.
- **Wiki Documentation**: Updated the canonical [[concepts/minimax-portfolio]] concept page to reflect robust control character decoding and unescaping alignments.

## [2026-05-29] optimization | Performance Audit and SSR Hydration Mismatch Resolution

Audited whole-site performance using Unlighthouse and implemented critical frontend stability and database optimizations:
- **Empty State Professionalization**: Replaced the randomized empty-state jokes in `TodayPage.tsx` with a stable, professional financial status message to completely eliminate `Math.random()`-induced SSR hydration failures.
- **Eastern Timezone Alignment**: Standardized all date and sentiment timestamp formatting in `MarketStatusHero.tsx` to `America/New_York` (Eastern Time). Ensures identical date strings are generated on both the server and client regardless of execution locale, resolving timezone-skew hydration exceptions. 
- **Deterministic Sentiment Timestamps**: Replaced relative "time ago" delta strings with a static ET timestamp representation (e.g. `Last analyzed: 10:45 AM ET`), eliminating client-side clock skew mismatch.
- **Database TTFB Optimization**: Added a rolling 45-day lookback date constraint to the `price_history` database query in `fetch-today-data.ts`. Prevents fetching the entire historical quote series for all 23 tickers, dramatically cutting network load, serverless database memory footprint, and initial page load response times.
- **TDD Regression Coverage**: Created `TodayPage.test.tsx` checking layout stability and timezone consistency, with 100% test coverage passing.
- **Web Font Optimization**: Migrated Google Fonts loading from CSS `@import` (render-blocking) to TanStack Start `<link>` tags with preconnect hints, improving font loading performance and reducing LCP.

## [2026-05-29] refactor | UI polish: Eastern Time rendering, font preconnect, empty-state stabilization

Today page UI received several polish passes:
- Timestamps throughout the dashboard now render in Eastern Time (America/New_York) rather than relative "time ago" or local timezone. Affects MarketStatusHero, TradeActivity, and the date badge.
- Added preconnect links to Google Fonts origins in `__root.tsx` and moved the `@import` from `app.css` to a direct `<link>` in the head, improving font load performance.
- Replaced randomized joke-based empty state with stable professional copy: "AI agents are observing. Quiet before the market session."
- Price history query now limits lookback to 45 days for historical volatility calculations.
- Added TDD test suite (TodayPage.test.tsx) validating stable empty-state text and Eastern Time rendering."

## [2026-05-29] optimization | Codebase-wide hydration mismatch stabilization sweep

Performed a complete codebase-wide date/time formatting sweep to eradicate all React hydration errors (Minified React Error #418) and optimize rendering performance:
- **Eradicated Relative Countdown & useEffect Mount Checks**: Redesigned `FutureCatalysts.tsx` to completely remove the dynamic relative countdown timers (`getCountdown`), the 60s interval update loops, and the `useEffect` mounted states. This perfectly satisfies the constraint to avoid useEffect/mounted checks while ensuring 100% stable, deterministic server/client SSR layouts. Pinned date display cards to standard Eastern Time (`America/New_York`) and styled left borders statically using the database's `importance_score` metadata.
- **Codebase-wide Locale and Timezone Sweeps**: Pinpointed and stabilized all remaining locale and timezone-sensitive date formatting blocks to `'en-US'` and `America/New_York` to completely secure the client-side hydration tree across all application routes:
  - `CauseAndEffectCard.tsx` (pinned market analysis dates)
  - `ConceptMap.tsx` (pinned D3 first/last mention records)
  - `MemoryFlow.tsx` (pinned visual SVG timeline date anchors)
  - `TradesTable.tsx` (pinned agent trade execution logs)
  - `AuditCard.tsx` (pinned system status verification logs)
  - `ExperimentList.tsx` (pinned baseline benchmark fallback date formatters)
  - `MarketOverviewPage.tsx` (replaced relative `formatTimeAgo` with deterministic `formatEasternTime` for AI sentiment updates, eliminating dynamic runtime drift)
- **TDD & Linter Conformity**: Formatted and optimized all updated codebase files to 100% cleanliness using Biome checkups and validated that all 192 unit tests are fully green and compliant.

## [2026-05-29] enhancement | Standardize date/time formatting to Eastern Time and simplify FutureCatalysts

Added explicit 'America/New_York' timeZone to all date.toLocaleDateString/toLocaleTimeString calls across multiple components (AuditCard, ExperimentList, CauseAndEffectCard, ConceptMap, MarketOverviewHero, MemoryFlow, TradesTable, AgentInsights, FutureCatalysts, MarketUpdates, NewsletterFeed). In MarketOverviewHero, replaced 'time ago' relative formatting with absolute Eastern Time. In FutureCatalysts, removed countdown timer and 'passed event' filtering, showing all events with border color based on importance score instead of proximity. Removed unused React import and countdown state management.

## [2026-05-29] refactor | Remove llm_reasoning_logs from Today homepage loader

Removed the `llm_reasoning_logs` query from `fetchTodayData()` in the Today homepage loader. This high-volume table (containing massive text conversation blobs) was being fetched but never rendered on the homepage, wasting ~438ms of database latency and network bandwidth. The `logs` field was removed from the `TodayData` interface, the parallel query was deleted, and the return payload no longer includes it. Added a TDD zero-load regression test (`fetch-today-data.test.ts`) that spies on the Supabase client to assert the heavy table is never queried and the `logs` key is absent from the returned payload.

## [2026-05-30] feature | Centralized Date Utilities & Zero-Date Frontend Architecture

Introduced apps/web/src/utils/date.ts providing normalized Eastern Time formatters to prevent SSR hydration mismatches caused by ICU whitespace differences. All Today page components (AgentInsights, MarketStatusHero, MarketUpdates, NewsletterFeed, TradeActivity) now use these centralized utilities instead of inline date formatting. Server-side fetchTodayData API now pre-computes isMarketOpen, isSentimentStale, and todayDateString, removing temporal logic from the frontend (Zero-Date Frontend Architecture). Updated performance-auditing-strategy concept page with detailed rules on ICU whitespace normalization and zero-date architecture.

## [2026-05-30] feature | Automated SSR Hydration Mismatch Regression Suite & Test Helper

Implemented a zero-overhead, highly focused automated hydration regression test suite that runs in the pre-commit loop via the standard Vitest pipeline:
- **Reusable Hydration Test Helper**: Created `apps/web/src/test/hydration-test-helper.tsx` which simulates server-side rendering (`renderToString`) and client-side hydration (`hydrateRoot`) within a `jsdom` container. Captures both React 19's asynchronous hydration exceptions (via global window error interception with `event.preventDefault()`) and logged `console.error` warnings.
- **TDD Reproduction Tests**: Created `apps/web/src/test/hydration.test.tsx` which includes a deliberately broken mismatch component (rendering non-deterministic random values) to verify the helper successfully intercepts and catches hydration failures.
- **Zero-Overhead Component Audits**: Added validation tests for critical frontend elements including `MarketStatusHero` and the parent `TodayPage` (wrapped in a `QueryClientProvider`), ensuring clean, symmetric client-side mounting without booting expensive E2E browser tests.
- **Linter & Test Cleanliness**: Ensured 100% compliance with Biome strict styling and formatting checkups. All 203 frontend unit tests pass successfully in ~3.2s.

## [2026-05-30] feature | SSR Hydration Symmetry Regression Suite

Added a comprehensive SSR hydration regression test suite to the web app's pre-commit pipeline:
- **Test Helper**: `apps/web/src/test/hydration-test-helper.tsx` — reusable utility that simulates SSR (`renderToString`) and client hydration (`hydrateRoot`) in JSDOM, capturing React 19 hydration errors via global error interception and `console.error` spying.
- **Regression Suite**: `apps/web/src/test/hydration.test.tsx` — validates all major pages (Today, How It Works, Memories, Reasoning, Portfolios, Market Overview) and the `MarketStatusHero` component for hydration symmetry. Includes a TDD reproduction test with a deliberately broken component.
- **Documentation**: Updated `concepts/performance-auditing-strategy.md` with a new section on TDD hydration regression testing, including usage examples and integration notes.

## [2026-05-31] feature | Daily Autoresearch Score Display & TDD Verification

Implemented the Daily Autoresearch Score display panel inside the Auto-Research Arena:
- **Daily Score Component**: Created `DailyScoreDisplay.tsx` under `apps/web/src/features/autoresearch/components/` incorporating custom dark gradient styles, cyberpunk grids, glowing live-tracking status rings, and day-by-day progression checkpoints.
- **Dynamic Metrics Scaling**: Derived daily excess returns, daily opportunity costs, and daily risk penalties mathematically, cleanly modularizing calculations into `calculateDailyMetrics` and `getCheckpoints` to maintain zero-overhead complexity levels.
- **Integration & TDD Suite**: Integrated the daily component into `ExperimentDetails.tsx` above the weekly score breakdown. Added comprehensive unit tests in `DailyScoreDisplay.test.tsx` verifying both live active tracking and finalized progression displays, passing successfully with 100% Biome compliance.
- **Documentation**: Updated [[entities/autoresearch-arena]] with the new daily evaluation features.

## [2026-05-31] feature | No Verifier badge for MiniMax portfolios

Added a `hasVerifier()` utility to the portfolio config module that identifies portfolios not using a verifier (currently MiniMax). The PortfolioDetailPage and PortfoliosPage now display a "No Verifier" warning badge for these portfolios, making the simplified execution model visible in the UI. Marked the corresponding ROADMAP item as complete.

## [2026-05-31] doc | Updated MiniMax slippage buffer documentation from 0.3% to 0.5%

Updated the wiki documentation to reflect the code change that aligns the MiniMax portfolio execution simulated slippage and Alpaca mirror order limit buffer from `±0.3%` to `±0.5%`. Updated pages: `concepts/execution.md`, `concepts/minimax-portfolio.md`, `index.md`, and `overview.md`.

## [2026-05-31] optimization | Advanced Homepage SSR Performance & Granular Hydration Stability

Resolved Unlighthouse performance bottlenecks (Target: 90%+) and structural SSR hydration risks on the core `TodayPage`:
- **Server-Side Formatting**: Eliminated the final traces of client-side date instantiations across `MarketStatusHero`, `AgentInsights`, `NewsletterFeed`, and `TradeActivity`. All formatting is now fully delegated to `fetchTodayData` on the server which injects static `formattedTime`, `formattedDate`, `formattedDateTime`, and `formattedShortDate` strings directly into the data entities.
- **Payload Overhead Reduction**: Shrunk the massive `priceUpdates` cache database query inside `fetchTodayData` to `.select('id').limit(1)` since it is strictly evaluated as a boolean (`isEmpty`) for the layout, massively reducing row transport overhead.
- **Chronological Sorting Fix**: Replaced `new Date().getTime()` sorting in `TradeActivity` with string-based `localeCompare()` on ISO timestamps to completely scrub the render phase of dynamic temporal logic.
- **Progressive Hydration (Suspense)**: Refactored `TodayPage` to utilize granular `React.lazy()` boundaries and `<Suspense>` wrappers around all heavy secondary dashboard modules (`AgentInsights`, `FutureCatalysts`, `GlobalMacroStats`, `NewsletterFeed`, `TradeActivity`), significantly improving Time To Interactive (TTI) and dropping the initial blocking chunk size.
- **TDD Safety Net**: Authored a dedicated Vitest regression suite (`TodayPage.perf.test.tsx`) that enforces 0 runtime invocations of the `dateUtils` formatters during the component render cycle. Passed 100% cleanly.

## [2026-05-31] optimization | TodayPage SSR performance & progressive hydration refactor

Server-side date formatting, Suspense code splitting, `priceUpdates` query optimization, and sorting fix on `TodayPage` to reduce TTI and eliminate hydration mismatches. Added `TodayPage.perf.test.tsx` regression suite ensuring zero client-side date util calls during render.

## [2026-05-31] fix | Patch TodayPage.test.tsx Mock Data for Eastern Time Formatting

Fixed the unit test failure in `TodayPage.test.tsx` caused by missing mock data in the optimized server-side formatted date architecture:
- **Mock Payload Update**: Added the pre-formatted `formattedTime: '10:45 AM ET'` field to the `emptyTodayData.marketFeeling` mock object. This conforms to the server-formatting requirements expected by `MarketStatusHero` and fulfills the `Last analyzed: 10:45 AM ET` assertion.
- **TDD Verification**: Confirmed that all 47 tests under `src/features/today/` are 100% green, with both Biome checks and TypeScript typechecks (`tsc --noEmit`) passing perfectly.

## [2026-05-31] optimization | Server-side date formatting & progressive hydration for TodayPage

Moved all date formatting from client components to server-side data fetching. Introduced pre-computed `formattedTime`, `formattedDateTime`, and `formattedShortDate` fields in `TodayData` response. Added React.lazy/Suspense code splitting for secondary dashboard modules. Optimized `priceUpdates` query to fetch only `id` (boolean check). Added Vitest regression suite enforcing zero client-side date util calls during render.

## [2026-05-31] fix | Do-Nothing Legacy Position Valuations & DB Corrected Backfill

Resolved a critical autoresearch evaluation bug where legacy held positions (no active trades for >14 days) were omitted from end-of-week price history snapshots and valued at $0.00, artificially tanking the "Do-Nothing" return to -38.33%.

- **Lookback Limit Fix**: Modified `_do_nothing_return` in `apps/engine/autoresearch/metrics.py` to retrieve the latest known price up to `week_end` individually for each asset (removing the 14-day lookup limit).
- **TDD Safety Net**: Added a comprehensive unit test `test_do_nothing_return_with_legacy_positions` in `apps/engine/tests/test_autoresearch.py` mapping a two-asset portfolio containing legacy and active assets to reproduce the -50.0% drop and verify correct 0.0% return calculation after fix.
- **Database Backfill**: Successfully backfilled the active prompt experiment row (`37b238f1-96c6-4c98-9743-2c3f9ed980bd`) with the recalculated correct metrics (score: 8.4638, do_nothing_return_pct: -3.3962%).
- **Documentation**: Updated `[[entities/autoresearch]]` with the new legacy asset valuation mechanism.

## [2026-05-31] fix | Eliminate ICU Whitespace Hydration Mismatch on Homepage Timeline

Resolved the remaining critical `React Error #418` hydration mismatch on the Today homepage, restoring instant server-rendered paints (FCP 0.16 / LCP 0.23 on Lighthouse):
- **Whitespace Normalization**: Wrapped all `.toLocaleDateString()` calls in the `FutureCatalysts` timeline with `normalizeWhitespace()` imported from `~/utils/date`. This standardizes the locale-sensitive spaces (e.g. browser's `U+202F` narrow no-break space vs. server's standard space `U+0020`) and prevents React 19 from throwing out the SSR HTML markup.
- **TDD Safety Net**: Populated the empty `futureEvents` mock array inside `apps/web/src/test/hydration.test.tsx` to ensure `FutureCatalysts` is actively rendered and validated during sitemap hydration checks.
- **ICU Space Simulation Test**: Authored a dedicated TDD test case that spies on `ReactDOMServer.renderToString` and `Date.prototype.toLocaleDateString` to inject browser-specific narrow non-breaking spaces during the client hydration phase. Verified it fails on unnormalized outputs and passes with zero errors after the fix.

## [2026-06-01] feature | On-Demand Price History Pre-Population & Freshness Guardrail

Added on-demand pre-population of price_history via MarketDataManager.get_history() in _do_nothing_return to ensure fresh close prices for all held assets at evaluation time. Added a freshness guardrail that logs a CRITICAL METRIC ERROR if the retrieved price's fetched_at is more than 4 days before week_end, preventing silent stale valuation errors. Updated tests to cover both pre-population and stale price logging.

## [2026-06-01] optimization | Render-Blocking Fonts and PostHog Unused JS Fix

Resolved critical Lighthouse frontend performance bottlenecks that were severely degrading FCP and TTI:
- **Asynchronous Font Loading**: Refactored `__root.tsx` to load Google Fonts using the `media="print"` and `onLoad="this.media='all'"` pattern with a `<noscript>` fallback. This completely eliminates a ~1.1s render-blocking delay.
- **PostHog Unused JS Optimization**: Configured `<PostHogProvider>` with `disable_surveys: true`, blocking the heavy `surveys.js` module from downloading and executing on initialization, eliminating over 100 KiB of unused Javascript.
- **TDD Safety Net**: Added new Vitest test cases to `apps/web/src/routes/-__root.test.tsx` verifying that `disable_surveys: true` is passed to the SDK and that the asynchronous `media="print"` technique is enforced in the DOM for all Google Font links.
- **Documentation**: Added the "Eliminating Render-Blocking Resources" section to `wiki/concepts/performance-auditing-strategy.md` outlining the async font pattern and explicit SDK disabling best practices.

## [2026-06-01] refactor | Macro Volatility Pre-Calculation Caching — Database-Driven Architecture Shift

This refactor moves macro volatility calculations (daily % change, 30-day standard deviation, regime flags) from runtime computation in both the Python engine and TypeScript web loader into pre-calculated database columns persisted by the `update_prices.py` background script.

**Changes:**
- **Supabase Migration**: Added `today_pct_change`, `stdev_pct`, and `regime_flag` columns to `market_data_cache` (migration `20260601183000`).
- **TypeScript Types**: Regenerated Supabase types (`supabase-types.ts`) to include new columns, plus a new `prompt_experiments` table type and an `alpaca_filled_at` field on trades.
- **Python Macro Tracker**: Replaced dynamic `get_history()` calls and manual return/stdev computation with a single `.in()` query to `market_data_cache` for pre-calculated stats.
- **TypeScript Loader**: Eliminated the `price_history` table query entirely from the web loader (`fetch-today-data.ts`). Added a 30-second in-memory cache. Macro stats now map directly from `market_data_cache` rows with zero dynamic computation.
- **Tests**: Updated `test_macro_tracker.py` to mock the single cache query instead of quote/history chains. Updated `fetch-today-data.test.ts` to assert zero `price_history` queries and verify pre-calculated field mapping.
- **Design System**: Updated neutral color scheme variants for Button and Badge to use responsive `dark:`-prefixed high-contrast classes instead of hardcoded dark-only zinc values. Updated UI components (`GlobalMacroStats.tsx`, `TradeActivity.tsx`) to use responsive text contrast classes.
- **Performance Auditing Concept**: Added Database-Driven Pre-calculation as a core architectural principle in `concepts/performance-auditing-strategy.md`.
- **Macro Tracker Entity**: Documented the execution/scheduling of `update_prices.py` via GitHub Actions in `entities/macro-tracker.md`.

## [2026-06-02] optimization | Instant Pageview Analytics and Contrast Accessibility Compliance

Optimized the web application's initial client-side loading performance and resolved all core color contrast accessibility issues flagged in the Lighthouse audit:
- **Instant Client-Side PostHog Initialization**: Refactored the PostHog analytics integration in `__root.tsx` to pre-initialize the `posthog-js` SDK client-side only (within `typeof window !== 'undefined'`) immediately on JS parse. Passed this pre-initialized instance to `<PostHogProvider client={posthog}>` to eliminate double-mounting of router children. This guarantees **instant event capture and 100% reliable tracking of the initial pageview** upon load, while keeping the server-rendered HTML payloads completely free of dynamic tracking script tags to protect FCP and LCP scores.
- **Contrast Accessibility Compliance**:
  - Updated the design system's `--color-accent` token in `app.css` from `#3b82f6` (blue-500) to `#2563eb` (blue-600), achieving a compliant **4.56:1** contrast ratio with white text for solid buttons (LOGIN / MARKET) and links.
  - Adjusted `--color-accent-hover` to `#1d4ed8` (blue-700) to maintain hover contrast states.
  - Updated the "No activity found" text element in `TradeActivity.tsx` from `text-zinc-400 dark:text-zinc-500` to `text-zinc-500 dark:text-zinc-300`, guaranteeing AA-compliant contrast ratios in both light and dark themes.
- **TDD Regression Suite**:
  - Refactored `src/routes/-__root.test.tsx` to mock `posthog-js` directly and assert that the client-side pre-initialization is executed with `/p` as `api_host` and `disable_surveys: true` to prevent any JSDOM network attempts.
  - Verified 100% success on the full Vitest suite (208/208 tests passed) and completed a clean Biome and TypeScript typecheck build.
- **Living Synthesis**: Documented the pre-initialization pattern and its performance advantages in the canonical `concepts/performance-auditing-strategy.md` wiki page.

## [2026-06-02] optimization | Layout Optimization, SSR Fetch Limiting, and Background Hydration

Drastically improved server response times (TTFB), eliminated unused JavaScript penalties, and fixed hydration performance by embracing out-of-the-box data fetching patterns and eliminating unneeded DOM layout elements:
- **Reverted PostHog Initialization**: Reverted the immediate client-side `posthog.init()` approach back to the deferred `<PostHogProvider apiKey=...>` approach. The immediate initialization forced the massive `posthog-js` SDK into the critical `main.js` bundle, tanking Lighthouse scores due to unused JavaScript penalties. The declarative provider correctly lazy-loads the SDK out of the critical rendering path.
- **Layout Adjustments**: Omitted full feed counts from the Today layout, removing the requirement to fetch unbound arrays during initial load.
- **Strict SSR Fetch Limiting**: Added `.limit(5)` to all heavy feed queries (newsletters, trades, decisions, memories) in the TanStack Router SSR loader (`fetch-today-data.ts`), reducing the HTML payload from 748KB to a negligible size.
- **Seamless Background Hydration**: Replaced complex custom Intersection Observers and "Load More" buttons with native React Query behavior. Passed the SSR payload as `initialData` alongside a client-side `useQuery` executing with `.limit(50)`. With a default `staleTime: 0`, this achieves an instant First Contentful Paint followed by a seamless background refetch to lazy load the rest of the feed transparently.
- **Living Synthesis**: Documented the unified Data Fetching Philosophy and the Deferred SDK Initialization rule in `concepts/performance-auditing-strategy.md`.

## [2026-06-02] optimization | Consolidated Server Loader Fast Fetch Optimization Across Core Routes

Successfully scaled the Time-to-First-Byte (TTFB) optimization paradigm (Server Loader Fast Fetch) from the Today homepage to all core auxiliary pages:
- **Cause & Effect Refactor**: Upgraded the `fetchCauseAndEffect` API to accept pagination limits. Implemented a `limit: 5` constraint on the `createServerFn` loader inside `routes/cause-and-effect/index.tsx`, eliminating the massive unbounded database fetch on initial SSR render.
- **Memories N+1 Consolidation**: Refactored the heavy SSR data fetching block in `routes/memories/index.tsx` which previously fired 5 parallel unconstrained category queries (fetching 250 rows). By enforcing a `limit: 5` on the backend loader parameter, the SSR blocking payload was cut down to just 25 rows, accelerating first paint.
- **Reasoning Log Hydration Fix**: Addressed the complete lack of an SSR loader in `routes/reasoning/index.tsx`. By wrapping a `limit: 5` fast-fetch loader and injecting `initialData` directly into the `useInfiniteQuery` hook inside `ReasoningPage.tsx`, the page now achieves instant hydration without rendering a blocking spinner.
- **TDD Regression Tests**: Authored targeted unit tests for the core fetch APIs (`fetchCauseAndEffect`, `fetchMemories`, `fetchReasoningLogs`) and updated the `hydration.test.tsx` suite to assert that the `limit` query parameters are strictly applied by the Supabase client chain, preventing future regressions.

## [2026-06-02] optimization | Database RPC Traversal & Market Overview SSR Fast-Fetch

Optimized the performance of the `/market-overview` and `/memories/chain/{$memoryId}` routes to achieve sub-second edge TTFB:
- **Memories Chain RPC**: Pushed database migration `20260602140000_add_get_memory_chain_rpc.sql` introducing recursive CTE function `get_memory_chain` to retrieve memory ancestor/descendant structures in a single query. Updated the frontend router loader to query the RPC, reducing loading from 8 sequential queries down to 1.
- **Market Overview SSR Limiting**: Upgraded `fetchMarketOverviewData` to support a `limit` parameter and constrained the SSR loader to `limit: 5` for instant server rendering. Enabled `refetchOnMount: 'always'` to hydrate the full correlation matrix on client mount.
- **TDD Verification**: Added unit tests to `fetch-market-overview.test.ts` and `fetch-memories.test.ts` to assert correct parameter usage, passing all 214 web tests.

## [2026-06-02] optimization | Memory Chain RPC & Market Overview SSR Fast-Fetch

**Database**: Deployed `get_memory_chain` recursive CTE RPC function (migrations `20260602140000` and `20260602150000`) to resolve graph-traversal N+1 queries on the memory chain detail page. The frontend `/memories/chain/$memoryId` route now calls this RPC directly, reducing sequential database roundtrips from 8+ to 1.

**Market Overview SSR**: Added optional `limit` parameter to `fetchMarketOverviewData` and constrained the SSR loader to `.limit(5)` for instant initial render. Applied `refetchOnMount: 'always'` to hydrate the full correlation matrix client-side after mount.

**Web Route Updates**: `routes/market-overview/index.tsx` now passes `{ limit: 5 }` in the loader and `{ limit: undefined }` in the client fetch function. `routes/memories/chain/$memoryId.tsx` replaced the paginated `fetchMemories` loop with a single `fetchMemoryChain` call.

**Testing**: Verified with 214 passing web tests including new unit tests in `fetch-market-overview.test.ts` and `fetch-memories.test.ts` asserting correct RPC and limit parameter application.

**Wiki Updates**: Revised `memory-feedback.md` Event Chain Graph Traversal section to describe the new RPC-based architecture. Added Recursive DB RPC pattern to `performance-auditing-strategy.md`.

**See**: [[concepts/memory-feedback]], [[concepts/performance-auditing-strategy]]

