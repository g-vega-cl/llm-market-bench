## [2026-07-02] feature | MiniMax Auto-Research Integration

Integrated the MiniMax-M3 portfolio trading agent into the autonomous prompt improvement loop (auto-research):
- **Auto-Research Active Prompt**: Added `"MiniMax-M3"` to `AUTORESEARCH_EXPERIMENT_OWNER_IDS` in `models.json`. When building the analysis system prompt, the engine now fetches the active database-backed experiment prompt instead of the hardcoded default prompt.
- **Unique Path Preservation**: Kept MiniMax-M3's unique characteristics fully intact. It continues to skip skeptical verification and standard tool-call loops, size trades at a default 20% position size, and execute using market orders with a ±0.5% price buffer.
- **Active Prompt Resiliency**: Added a fail-safe `try-except` block in `PromptFactory.build_analysis_messages` when loading the active database prompt. If database connectivity fails, the engine gracefully logs the traceback and falls back to the static baseline prompt, ensuring uninterrupted trading.
- **TDD & Code Quality**: Authored a new test suite in `test_minimax_autoresearch.py` verifying active prompt loading and protocol nudge prepending. Mocked active prompt store queries in existing test suites `test_minimax_anthropic_sdk.py` and `test_minimax_pipeline.py` using pytest fixtures to prevent unmocked network/database requests. All 803 pytest checks and Ruff formatting/linter audits pass cleanly.

**See**: [[concepts/minimax-portfolio]], [models.json](file:///Users/cesarvega/Documents/p-code/llm-market-bench/packages/config/models.json), [prompt_factory.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/prompt_factory.py), [test_minimax_autoresearch.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_minimax_autoresearch.py)

## [2026-06-30] fix | Sector Predictor Autoresearch Gemini Await-Bug & Frontend Dates

Fixed a critical await exception bug in the sector predictor autoresearch pipeline and enhanced the frontend model arena dashboard:
- **Autoresearch Await Fix**: Resolved a `TypeError` in `predictor_autoresearch.py` where it attempted to `await` the synchronous Gemini client completions call. Implemented a robust, dynamic awaitable check (`hasattr(resp_awaitable, "__await__")`) that works correctly for both the synchronous production client and the `AsyncMock`s used in tests.
- **Autoresearch Database Recovery**: Restored the missing active prompt variant pointers in the database by bootstrapping from the baseline. This allows future weekly scheduled autoresearch cron jobs to find and mutate the active predictor prompt.
- **Frontend Dashboard Enhancements**: Refactored `AIPredictionsPage.tsx` to display variant metadata (Type, Active Period, Parent Variant, Created At) inside the details card. Added sortable "Type" and "Period" columns to the sidebar experiment history table.
- **Cognitive Complexity Refactoring**: Extracted JSX layout components (`PredictorAutoresearchTab` and `PredictorExperimentRow`) to reduce cognitive complexity of the main page component below Biome's linting threshold.
- **TDD Verification**: Updated `test_predictor_autoresearch.py` to use a sync mock for completions and verified that the entire test suite passes successfully.

**See**: [[entities/sector-predictor-arena]], [predictor_autoresearch.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tasks/predictor_autoresearch.py), [AIPredictionsPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/ai-predictions/pages/AIPredictionsPage.tsx)

## [2026-06-29] feature | Quarterly Earnings Verification & Barometer Audit Earnings Date Column

Verified FMP earnings data availability and added report dates to the Market Health Barometer constituent audit table:
- **FMP Endpoint Verification**: Confirmed that `/earnings` (actuals vs estimates calendar) and `/income-statement?period=quarter` are fully accessible (HTTP 200) under our FMP subscription key, while quarterly valuation ratios (`/key-metrics?period=quarter`) remain gated (HTTP 402).
- **Backend Aggregator**: Updated `update_market_barometer.py` to extract `earnings_date` from FMP `/earnings` responses and preserve it within the `constituents_data` JSONB payload stored in `market_barometer_history`.
- **Frontend Audit View**: Added `earnings_date` to the constituent interface and rendered a new sortable `Earnings Date` column in `BarometerAuditPage.tsx` next to `Earnings Beat`.
- **Testing**: Added unit test coverage in `test_market_barometer.py` and `-barometer-audit.test.tsx`.

**See**: [[entities/market-barometer-audit]], [update_market_barometer.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/scripts/update_market_barometer.py), [BarometerAuditPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/home/pages/BarometerAuditPage.tsx)

## [2026-06-28] feature | UI Design System Select Primitive & Reasoning Model Filtering

Expanded design system primitives and added model filtering to Reasoning audit trail:
- **Design System Expansion**: Added reusable `Select` primitive to `packages/ui-design-system/src/primitives/Select.tsx` with full dark/light mode and zinc palette styling.
- **Reasoning Page Filtering**: Integrated model filter dropdown in `ReasoningPage.tsx` dynamically listing models from active traces. Enables concurrent category and model filtering.
- **Analytics & Testing**: Tracked model selection via PostHog (`reasoning_model_filtered`) and added unit test coverage in `ReasoningPage.test.tsx`.

**See**: [[entities/web-app]], [Select.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/packages/ui-design-system/src/primitives/Select.tsx), [ReasoningPage.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/reasoning/pages/ReasoningPage.tsx)

## [2026-06-27] refactor | Authenticated Profile Route & Header Navigation Refactoring


Replaced legacy mock `/posts` route with an authenticated `/profile` dashboard and updated navbar layout:
- **Route Cleanup**: Removed legacy JSONPlaceholder `/posts` route files (`posts.tsx`, `posts.index.tsx`, `posts.$postId.tsx`, and `lib/posts.ts`) and removed `/posts` from navigation items.
- **Protected Profile Route**: Added `/_authed/profile` displaying authenticated user email, session status, and security options using Design System primitives.
- **Navbar Layout**: Positioned authenticated user's email at the far left of the sticky navigation header, linking to `/profile`.
- **TDD Verification**: Authored tests in `-profile-navigation.test.tsx`. 100% of test suites and Biome linter checks pass.

**See**: [[entities/web-app]], [profile.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/routes/_authed/profile.tsx), [__root.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/routes/__root.tsx)

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

## [2026-06-22] bugfix | Switch MiniMax-M3 to Anthropic SDK and fix 4 ingestion regressions

A user-shared engine log (`2026-06-22 17:14-17:21`) surfaced five regressions in the daily ingestion pipeline. This change addresses four of them with root-cause fixes (the fifth — contrarian rejection propagation — was reclassified as non-bug and dropped).

- **MiniMax JSON parsing (root cause fix)**: The MiniMax-M3 analysis pipeline was wired to the OpenAI SDK pointed at MiniMax's OpenAI-compatible endpoint. The model returned raw JSON text prefixed with literal `JSON` (e.g. `'JSON{\n  "decisions": [...]'`), but Instructor's default `Mode.TOOLS` requires structured `tool_calls` and raised `"No tool calls or function call found in response (mode: TOOLS)"`. The retry loop's predicate only caught `validation error` / `list_type` substrings, so the error was re-raised and the batch's 3 decisions + 6 macro_events were silently dropped (total batch recorded 11/13 instead of 14/19). **Fix**: Switched `core/llm/clients.get_minimax_client` to `instructor.from_anthropic(AsyncAnthropic(base_url="https://api.minimax.io/anthropic", ...))` and routed the MiniMax tool loop through `handlers/anthropic.run_tool_loop` (M3 supports both formats per the MiniMax docs; the Anthropic format gives native `tool_use` blocks reusing the existing tool-loop handler). The OpenAI-format endpoint remains in use for auxiliary flows (`market_feeling`, `sector_predictor`) via `core/llm/minimax.MiniMaxClient`. The retry predicate was also widened to catch `no tool calls` / `function call found` substrings as defense-in-depth.
- **FMP quarterly metrics**: `audit_financial_valuation` was hardcoded to `period="annual", limit=5`, feeding annual-only data into the DCF for tickers with imminent earnings (e.g., MU reporting this week). **Fix**: changed to `period="quarter", limit=2` (FMP provider's `get_key_metrics` already falls back to annual on `402 Payment Required`). Added a degradation note that surfaces in the audit report when the FMP plan tier returns annual fallback.
- **Market barometer column drift**: `core/llm/tools.py:1434` queried `pe_ratio, price_to_fcf_ratio` from `market_barometer_history`. The DB column is `pfcf_ratio` (added by migration `20260621100000`). PostgREST returned 400 and `except Exception: pass` silently swallowed it, leaving the P/FCF premium line computed against a hardcoded 20.0 default. **Fix**: renamed the column to `pfcf_ratio` and replaced `pass` with a `logger.warning` so future schema drift surfaces in production.
- **Gemini AFC warning noise**: The `google-genai` SDK prints `[AFC] Tools at indices [0] are not compatible...` on every request because `automatic_function_calling.disable` defaults to False when not set. **Fix**: `core/llm/handlers/gemini.py` now always sets `automatic_function_calling = AutomaticFunctionCallingConfig(disable=True)` in the default `config_kwargs`. When `enable_google_search=True` and the new SDK supports `tool_config`, that branch still overrides (mutually exclusive in effect per the SDK) — the change only suppresses the warning in the common case where `enable_google_search=False`.
- **Verification rejection propagation (dropped)**: Originally proposed injecting verification rejections into the Contrarian Agent prompt so it doesn't re-attempt trades that other portfolios just had rejected. After re-reading the log, the contrarian's independent SPY trade was operating on its own portfolio state — the "bug" was the Contrarian Agent doing its job (deliberate independent reasoning). Propagating rejections across portfolios would couple independent risk silos and bias the contrarian away from its mandate. Dropped from scope.
- **TDD Verification**: Added `test_minimax_anthropic_sdk.py` (3 tests), `test_retry_predicate_widening.py` (2 tests), `test_valuation_audit_quarterly_first.py` (3 tests), and `test_gemini_tool_loop_always_disables_afc_when_search_enabled`. Updated `test_minimax_pipeline.test_minimax_tool_loop_called` to verify the Anthropic handler is invoked. Updated `test_call_counts.py` assertions (OpenAI 3 → Anthropic 2) to reflect MiniMax-M3's new SDK routing. Full engine test suite (780 tests) passes with `ruff check` clean.

**See**: [[concepts/minimax-portfolio]], [[concepts/agents]], [[concepts/fundamental-analysis]], [[concepts/model-anomalies]], [[entities/engine]], [core/llm/clients.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/clients.py), [core/llm/analysis.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/analysis.py), [core/llm/tools.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/tools.py), [core/llm/handlers/gemini.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/handlers/gemini.py), [tests/test_minimax_anthropic_sdk.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_minimax_anthropic_sdk.py), [tests/test_retry_predicate_widening.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_retry_predicate_widening.py), [tests/test_valuation_audit_quarterly_first.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_valuation_audit_quarterly_first.py), [tests/test_call_counts.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_call_counts.py)

## [2026-06-23] feature | Infinite caching for static and archival pages

Configured infinite staleTime cache settings for static/archival queries across concepts, reasoning, and memories features:
- **Concepts**: Configured `staleTime: Number.POSITIVE_INFINITY` for `conceptsQueries.list` and `memories`.
- **Reasoning**: Configured `staleTime: Number.POSITIVE_INFINITY` for `reasoningQueries.detail` (past decision traces).
- **Memories**: Configured `staleTime: Number.POSITIVE_INFINITY` for `memoriesQueries.detail`, `sources`, `resolutionChild`, and `causeAndEffect` (immutable event graph items).
- **Vertical TDD Unit Tests**: Added unit test files in `src/features/concepts/queries/options.test.ts`, `src/features/reasoning/queries/options.test.ts`, and `src/features/memories/queries/options.test.ts` to assert correct staleTime configuration.

**See**: [concepts/options.ts](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/concepts/queries/options.ts), [reasoning/options.ts](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/reasoning/queries/options.ts), [memories/options.ts](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/memories/queries/options.ts)

## [2026-06-23] refactor | MiniMax provider switches to Anthropic SDK handler for tool calling

MiniMax analysis now uses the Anthropic handler (`anthropic.run_tool_loop`) instead of the OpenAI handler. This aligns with the simplified MiniMax pipeline: no web search, `max_tokens=32000`, and system message handling via Anthropic conventions. The change affects both initial analysis and retry loops. Additionally, the batch analysis orchestrator now logs gather exceptions with `exc_info=res` to include the actual traceback, fixing a `NoneType: None` issue.

## [2026-06-23] bugfix | Fix test_orchestrator_logs_gather_exceptions_with_exc_info CI failure

The test `test_orchestrator_logs_gather_exceptions_with_exc_info` was failing in CI/CD environments with `openai.OpenAIError: Missing credentials`.

- **Root cause**: The test calls `analyze_chunks`, which executes the `summarize_newsletters` pre-filtering step. This step initializes the DeepSeek LLM client, failing when credentials are not present.
- **Fix**: Added a patch for `analysis.pre_filter.summarize_newsletters` returning `AsyncMock(return_value={})` within the test's mock context manager.
- **Verification**: Verified that the test and entire suite pass locally without any environment variables.

**See**: [tests/test_batch_analysis.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_batch_analysis.py)

## [2026-06-24] ui | Today page — AIFeelingCard component and empty-state placeholders for AgentInsights, NewsletterFeed

Added the `AIFeelingCard` component to the Today dashboard, replacing the previous `TradeActivity` slot in the 3-column grid. The card renders market sentiment (label, emoji, direction badge, confidence bar, why-explanation, primary concern, buy/sell split, timestamp, model name) from existing `marketFeeling` and `trades` data. `TradeActivity` moved to a full-width row below the grid.

Also fixed a layout bug where `AgentInsights` and `NewsletterFeed` silently returned `null` when no data was available, causing gaps in the 3-column grid. Both now render their section heading + a dashed-border empty-state card when data is absent.

Tests added: `AIFeelingCard.test.tsx` (15 tests), `NewsletterFeed.test.tsx` (10 tests), plus 3 new empty-state tests in `AgentInsights.test.tsx`. Total test count: 310 (up from 282).

## [2026-06-24] bugfix | Resolve MiniMax double-buffer bug and redundant market status checks

Resolved two issues identified during the logs audit:
- **MiniMax Double-Buffer**: Modified [main.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/main.py#L319-L324) to set `alpaca_limit = exec_price` directly, resolving a bug where the 0.5% buffer was applied twice on Alpaca mirror orders.
- **Redundant Market Status Checks**: Increased the market status cache `"ttl_seconds"` from `300` to `1800` (30 minutes) in [market_data.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/execution/market_data.py) to prevent redundant API queries to FMP during slow parallel analysis runs.
- **TDD Verification**: Updated `test_buy_alpaca_limit_uses_same_buffer` in [test_minimax_pipeline.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_minimax_pipeline.py) to assert correct single-buffer limit price.

**See**: [[concepts/minimax-portfolio]], [[entities/pipeline]], [main.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/main.py), [market_data.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/execution/market_data.py), [test_minimax_pipeline.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_minimax_pipeline.py)

## [2026-06-24] fix | Restore daily briefings visibility by adding newsletter_snapshots RLS policy and SELECT grant

Resolved the issue where the Today page's Daily Intelligence Briefing section was stuck showing "No briefings ingested yet today" despite successful ingestion:
- **Database Layer**: Deployed migration `20260624000000_add_newsletter_snapshots_read_policy.sql` adding RLS select policies and explicit `GRANT SELECT` statements on the `newsletter_snapshots` table for the `anon` and `authenticated` roles.
- **Root Cause**: The web app calls `fetchTodayData` under the anonymous role client (`SUPABASE_ANON_KEY`). Since RLS was enabled on `newsletter_snapshots` but SELECT grants/policies were omitted to prevent arbitrary selects of raw emails, anonymous queries returned 0 results. The Today page relies on direct queries for today's newsletters. Adding SELECT policies/grants allows the web app to query the table.
- **Verification**: Verified using a custom scratch script executing the Today page query pattern via the `anon` client credentials. Results returned went from 0 to 4.

**See**: [[concepts/supabase-grant-convention]], [fetch-today-data.ts](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/today/api/fetch-today-data.ts), [20260624000000_add_newsletter_snapshots_read_policy.sql](file:///Users/cesarvega/Documents/p-code/llm-market-bench/supabase/migrations/20260624000000_add_newsletter_snapshots_read_policy.sql)

## [2026-06-24] ui | Daily Intelligence Briefing — Clean email addresses and enable badge wrapping

Shortened and improved wrapping/responsiveness of the sender badges in the Daily Intelligence Briefing cards:
- **Email stripping**: Added `formatSender` utility in [NewsletterFeed.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/today/components/NewsletterFeed.tsx) to strip bracketed email addresses (e.g. `<squad@thedailyupside.com>`) from the sender string while safely falling back to the original value if it is a pure email address.
- **Responsiveness & Wrapping**: Refactored the card header flex layout to include `gap-4`, added `min-w-0` to the badge wrapper container, and added `whitespace-normal break-words text-left` classes to the `Badge` primitive to ensure clean wrapping and prevent horizontal squishing or overflow.
- **Verification**: Created new test cases in [NewsletterFeed.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/today/components/NewsletterFeed.test.tsx) asserting the email cleaning behavior and the raw email fallback. Checked lint rules with `pnpm biome check` and verified the build using `pnpm run build`.

**See**: [NewsletterFeed.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/today/components/NewsletterFeed.tsx), [NewsletterFeed.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/today/components/NewsletterFeed.test.tsx)

## [2026-06-24] ui | Daily Intelligence Briefing — Center sender name in badge

Centered the email sender name in the header badge on the Daily Intelligence Briefing cards:
- **Styling Update**: Replaced `text-left` with `text-center justify-center` in the [NewsletterFeed.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/today/components/NewsletterFeed.tsx) sender `Badge` element to center its wrapped name string.
- **Verification**: Added an assertion in [NewsletterFeed.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/today/components/NewsletterFeed.test.tsx) to verify the presence of `text-center` and `justify-center` classes.

**See**: [NewsletterFeed.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/today/components/NewsletterFeed.tsx), [NewsletterFeed.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/today/components/NewsletterFeed.test.tsx)

## [2026-06-24] enhancement | Add MiniMax to agent-info display config

Added `MODELS.MINIMAX` to the `agentConfig` mapping in `apps/web/src/features/today/lib/agent-info.ts`, along with a test case for exact and lowercase matching. This gives MiniMax a proper display name, color (`text-pink-500 / bg-pink-500`), and emoji (🟡) in the Today dashboard UI, completing the set of active trading models recognized by the frontend agent info utility.

## [2026-06-26] fix | Dust cleanup metrics recalculation and cleaned position counting bugs

Resolved two bugs in the Pre-Analysis Dust Cleanup phase of the daily pipeline:
- **Metrics Recalculation**: Updated `_check_and_sell_dust_positions` in `portfolio.py` to recalculate portfolio metrics using correct `current_prices` instead of mapping remaining tickers to their average cost basis. This keeps the total equity and other Reg T margin metrics accurate after dust positions are automatically closed.
- **Cleaned Position Counting**: Updated `_stage_dust_cleanup` in `main.py` to track position keys before the dust cleanup and compare them to position keys after the cleanup. This fixes the dead code that caused the reported cleaned count to always be 0.
- **TDD Verification**: Added unit tests `test_dust_cleanup_recalculates_metrics_with_current_prices` in `test_dust_position_cleanup.py` and `test_stage_dust_cleanup_reports_correct_cleaned_count` in `test_sell_threshold_tool.py` to verify both fixes. All tests pass successfully.

## [2026-06-27] feature | Continuous Crash Recovery Generation

Updated `runner.py` so that when a prompt variant crashes (< 2 trades), the runner reverts to the baseline and immediately proceeds to generate a new candidate prompt off the baseline for the upcoming week, instead of skipping auto-research entirely. Added `TestCrashRecoveryContinuesGeneration` test coverage. Updated `wiki/entities/autoresearch.md` with the new behavior.

## [2026-07-02] fix | Resolve ticker validation, MiniMax JSON format, Gemini retry context, and DiscoveryAgent list parsing issues

Resolved multiple pipeline anomalies identified in the logs audit:
- **Ticker Validation**: Added `_is_valid_ticker` guardrail to the central tool dispatcher `execute_tool` in [base.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/handlers/base.py) to validate stock ticker parameters (1-5 alphanumeric characters with optional single period or hyphen), preventing model ticker hallucinations (like `USSHORT` or `SOFTWARE`) from hitting external APIs.
- **MiniMax JSON Format**: Restructured MiniMax/Anthropic message flattening in [analysis.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/analysis.py) to use plain natural language annotations for tool calls and result histories instead of structured pseudo-tags for MiniMax, eliminating Pydantic JSON validation parsing crashes.
- **Gemini Correction Context**: Updated [analysis.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/analysis.py) retry logic to append the assistant's previous decisions JSON response before the user's correction prompt, restoring complete context so the model successfully performs missing tool calls and keeps its original decisions on retry.
- **DiscoveryAgent JSON List Parsing**: Adjusted the regular expression in [discovery_agent.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/analysis/discovery_agent.py) to match JSON list blocks `[...]` in addition to dictionaries `{...}`, resolving discovery agent parsing failures for models that output pure lists.
- **TDD Verification**: Created `test_audit_fixes.py` with 5 new unit tests covering ticker validation rules, blocked invalid execute-tool calls, list JSON parsing in DiscoveryAgent, MiniMax natural language flattening, and retry context insertion. All tests pass successfully.

**See**: [base.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/handlers/base.py), [analysis.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/analysis.py), [discovery_agent.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/analysis/discovery_agent.py), [test_audit_fixes.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_audit_fixes.py)


