## [2026-06-01] doc | Client/Server Time Best Practices Documentation

Expanded the canonical performance auditing strategy concept page to comprehensively detail the 5 core client/server time best practices for eliminating SSR hydration mismatches (React Error #418) in server-side rendered environments.

## [2026-06-01] feature | Granular Stock Valuation Ledger and Auditable Starting Prices

Expanded the auto-research do-nothing return calculation engine and frontend dashboard to provide comprehensive, factual transparency for initial vs. ending asset valuations:
- **Starting Price Queries**: Enhanced `_do_nothing_return()` in `apps/engine/autoresearch/metrics.py` to fetch historical stock prices at the exact beginning of the week (`week_start`) in addition to ending prices (`week_end`).
- **Initial Valuation Ledger**: Extended the compiled `portfolio_details` position schema to calculate and record starting prices (`start_price`) and starting position values (`start_value` = `qty * start_price`) along with ending prices (`end_price`) and values (`end_value` / `value`).
- **TDD Regression Tests**: Added `test_do_nothing_includes_initial_and_end_prices` in `apps/engine/tests/test_autoresearch.py` verifying that starting vs. ending prices are queried correctly and details are populated with full mathematical precision. Verified 100% engine test success (732/732 tests passing) and 84% code coverage.
- **Premium Frontend Asset Auditor**: Expanded the React/TypeScript types and tabular asset auditor in `apps/web/src/features/autoresearch/components/ScoreBreakdown.tsx` with two new columns: "Start Price" and "Start Value". Added backward-compatible fallback styling (`—`) to cleanly render older experiment records that lack starting prices. Passed all 214 Vitest unit tests and `pnpm biome check` cleanly.

## [2026-05-27] feature | Dynamic Market Tab, Price History Synchronization & Date Deduplication

Refactored the Global Macro Stats panel to remove static benchmark hero cards and introduce a dynamic "Market" default tab containing SPY, TLT, IWM, and VIXY. Moved QQQ to the "Equities" tab. Fixed stale price history calculations by adding 8 missing benchmark tickers to update_prices.py and implementing ET-date filtering with per-calendar-day deduplication in the frontend fetch-today-data layer. Added comprehensive Vitest unit tests for buildHistoryGroup and updated GlobalMacroStats component tests.

## [2026-05-27] feature | Dynamic Market Tab, Price History Synchronization & Date Deduplication

Refactored the Global Macro Stats panel to remove static benchmark hero cards and introduce a dynamic "Market" default tab containing SPY, TLT, IWM, and VIXY. Moved QQQ to the "Equities" tab. Fixed stale price history calculations by adding 8 missing benchmark tickers to update_prices.py and implementing ET-date filtering with per-calendar-day deduplication in the frontend fetch-today-data layer. Added comprehensive Vitest unit tests for buildHistoryGroup and updated GlobalMacroStats component tests.

## [2026-05-28] update | Cleanup module parameterization and test coverage

Updated cleanup.py with comprehensive docstring explaining the 6-stage maintenance pipeline and Python-calculated threshold parameterization. Added test for exception handling. Updated wiki page to reflect new parameterization.

## [2026-05-28] fix | MiniMax 2.7 JSON Repair and Schema Enforcement

Fixed a major trade execution blocking issue where the MiniMax 2.7 Simple Portfolio made 0 trades due to JSON parsing and schema validation failures:
- **Quote and Newline Unescaping Fix**: Corrected the custom JSON repair helper `_repair_json_string` in `core/llm/analysis.py` to perform quote and newline unescaping ONLY on double-escaped JSON responses (those wrapped in outer double quotes). This prevents the helper from unconditionally unescaping valid internal escaped quotes and newlines in standard JSON responses, which previously invalidated the JSON structure.
- **Detailed Prompt Schema Enforcement**: Expanded the user prompt instruction in `_analyze_with_minimax` to include a precise, detailed JSON schema for both `decisions` and `macro_events`. This ensures the MiniMax API returns JSON matching the exact expected Pydantic fields (e.g. `event_name`, `impact`, and `reasoning` for `macro_events`), preventing Pydantic `ValidationError` drop-offs.
- **TDD Tests**: Added comprehensive unit tests (`test_repair_json_string_with_escaped_quotes_and_newlines` and `test_try_parse_minimax_raw_schema`) in `apps/engine/tests/test_analysis_logic.py`.
- **Documentation**: Updated the [[concepts/minimax-portfolio]] concept page to document the JSON extraction, schema enforcement, and parsing repair alignment.

## [2026-05-28] chore | Scratch Script Cleanup & Event Chain Enhancement

Removed 10 stale scratch/utility scripts from `apps/engine/scratch/` that were used for ad-hoc debugging, DB inspection, and metrics backfill during development. These were one-off scripts and are no longer needed. Also added TDD-backed `buildChain` utility and tests to the memories feature for full event chain tree traversal (already added to wiki in a previous commit), and marked two completed ROADMAP items.

## [2026-05-28] fix | MiniMax 2.7 Parsing Scoping Bug and Improved Observability

Resolved a critical scoping bug in the MiniMax 2.7 portfolio pipeline that was preventing it from making trades due to JSON parsing failures:
- **Lambda Scoping Bug Fix**: Fixed a variable scoping bug in `_try_parse_decisions_response` in `apps/engine/core/llm/analysis.py` where fallback repair strategies closed over strategies but evaluated the original, un-repaired payload instead of the repaired/copied elements (`repaired`, `data_copy`, `parsed`). Addressed this by properly binding variables to default arguments within lambda scopes (e.g., `lambda d, r=repaired: ...`).
- **Observability Tracing**: Removed the arbitrary `max_retries` strategy constraint so the parser attempts all available repair strategies. If all strategies fail, we now aggregate and log the exact exceptions and validation details under a single warning block, complying with **GEMINI.md Principle 5**.
- **TDD Verification**: Added a unit test `test_try_parse_escaped_json_string_repair` in a new test file `apps/engine/tests/test_minimax_repair_bug.py` to ensure escaped JSON repair logic functions correctly. Verified 100% test success and 85% test coverage.
- **Documentation**: Updated the [[concepts/minimax-portfolio]] concept page to reflect the new robust scoping and observability mechanisms.

## [2026-05-28] fix | MiniMax 2.7 Parsing Scoping Bug and Improved Observability

Resolved a critical scoping bug in the MiniMax 2.7 portfolio pipeline that was preventing it from making trades due to JSON parsing failures:
- **Lambda Scoping Bug Fix**: Fixed a variable scoping bug in `_try_parse_decisions_response` in `apps/engine/core/llm/analysis.py` where fallback repair strategies closed over strategies but evaluated the original, un-repaired payload instead of the repaired/copied elements (`repaired`, `data_copy`, `parsed`). Addressed this by properly binding variables to default arguments within lambda scopes (e.g., `lambda d, r=repaired: ...`).
- **Observability Tracing**: Removed the arbitrary `max_retries` strategy constraint so the parser attempts all available repair strategies. If all strategies fail, we now aggregate and log the exact exceptions and validation details under a single warning block, complying with **GEMINI.md Principle 5**.
- **TDD Verification**: Added a unit test `test_try_parse_escaped_json_string_repair` in a new test file `apps/engine/tests/test_minimax_repair_bug.py` to ensure escaped JSON repair logic functions correctly. Verified 100% test success and 85% test coverage.
- **Documentation**: Updated the [[concepts/minimax-portfolio]] concept page to reflect the new robust scoping and observability mechanisms.

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

