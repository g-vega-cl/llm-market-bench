## [2026-06-15] bugfix | Fix portfolios page benchmark selection cache pollution

Resolved a bug where selecting alternative benchmarks (such as QQQ, GLD, TLT) in the portfolios comparison chart failed to display their respective performance lines:
- **React Query Cache Pollution**: Removed stale `initialData` parameter from `useSuspenseQuery` inside `PortfoliosPage.tsx` to stop old default ('SPY') benchmark data from seeding and freezing new query keys.
- **Smooth Suspense Transition**: Integrated `React.useTransition` to wrap `setSelectedBenchmark` updates, allowing client-side background refetching to transition smoothly without triggering hard-suspense loaders.
- **TDD Regression Suite**: Added `PortfoliosPageBenchmark.test.tsx` which simulates switching benchmark options and verifies the chart receives the correct dataset.
- **Documentation**: Documented this specific React Query `initialData` gotcha in `concepts/tanstack-query.md`.

**See**: [[concepts/tanstack-query]], [PortfoliosPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/portfolios/pages/PortfoliosPage.tsx)

## [2026-06-15] fix | Eliminate benchmark switch flash and add D3 fade transition

Root-caused and fixed a visual flash in the portfolio comparison chart when switching the benchmark dropdown:

- **Root cause 1 — `key={selectedBenchmark}` on chart component**: React interpreted a different `key` as a different component and fully unmounted + remounted the `<PortfolioComparisonChart>` on every benchmark change, destroying the D3 SVG and all state. Removed the `key` prop; the chart's existing `useEffect([data, benchmarkData, selectedBenchmark])` already handles in-place re-draws correctly.
- **Root cause 2 — `useSuspenseQuery` without `placeholderData`**: When the query key changed (new benchmark), `useSuspenseQuery` suspended immediately (no cache hit), triggering the nearest Suspense fallback and blanking the chart area. Added `placeholderData: keepPreviousData` so the previous benchmark's cached data stays visible while the new fetch runs.
- **Smooth D3 animation**: Added a 350ms `easeQuadInOut` opacity fade-in transition to all chart paths (portfolio lines and benchmark line) on every D3 redraw. Combined with the two fixes above, switching benchmarks now produces a smooth animated handoff instead of a hard snap.
- **TDD regression guard**: Added a second test in `PortfoliosPageBenchmark.test.tsx` that captures the DOM node reference before a benchmark switch and asserts it is the exact same node after — a structural guarantee that no unmount/remount occurred.
- **Documentation**: Updated `concepts/tanstack-query.md` with the corrected `keepPreviousData` solution pattern and a new pitfall entry for the `key={dynamicValue}` anti-pattern. Updated `sources/web-portfolios-source.md` with a Smooth Benchmark Switching bullet.

**See**: [[concepts/tanstack-query]], [[sources/web-portfolios-source]], [PortfoliosPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/portfolios/pages/PortfoliosPage.tsx), [PortfolioComparisonChart.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/portfolios/components/PortfolioComparisonChart.tsx)

## [2026-06-16] fix | Hardcode ingest schedule to UTC for DST correctness

GitHub Actions does not correctly handle DST when using the `timezone` field — it treats `America/New_York` as always UTC-5. The ingest workflow schedule has been converted to explicit UTC times (13:35, 15:35, 19:00) to match the intended 9:35 AM, 11:35 AM, and 3:00 PM ET during EDT (UTC-4). This ensures the pipeline runs at the correct market hours year-round without relying on GitHub's broken DST support.

## [2026-06-16] documentation | Simplified pipeline wiki and hardcoded ingest schedule for DST

The `how-it-works.json` data source has been emptied, removing the detailed 7-phase breakdown from the web UI. The [[entities/pipeline]] wiki page has been condensed to a high-level 6-phase overview with UTC schedule details. The ingest workflow cron is now hardcoded to UTC to avoid GitHub Actions DST handling bug.

## [2026-06-16] refactor | Unified HomePage dashboard with table layout

Merged separate mobile/desktop views into a single responsive Dashboard component. Replaced portfolio cards with a compact table row layout, collapsed the market feeling analysis into a toggleable section, and removed the desktop-specific BenchmarkCard and MarketFeelingCard in favor of inline rows. Simplified the sentiment header and removed the background selector experiment logic.

## [2026-06-16] fix | MiniMax empty response and DeepSeek tool call narration anomalies

Resolved two critical LLM engine anomalies identified during the 2026-06-16 15:21 UTC ingest run audit:
- **MiniMax Empty Response & Tag Clash**: Stripped `<think>...</think>` reasoning blocks (including unclosed blocks) from the raw response content in `_analyze_with_minimax` before attempting JSON extraction, preventing parser clashes with internal thoughts. Coerced `None` response content to `""` to prevent attribute errors, and passed `response_format={"type": "json_object"}` to force valid JSON output.
- **DeepSeek Tool Call Narration**: Disabled `thinking` mode during the info-gathering tool execution loop (`run_tool_loop`) for DeepSeek to stop the reasoning model from narrating its planned tool calls in text instead of emitting structured API `tool_calls` objects.
- **DeepSeek Final Extraction Thinking**: Explicitly enabled `thinking` mode (`extra_body={"thinking": {"type": "enabled"}}`) in the final extraction phase inside `analyze_with_provider` so the model uses its full reasoning capacity to formulate the final trade decisions.
- **TDD Verification**: Created `test_reproduce_deepseek_minimax.py` reproducing the anomalies and verifying the fixes. Passed 100% of the 757-test suite.

**See**: [[concepts/model-anomalies]], [[concepts/tool-enforcement]], [analysis.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/analysis.py), [deepseek.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/handlers/deepseek.py), [test_reproduce_deepseek_minimax.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_reproduce_deepseek_minimax.py)

## [2026-06-16] fix | MiniMax empty response and DeepSeek tool call narration anomalies

Resolved two critical LLM engine anomalies identified during the 2026-06-16 15:21 UTC ingest run audit:
- **MiniMax Empty Response & Tag Clash**: Stripped ` thinking... response` reasoning blocks (including unclosed blocks) from the raw response content in `_analyze_with_minimax` before attempting JSON extraction, preventing parser clashes with internal thoughts. Coerced `None` response content to `""` to prevent attribute errors, and passed `response_format={"type": "json_object"}` to force valid JSON output.
- **DeepSeek Tool Call Narration**: Disabled `thinking` mode during the info-gathering tool execution loop (`run_tool_loop`) for DeepSeek to stop the reasoning model from narrating its planned tool calls in text instead of emitting structured API `tool_calls` objects.
- **DeepSeek Final Extraction Thinking**: Explicitly enabled `thinking` mode (`extra_body={"thinking": {"type": "enabled"}}`) in the final extraction phase inside `analyze_with_provider` so the model uses its full reasoning capacity to formulate the final trade decisions.
- **TDD Verification**: Created `test_reproduce_deepseek_minimax.py` reproducing the anomalies and verifying the fixes. Passed 100% of the 757-test suite.

**See**: [[concepts/model-anomalies]], [[concepts/tool-enforcement]]

## [2026-06-16] feature | Terminal-Friendly Visual Planning Framework

Implemented a terminal-native visual planning framework to allow agents to generate rich, visual, Markdown-compliant plans:
- **Concept Page**: Created [[concepts/visual-planning]] detailing Unicode box-drawing, ASCII flowcharts, progress trackers, and UI mockups.
- **Mandatory Agent Guideline**: Updated the Plan First instructions in [[entities/gemini]] and [[concepts/agent-workflow]] to require visual planning for all non-trivial tasks.
- **Wiki Integration**: Indexed and cross-linked the new planning page within the wiki index.

**See**: [[concepts/visual-planning]], [[concepts/agent-workflow]], [[entities/gemini]]

## [2026-06-16] documentation | Document Supabase Google OAuth Redirect Whitelisting

Created a concept page to detail how Supabase Auth whitelisting and fallback logic handles requested redirects. Documents the difference between local dev ports (Netlify dev 3000 vs. Vite 3005) and production deployment whitelists, providing step-by-step instructions to prevent redirect-loop fallbacks to localhost:3000.

**See**: [[concepts/supabase-redirect-whitelisting]], [[entities/web-app]]

## [2026-06-17] feature | Prediction Market Tools and Database Schema

Added prediction market capabilities to the engine:
- New DB table `prediction_market_snapshots` for storing Polymarket/Kalshi odds
- Two new LLM tools: `search_prediction_markets` (DB search) and `get_prediction_market_odds` (live API fetch)
- Tool definitions registered across all providers (OpenAI, Anthropic, Gemini)
- Execution handlers with dispatcher routing
- Unit tests for search, live odds, and handler dispatch
- Wiki updates: agents, database, ingestion pages updated
- ROADMAP.md: added options/info item

## [2026-06-17] refactor | Remove progress bar from visual planning framework

Refactored the visual planning framework:
- **Removed Progress Bar**: Removed the 0%-100% Unicode progress bars from `wiki/concepts/visual-planning.md` instructions, tables, and templates.
- **Status Board**: Renamed "Progress Board" and "Progress Tracker" to "Status Board", focusing exclusively on the active phase rather than completion percentages.

**See**: [[concepts/visual-planning]]

## [2026-06-17] feature | LLM Leaderboard & Screening Tool

Implemented a comprehensive screening and ranking leaderboard for comparing LLMs based on trading performance, reasoning quality, and consistency:
- **Database Layer**: Deployed Supabase migration `20260618000000_create_llm_leaderboard_rpc.sql` creating the `get_llm_leaderboard_metrics` function to dynamically calculate returns, realized P&L, win rates, verifier approval rates, average confidence, and consistency scores over selected timeframes (7d, 30d, 90d, All-Time).
- **TypeScript Integration**: Added `LLMLeaderboardRow` types to `@llm-market-bench/database`.
- **API Fetcher**: Created `fetch-leaderboard.ts` to execute RPC queries from the TanStack Start server layer.
- **Visual Page & Routing**: Added new route `/leaderboard` and created the `LeaderboardPage` hub with a timeframe switcher.
- **Aesthetic Components**: Designed a Bloomberg-meets-Wired podium layout (`LeaderboardPodium.tsx`), a sortable data grid (`LeaderboardTable.tsx`), and a side-by-side comparative diagnostics utility (`ModelComparison.tsx`) using the design system's glass Cards, Tables, and Badges.
- **TDD & Quality**: Created `fetch-leaderboard.test.ts` and `LeaderboardPage.test.tsx` verifying data aggregation, metrics calculations, UI rendering, and comparison interactions. Passed 100% of test suites with zero lint or formatting errors.

**See**: [leaderboard route](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/routes/leaderboard/index.tsx), [fetch-leaderboard.ts](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/leaderboard/api/fetch-leaderboard.ts)

## [2026-06-17] feature | LLM Leaderboard & Screening Tool

Implemented a comprehensive screening and ranking leaderboard for comparing LLMs based on trading performance, reasoning quality, and consistency:
- **Database Layer**: Deployed Supabase migration `20260618000000_create_llm_leaderboard_rpc.sql` creating the `get_llm_leaderboard_metrics` function to dynamically calculate returns, realized P&L, win rates, verifier approval rates, average confidence, and consistency scores over selected timeframes (7d, 30d, 90d, All-Time).
- **TypeScript Integration**: Added `LLMLeaderboardRow` types to `@llm-market-bench/database`.
- **API Fetcher**: Created `fetch-leaderboard.ts` to execute RPC queries from the TanStack Start server layer.
- **Visual Page & Routing**: Added new route `/leaderboard` and created the `LeaderboardPage` hub with a timeframe switcher.
- **Aesthetic Components**: Designed a Bloomberg-meets-Wired podium layout (`LeaderboardPodium.tsx`), a sortable data grid (`LeaderboardTable.tsx`), and a side-by-side comparative diagnostics utility (`ModelComparison.tsx`) using the design system's glass Cards, Tables, and Badges.
- **TDD & Quality**: Created `fetch-leaderboard.test.ts` and `LeaderboardPage.test.tsx` verifying data aggregation, metrics calculations, UI rendering, and comparison interactions. Passed 100% of test suites with zero lint or formatting errors.

## [2026-06-17] feature | Leaderboard MiniMax Bypass & Card Height Fixes

Updated the LLM Leaderboard to ignore verifier metrics for MiniMax-M3 and fix card height overflow:
- **Database Layer**: Added migration `20260618000001_update_llm_leaderboard_rpc_minimax.sql` that sets `verifier_approval_rate` to NULL and bases reasoning quality and composite scores solely on confidence for MiniMax-M3.
- **Frontend Filtering**: Modified `fetch-leaderboard.ts` to filter out old/inactive models not present in the active `MODELS` config.
- **Card Styling & Height**: Replaced fixed height `md:h-[...]` with dynamic `md:min-h-[...] h-auto` on the Podium cards to prevent floating text overflow, extracting `PodiumCard` to resolve Biome complexity warnings.
- **UI Logic**: Handled null verifier approval rates gracefully with an em-dash (`—`) and disabled win/loss highlighting for it in side-by-side comparison.
- **Type Safety**: Updated `LLMLeaderboardRow` definition to allow `verifier_approval_rate` to be `number | null`.
- **TDD Tests**: Updated tests to verify null-safety, em-dash display, and filtering of inactive models.

**See**: [[entities/llm-leaderboard]], [LeaderboardPodium.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/leaderboard/components/LeaderboardPodium.tsx), [fetch-leaderboard.ts](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/leaderboard/api/fetch-leaderboard.ts)

## [2026-06-17] feature | S&P 500 Market Health Barometer & Company Earnings Tools

Added two new LLM agent tools (`get_market_health_barometer` and `get_earnings_history`) and a daily S&P 500 barometer aggregator script. The barometer computes cap-weighted Trailing P/E, Forward P/E, P/S, P/B, and earnings beat rate from top 100 S&P 500 constituents, stores daily snapshots in `market_barometer_history`, and injects the latest snapshot into the global macro context. The earnings tool fetches ticker-specific earnings history (actuals vs estimates, surprise %, upcoming dates) via FMP and yfinance. Both tools are registered across Anthropic, Gemini, and OpenAI handlers. The barometer is displayed on the HomePage dashboard with a glassmorphism widget and animated beat rate gauge.

**See**: [[concepts/fundamental-analysis]], [[entities/web-app]], [[entities/macro-tracker]]

## [2026-06-17] feature | S&P 500 Market Health Barometer Audit Page & transparent constituent tracking

Implemented constituent-level audit tracking for S&P 500 Market Health Barometer:
- **Database Layer**: Added migration `20260620000000_add_constituents_data_to_barometer.sql` introducing a `constituents_data` JSONB column to the `market_barometer_history` table to store atomic daily constituent snapshot weights. Manually updated `supabase-types.ts` Row, Insert, and Update interface definitions.
- **Data Engine**: Updated the daily calculation script `update_market_barometer.py` to extract `companyName` and construct/persist the serialized array of constituent valuation metrics (market cap, price, trailing/forward P/E, P/B, P/S, earnings beat status) alongside the aggregates.
- **Frontend APIs**: Added `fetchMarketBarometerDates` and `fetchMarketBarometerForDate` loader functions in `fetch-barometer.ts` to retrieve historical dates and daily snapshots.
- **Audit View Routing**: Created the `/barometer-audit` route with TanStack Start's URL search params loader schema mapping, making selecting historical dates fully shareable and refreshable without client-side state.
- **High-Density Audit Dashboard**: Created `BarometerAuditPage.tsx` outlining standard formulas (cap-weighted averages) and presenting a high-density constituent table with reactive client-side search, column sorting, and beat-status filtering. Added an "Audit Data" link to the dashboard's barometer header.
- **TDD & Code Quality**: Updated Python backend tests to verify constituent snapshot generation. Created Vitest frontend test `barometer-audit.test.tsx` verifying data filtering, search, sorting, and fallback notice behaviors. Re-organized TS imports and refactored helper functions to fully comply with Biome's strict formatting and cognitive complexity constraints.

**See**: [[entities/web-app]], [BarometerAuditPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/home/pages/BarometerAuditPage.tsx), [update_market_barometer.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/scripts/update_market_barometer.py)

## [2026-06-18] fix | DeepSeek / Anthropic Hard Enforcement and MiniMax JSON Repair Bugs

Resolved two critical bugs in the LLM analysis and consensus pipeline:
- **DeepSeek/Anthropic Message Preservation**: Fixed a bug where `unflattened_messages` was captured *after* provider-specific message preparations (such as DeepSeek's `prepare_messages_for_instructor` or Anthropic's flattening) had already run and stripped `tool_calls` from the messages. The copy is now captured immediately after the tool execution loops run, preserving full `tool_calls` history for Layer 3 Hard Tool Enforcement validation.
- **MiniMax JSON Repair**: Improved `_repair_json_string` in `analysis.py` to identify and escape unescaped single backslashes that mistakenly escape closing JSON delimiter quotes (e.g. `basis\"}` resulting from trailing markdown/backslash content), preventing `JSONDecodeError` on MiniMax and other raw JSON-response models.
- **TDD verification**: Added new tests `test_deepseek_first_run_tool_check_preserves_calls` in `test_tool_enforcement.py` and `test_try_parse_json_with_trailing_backslash_escape` in `test_minimax_repair_bug.py`. Verified that the complete 773-test engine suite passes.

**See**: [[concepts/tool-enforcement]], [analysis.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/analysis.py), [test_tool_enforcement.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_tool_enforcement.py), [test_minimax_repair_bug.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_minimax_repair_bug.py)

## [2026-06-18] feature | Memories inline newsletter snippet citations and secure RPC


Implemented secure, lazy-loaded inline newsletter source citations for memories:
- **Database Layer**: Deployed Supabase migration `20260621000000_add_referenced_newsletters_rpc.sql` creating the `get_referenced_newsletter_snapshots` function with `SECURITY DEFINER` access. This securely exposes only those newsletter snippets that are explicitly linked inside a promoted memory's `metadata.source_ids`.
- **API Fetcher**: Added `fetchReferencedNewsletters` in `fetch-memories.ts` to call the new RPC.
- **Frontend Integration**: Updated `MemoryCard.tsx` to extract `source_ids` and query for their content on-demand via TanStack Query (`useQuery`) when a card is expanded.
- **Aesthetic UI**: Rendered source cards inside the expanded panel showing sender, subject, formatted date, and a scrollable viewport of the original news chunk.
- **TDD & Code Quality**: Created integration test `test_referenced_newsletters.py` verifying correct database RPC filters, added unit tests in `fetch-memories.test.ts`, and updated `MemoryCard.test.tsx` and `MemoriesList.test.tsx` to provide `QueryClientProvider` context. All tests pass with zero Biome/Ruff linting warnings.

**See**: [[concepts/memory-feedback]], [[entities/web-app]], [MemoryCard.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/memories/components/MemoryCard.tsx), [test_referenced_newsletters.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_referenced_newsletters.py)

## [2026-06-19] feature | Add Price-to-FCF (P/FCF) metric to backend engine, LLM tools, and web barometer

Added Price-to-Free-Cash-Flow (P/FCF) metric across the entire stack:
- **Database Layer**: Created migration `20260621100000_add_pfcf_to_barometer.sql` to add `pfcf_ratio` column to the `market_barometer_history` table in Supabase. Manually updated `supabase-types.ts` Row, Insert, and Update interface definitions.
- **Backend Provider & Tools**: Updated `FMPProvider` and `YFinanceProvider` to mathematically calculate constituent-level `priceToFreeCashFlowsRatio` from FCF yields (`1 / freeCashFlowYield`). Updated `execute_key_metrics_tool` and `execute_market_health_barometer_tool` to format and output P/FCF to the LLMs.
- **Barometer Aggregator**: Updated `update_market_barometer.py` to retrieve constituent P/FCF, calculate the cap-weighted Index P/FCF, exclude companies with negative or zero free cash flow to prevent multiple distortion, and save index-level and constituent-level results to Supabase.
- **Frontend Dashboard & Audit**: Updated `HomePage.tsx` to render the aggregate Price-to-FCF ratio on the S&P 500 Market Health Barometer glassmorphism card. Updated `BarometerAuditPage.tsx` to display aggregate P/FCF, include a P/FCF column in the constituent weightings table, and support sorting by P/FCF.
- **TDD & Code Quality**: Added unit tests verifying `priceToFreeCashFlowsRatio` retrieval and formatting in `test_key_metrics_tool.py`. Updated `test_market_barometer.py` to verify cap-weighted index P/FCF calculation and negative FCF exclusion logic. Updated Vitest suite in `barometer-audit.test.tsx` to verify P/FCF rendering on the audit dashboard. All frontend and backend lints and tests pass.

**See**: [[concepts/fundamental-analysis]], [[entities/web-app]], [HomePage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/home/pages/HomePage.tsx), [BarometerAuditPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/home/pages/BarometerAuditPage.tsx), [update_market_barometer.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/scripts/update_market_barometer.py)

## [2026-06-19] improvement | MiniMax error handling, market status lock, FMP quarterly fallback, consensus await

- **MiniMax error logging**: Enhanced MiniMaxClient and analysis.py to log raw API responses, finish reasons, and processing times when MiniMax returns empty or unparseable content. Added explicit handling for HTTP status errors, `base_resp` business-logic errors, generic `error` fields, and empty `choices` arrays — with dedicated error/warning log messages for each case.
- **Market status thundering herd prevention**: Added `asyncio.Lock` to `MarketDataManager.is_market_open()` to serialize concurrent calls, ensuring only one FMP API request is made per cache TTL window. Fetched-at timestamps now use UTC consistently.
- **FMP quarterly → annual fallback**: `FMPProvider.get_key_metrics()` now falls back to `period="annual"` when quarterly metrics return a non-200 status code (e.g., 402/403 for unsupported symbols).
- **Consensus await**: `_stage_decision_processing()` now awaits the background consensus task before returning, ensuring consensus and momentum processing complete before the pipeline exits.

**See**: [[concepts/minimax-portfolio]], `apps/engine/core/llm/minimax.py`, `apps/engine/core/llm/analysis.py`, `apps/engine/execution/market_data.py`, `apps/engine/execution/providers/fmp.py`, `apps/engine/main.py`

## [2026-06-21] refactor | Portfolios page client-side timeframe filtering & D3 alignment fix

Refactored the Portfolios page comparison data flow to support client-side timeframe filtering (7d, 30d, 90d, all) with zero network requests on filter changes.

**Backend changes**:
- `getComparisonData` server function now fetches full portfolio history (36500 days) and all 4 benchmarks (SPY, QQQ, DIA, IWM) in a single payload
- Removed `benchmark` and `maxDays` input validation — comparison query key is now parameterless

**Client-side changes**:
- `PortfoliosPage.tsx` gained a `timeframe` state with `useMemo`-based data slicing and re-normalization (returns reset to 0% at window start)
- `PortfolioComparisonChart.tsx` now uses a shared `dateRange` computed via `d3.extent` across all portfolios, fixing the bug where x-axis domain was derived from `data[0]` only
- Timeframe buttons use `Button` with `solid`/`ghost` variants and `success`/`neutral` color schemes

**Test coverage**:
- Added test verifying 30D filter slices data client-side without additional network calls
- Updated mock signatures to match new parameterless `comparisonFetchFn` interface

**See**: [[sources/web-portfolios-source]], [[concepts/tanstack-query]]

## [2026-06-21] feature | Interactive Daily Score Progression Inspection

Added interactive score inspection and date display on the Day-by-Day Score Progression cards in the Auto-Research page.
- **Date Display**: Parses `week_start` and renders individual offset date badges (e.g. `6/3` for Wednesday) next to day abbreviations.
- **Constituents inspection**: Added stateful selection of weekdays. Clicking any non-future card reveals a detailed, scaled constituents breakdown panel showing excess return, opportunity cost, risk penalty, returns vs. SPY and Do-Nothing, and the step-by-step arithmetic equation.
- **Refactoring & Accessibility**: Split card item rendering into a clean, semantic, accessible `<button>`-based `CheckpointCard` sub-component, reducing cognitive complexity and ensuring full keyboard and screen-reader support.
- **TDD Safety Net**: Added unit tests in `DailyScoreDisplay.test.tsx` verifying correct date rendering, clickable state updates, toggle closing, and future-day disabled states.

## [2026-06-21] refactor | Scoped Portfolio and Sector Predictor Prompt Experiments

Separated the views and prompt experiments for the model portfolios (auto-research) and the market sector predictors to align with vertical design guidelines and prevent mixed metrics.

**Backend & API Changes**:
- **Portfolio Autoresearch API**: Restricted `fetchExperiments` to query only `CORE_ANALYSIS_SYSTEM_PROMPT` variants, keeping the Auto-Research page focused on portfolio prompts.
- **Predictor Experiments API**: Introduced `fetchPredictorExperiments` under `fetch-predictions.ts` to retrieve `SECTOR_PREDICTOR_PROMPT` prompt variants.
- **Route Loader**: Modified the `/ai-predictions` route to load both predictions and predictor experiments.

**Frontend UI Changes**:
- **Predictions Page Tabs**: Built a sleek, glassmorphic tabbed layout on the AI Sector Predictions Arena page, splitting it into **Arena Dashboard** (forecasting track record) and **Prompt Auto-Research** (prompt evolution).
- **Prompt Auto-Research Dashboard**: Displayed all-time baseline scores, active prompt variant details, scoring formula breakdowns, and the history of `SECTOR_PREDICTOR_PROMPT` mutations.
- **Unified Diff Inspection**: Reused the Longest Common Subsequence line diff algorithm (`diffLines`) to render prompt modifications and collapsible changes-only diffs.

**TDD & Linting**:
- **API Test Suite**: Authored TDD tests verifying correct table query routing and scoping filters for both APIs.
- **Strict Format Enforcement**: Verified 100% passing test suite (274 tests) and clean Biome formatting/linter conformance.

**See**: [[entities/sector-predictor-arena]], [[entities/autoresearch]]

## [2026-06-21] bugfix | DeepSeek Verifier Response Model Schema Crash

Resolved a critical verification extraction crash for non-Gemini models (specifically DeepSeek) in `verify_trading_decision`:
- **Problem**: When executing `verify_trading_decision`, the engine passed `response_model = list[VerificationResult]` to support Gemini's multi-block tool calling behavior. However, DeepSeek runs in Markdown JSON mode (`mode=instructor.Mode.MD_JSON`). Under `MD_JSON` mode, `instructor` attempts to retrieve the JSON schema by calling `.model_json_schema()` on the `response_model` directly, which threw an `AttributeError` for the native python `list` class. This crashed the verifier and resulted in all DeepSeek trades defaulting to `REJECTED_VERIFICATION`.
- **Fix**: Modified [verification.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/verification.py) to dynamically resolve the `response_model` (uses `list[VerificationResult]` only when `provider == "gemini"` and `VerificationResult` directly for other models). The output is flattened using `ensure_list` before downstream evaluation.
- **TDD Safety Net**: Authored a mock-network test `test_verification_deepseek_schema_list_vs_single` in [test_verification.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_verification.py) to verify schema parsing and prevent future regressions.

**See**: [[concepts/tool-enforcement]], [verification.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/verification.py), [test_verification.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_verification.py)

## [2026-06-21] bugfix | FMP retry/timeout, MiniMax token limit, DiscoveryAgent ticker validation

Six bug fixes addressing reliability issues found in production logs:

- **FMP Provider retries with exponential backoff**: `get_ticker_data` and `get_history` now retry failed requests up to `MARKET_DATA_RETRIES` (default 2) times with exponential backoff (`2^attempt` seconds). 402 quota errors are not retried. This resolves the ConnectTimeout failures for SPOT, PPTA, IBM, and UPS observed in logs.
- **FMP HTTP timeouts**: All `httpx.AsyncClient()` instances in `fmp.py` now use `httpx.Timeout(10.0)` to prevent hanging connections.
- **MiniMax token limit increase**: `market_feeling.py` now passes `max_completion_tokens=16384` (up from 1024) to prevent JSON truncation in the `why_explanation` field. The 1024 limit was causing `Unterminated string` parse failures.
- **MiniMax empty content guard**: `chat_with_json_response` in `minimax.py` now safely handles `None` content by coalescing to `""` before `.strip()`, and raises `ValueError` on empty content instead of crashing.
- **DiscoveryAgent ticker validation**: `_parse_json_response` now validates ticker format (1-5 chars, `^[A-Z0-9.\-]+$`) before returning, filtering out obviously invalid tickers like `HONIV` early.
- **FMP key-metrics 402 fallback**: `get_key_metrics` now returns `[]` instead of crashing when both quarterly and annual endpoints return non-200 status codes.

**See**: `apps/engine/execution/providers/fmp.py`, `apps/engine/core/llm/minimax.py`, `apps/engine/analysis/market_feeling.py`, `apps/engine/analysis/discovery_agent.py`, `apps/engine/tests/test_fmp_error_logging.py`

## [2026-06-21] bugfix | FMP retry/timeout, MiniMax token limit, DiscoveryAgent ticker validation

Six bug fixes addressing reliability issues found in production logs:

- **FMP Provider retries with exponential backoff**: `get_ticker_data` and `get_history` now retry failed requests up to `MARKET_DATA_RETRIES` (default 2) times with exponential backoff (`2^attempt` seconds). 402 quota errors are not retried. This resolves the ConnectTimeout failures for SPOT, PPTA, IBM, and UPS observed in logs.
- **FMP HTTP timeouts**: All `httpx.AsyncClient()` instances in `fmp.py` now use `httpx.Timeout(10.0)` to prevent hanging connections.
- **MiniMax token limit increase**: `market_feeling.py` now passes `max_completion_tokens=16384` (up from 1024) to prevent JSON truncation in the `why_explanation` field. The 1024 limit was causing `Unterminated string` parse failures.
- **MiniMax empty content guard**: `chat_with_json_response` in `minimax.py` now safely handles `None` content by coalescing to `""` before `.strip()`, and raises `ValueError` on empty content instead of crashing.
- **DiscoveryAgent ticker validation**: `_parse_json_response` now validates ticker format (1-5 chars, `^[A-Z0-9.\-]+$`) before returning, filtering out obviously invalid tickers like `HONIV` early.
- **FMP key-metrics 402 fallback**: `get_key_metrics` now returns `[]` instead of crashing when both quarterly and annual endpoints return non-200 status codes.

**See**: `apps/engine/execution/providers/fmp.py`, `apps/engine/core/llm/minimax.py`, `apps/engine/analysis/market_feeling.py`, `apps/engine/analysis/discovery_agent.py`, `apps/engine/tests/test_fmp_error_logging.py`

## [2026-06-21] refactor | Restructure prompt experiment statuses for baseline ratchet

Aligned the prompt auto-research engine and dashboard status definitions with the ratchet philosophy:
- **Database Schema**: Deployed migration `20260623000000_update_prompt_experiments_status.sql` changing the status constraint from `('active', 'kept', 'discarded', 'crashed')` to `('active', 'baseline', 'saved', 'discarded', 'crashed')`. Migrated all existing `kept` rows, setting the highest-scoring variants to `baseline` and others to `saved`.
- **Autoresearch Ratchet**: Modified `prompt_store.py` and `predictor_autoresearch.py` to transition newly evaluated high-scoring prompts to `baseline` status, while demoting prior baselines to `saved`.
- **Active Prompt Timeline**: Removed the identical-prompt return skip in `predictor_autoresearch.py` so a new active variant is always inserted weekly, avoiding timeline gaps.
- **Frontend Badges**: Updated `AIPredictionsPage.tsx` and `ExperimentList.tsx` status indicators to display `'Baseline'` and `'Saved'` badges instead of `'Kept'`. Updated the description in `ScoreCalculation.tsx`.
- **TDD Tests**: Updated `test_sector_predictions_audit.py` to assert new status transitions and added `test_predictor_autoresearch_always_inserts_active` to guard the weekly active prompt sequence.

**See**: [[entities/sector-predictor-arena]], [[entities/autoresearch]], [prompt_store.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/autoresearch/prompt_store.py), [predictor_autoresearch.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tasks/predictor_autoresearch.py)

## [2026-06-22] feature | On-Demand News Summaries, Dynamic RAG, and MiniMax Tool Calling Integration

Implemented a hybrid newsletter summary pre-filtering and dynamic retrieval mechanism, dynamic pgvector memories search, and native tool-calling integration for the MiniMax model:
- **Newsletter Menu Triage**: Added a pre-filtering task (`apps/engine/analysis/pre_filter.py`) utilizing `deepseek-v4-flash` via Instructor to generate concise 1-2 sentence summaries (`NewsletterTriageResponse`) of daily newsletter chunks. These summaries are formatted as a menu inside the Analysis Agent prompt instead of the full raw emails to reduce token bloat.
- **Dynamic Content Fetching**: Added a `fetch_newsletter_content` tool to retrieve the full de-advertised text of target newsletters from the database on demand when a menu summary warrants deeper investigation.
- **Dynamic memories RAG**: Added a `search_past_memories` tool allowing the Analysis Agent to execute dynamic pgvector semantic searches against past events and historical trade lessons.
- **MiniMax Tool Calling**: Configured `MiniMax-M3` to use the standard OpenAI tool execution handler, enabling native tool calling and Instructor structured output extraction, and bypassing the raw text JSON repair pipeline during primary analysis.
- **System Prompt & Auto-Research Compatibility**: Embedded the instructions for the new on-demand tools inside the immutable `SYSTEM_PROMPT_CONSTRAINTS_HEADER` constant to keep them safe from auto-research weekly modifications.
- **TDD Verification**: Authored `test_newsletter_menu_flow.py` and updated call counts in `test_call_counts.py` and minimax pipeline integration tests in `test_minimax_pipeline.py`. 100% of tests pass.

**See**: [[concepts/rag-strategy]], [[concepts/minimax-portfolio]], [[concepts/agents]], [[entities/engine]], [pre_filter.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/analysis/pre_filter.py), [tools.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/tools.py), [analysis.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/analysis.py), [test_newsletter_menu_flow.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_newsletter_menu_flow.py)

## [2026-06-22] feature | Newsletter Pre-Filter, Dynamic RAG Tools, and MiniMax Tool-Calling Integration

Implemented a hybrid newsletter summary pre-filtering and dynamic retrieval mechanism, dynamic pgvector memories search, and native tool-calling integration for the MiniMax model:
- **Newsletter Menu Triage**: Added a pre-filtering task (`apps/engine/analysis/pre_filter.py`) utilizing `deepseek-v4-flash` via Instructor to generate concise 1-2 sentence summaries (`NewsletterTriageResponse`) of daily newsletter chunks. These summaries are formatted as a menu inside the Analysis Agent prompt instead of the full raw emails to reduce token bloat.
- **Dynamic Content Fetching**: Added a `fetch_newsletter_content` tool to retrieve the full de-advertised text of target newsletters from the database on demand when a menu summary warrants deeper investigation.
- **Dynamic memories RAG**: Added a `search_past_memories` tool allowing the Analysis Agent to execute dynamic pgvector semantic searches against past events and historical trade lessons.
- **MiniMax Tool Calling**: Configured `MiniMax-M3` to use the standard OpenAI tool execution handler, enabling native tool calling and Instructor structured output extraction, and bypassing the raw text JSON repair pipeline during primary analysis.
- **System Prompt & Auto-Research Compatibility**: Embedded the instructions for the new on-demand tools inside the immutable `SYSTEM_PROMPT_CONSTRAINTS_HEADER` constant to keep them safe from auto-research weekly modifications.
- **TDD Verification**: Authored `test_newsletter_menu_flow.py` and updated call counts in `test_call_counts.py` and minimax pipeline integration tests in `test_minimax_pipeline.py`. 100% of tests pass.

**See**: [[concepts/rag-strategy]], [[concepts/minimax-portfolio]], [[concepts/agents]], [[entities/engine]], [pre_filter.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/analysis/pre_filter.py), [tools.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/tools.py), [analysis.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/analysis.py), [test_newsletter_menu_flow.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_newsletter_menu_flow.py)

## [2026-06-22] test | Add summarize_newsletters mock to analysis tests

Five analysis test files (`test_analysis_logic.py`, `test_batch_analysis.py`, `test_resilience.py`, `test_streaming_analysis.py`, `test_verification.py`) were updated to patch `analysis.pre_filter.summarize_newsletters` with an `AsyncMock(return_value={})`. This prevents tests from calling the real newsletter summarization function during analysis orchestration, which would fail without proper API credentials in CI. The `test_verification.py` file also gained a mock for `get_deepseek_client` to bypass `AsyncOpenAI` client construction in CI, allowing the test to focus on schema handling rather than network/auth concerns.

## [2026-06-22] bugfix | Fix test_verification_deepseek_schema_list_vs_single CI failure (wrong patch target)

`tests/test_verification.py::test_verification_deepseek_schema_list_vs_single` failed in CI with `openai.OpenAIError: Missing credentials` despite no real API calls being made.

- **Root cause**: The test patched `core.llm.clients.get_deepseek_client`, but `verify_trading_decision` (`core/llm/verification.py:62`) looks up the client via the module-level dict `CLIENT_FACTORIES`, which is populated at import time with function references. Patching the module-level function attribute does **not** update the dict — the real factory still ran and `AsyncOpenAI.__init__` enforced credentials (`_enforce_credentials=True` default), failing without `DEEPSEEK_API_KEY` in CI.
- **Fix**: Changed the test to patch `core.llm.clients.CLIENT_FACTORIES` (with `mock_factories.get.return_value = MagicMock(return_value=mock_ds_client)`) and added a `close_client` mock — matching the convention already used by all 13 other tests in `tests/test_verification.py` and 3 in `tests/test_verification_retry.py`. Verified: the single test passes with no API keys set; full 14-test file passes.
- **Documentation**: Added an inline warning comment above `CLIENT_FACTORIES` in `core/llm/clients.py` explaining the import-time reference capture and pointing tests at the dict-patching pattern. Updated `[[sources/engine-testing-source]]` with a "LLM Client Factory Mocking" takeaway so future tests don't repeat the mistake.

**See**: [[sources/engine-testing-source]], [core/llm/clients.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/clients.py), [tests/test_verification.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_verification.py)

