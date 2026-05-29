## [2026-05-24] feature | DeepSeek MD_JSON mode, Ollama fallback resolution, and auto-wiki resource cleanup

- **DeepSeek client**: Switched from `instructor.Mode.JSON` to `instructor.Mode.MD_JSON` in `get_deepseek_client()` to eliminate the cognitive formatting clash that caused empty responses when thinking mode (reasoning_content) was active with strict JSON Mode. This is the root-resolution fix for the DeepSeek empty content anomaly.
- **Ollama fallback resolver**: `call_ollama()` now queries available local models and falls back gracefully if the requested model is not installed, with a preference order (`gemma4:31b` → `qwen3.6:35b` → `llama3.1:8b`) before resorting to the first available local model.
- **Ollama resource management**: Added `keep_alive: 10s` to Ollama API payloads so models unload from memory after rapid sequential queries. The `auto-wiki.sh` cleanup trap now runs `pkill ollama` to terminate the local server after pre-commit finishes.
- **Default Ollama model**: Changed from `qwen3.5:latest` to `gemma4:31b`.
- **Tests**: Added `test_prepare_messages_for_instructor`, `test_has_valid_content`, and `test_get_deepseek_client_mode` to `test_deepseek_handler.py`.
- **Wiki model-anomalies.md**: Updated DeepSeek mitigation description to document the MD_JSON root resolution alongside the existing fail-safe recovery logic.

## [2026-05-24] docs | Alpaca sync resilience, new agents concept page, and wiki enhancements

- Increased MAX_AGE_HOURS to 96 for weekend/cron failure resilience
- Added comprehensive test suite for Alpaca order sync
- Created new concept page for multi-agent system overview
- Expanded equal-weighted returns documentation with rationale and edge cases
- Updated pipeline and autoresearch pages with execution details
- Added cross-references between system-heavy prompt and agents pages

## [2026-05-24] refactor | Parameterized LLM client factories for isolated unit testing in CI/CD

Updated `apps/engine/core/llm/clients.py` to parameterize the four LLM client factories (`get_openai_client`, `get_anthropic_client`, `get_deepseek_client`, `get_gemini_client`) with an optional `api_key: str | None = None` parameter. This enables clean dependency injection for unit tests, eliminating the need for `monkeypatch` or environment variable manipulation in CI/CD. Tests updated: `test_deepseek_handler.py`, `test_models.py`, `test_memory_consolidation.py`.

## [2026-05-25] refactor | Auto-Research Metrics Alignment & Baseline Ratchet Refactor

Refactored the Auto-Research engine and web UI to properly align weekly trading metrics with the prompt variant that actually ran, ensuring a clean and logical progression in the history table:
- **Metrics Alignment**: Realigned `runner.py` to evaluate the completed trading week and update the metrics directly on the **previous active prompt** `P_active` (e.g. baseline `v20260519-221104`).
- **New Variant Initialization**: The brand-new mutated active prompt (e.g. `v20260524-221848`) is saved with empty/N/A metrics (`{}`) and advanced week start/end dates representing the **upcoming week** (prior week dates + 7 days).
- **UI Enhancements**: 
  - Updated `ScoreBreakdown.tsx` to render a premium pending performance state (a clean info card explaining weekly metrics are calculated at week close) when `metrics.score` is `undefined`/`null`, resolving the legacy zero-placeholder display.
  - Enhanced `ExperimentDetails.tsx` to render `N/A` for metric values when metrics are not present, avoiding `undefined%`.
  - Stylized `N/A` scores neutrally in `ExperimentList.tsx`.
- **Database Backfill**: Ran a migration backfilling `v20260519-221104` with its correct metrics (score `-2.8643`, `excess_return = -1.7712`, etc.) and resetting the new active variant to a clean pending state.
- **Tests**: Mocked database client methods in `test_autoresearch.py` and successfully verified 100% green test passing (43/43 Python pytest, 163/163 TS vitest).

## [2026-05-25] fix | Resolve memories category filter SQL casting error with ->> operator

Fixed a PostgreSQL casting error (22P02) in the memories category filter by migrating from JSONB object extraction (`->`) to text extraction (`->>`) in Supabase queries. This resolves `invalid input syntax for type json` errors when filtering by `academic_paper`, `post_mortem`, or `lesson_learned` categories. Added comprehensive Vitest test suite for the fetchMemories function. Updated database entity documentation with JSONB querying conventions.

## [2026-05-25] feature | Hybrid Local Cache + Delta-Syncing for AI Memories

Optimized the AI Memories feature using a highly efficient **Hybrid Local Cache + Delta-Syncing** pattern utilizing TanStack Query's `initialData`:
- **Instant Client Render (0ms)**: Reads directly from local storage cache (`localStorage` with a 500-item ceiling) during startup to render the dashboard instantly without spinners.
- **Declarative Delta Syncing**: Utilizes a single React Query cache key `['benchify', 'memories', 'list']` with `initialDataUpdatedAt: 1` to immediately trigger a background delta-sync on mount. Delta-syncing fetches only memories created *after* the latest cached memory, drastically reducing network overhead.
- **Pure Client-Side Filtering**: Executes 100% in-memory filtering based on `getMemoryCategory(m)`, resulting in **0ms latency** when clicking filter pills.
- **Client-Side Pagination**: Implemented local pagination on the cached list (incrementing display limits by 50 when clicking "Load More"), removing subsequent API calls.
- **No Side-Effects**: Replaced legacy `useEffect` dependencies with clean declarative React event handlers, satisfying Biome's strict formatting and unused import rules.
- **TDD Regression Tests**: Added `MemoriesPage.test.tsx` verifying visual shell loading, background delta-sync triggers, and tab filter transitions. All 171 frontend unit tests are green.

## [2026-05-25] feature | Hybrid Local Cache + Delta-Syncing for AI Memories

Implemented a hybrid caching strategy for the Memories dashboard using TanStack Query's `initialData` with localStorage persistence. New `fetchNewMemories` API fetches only records since the latest cached timestamp. New `cache.ts` lib provides `getCachedMemories`, `saveCachedMemories`, and `mergeAndDeduplicate` utilities. `MemoriesPage` refactored from infinite query to single-query delta-sync pattern with 100% client-side filtering and local pagination. Added comprehensive test suite (`MemoriesPage.test.tsx`) verifying instant render, background sync, and zero-network tab transitions. Removed completed roadmap item about database ID vs display filter disparity.

## [2026-05-25] decision | Revert Live QMD/Search-First CLI Hooks in Favor of Lean Pre-Commit/Manual Flows

Explored and implemented a workspace-level hook configuration (`.agents/hooks.json` mapping to a Python validation helper `scripts/qmd_hooks.py`) to enforce the **Search First (QMD)** principle and perform real-time QMD index updates during active agent sessions. 

Upon testing, the decision was made to roll back these live CLI hooks:
- **Overhead & Noise**: The `PreToolUse` grep validation injected warning messages directly into the agent's stream, which was determined to be too invasive and noisy for day-to-day workflow.
- **Workflow Sufficiency**: The project's existing Husky Git hooks (`.husky/pre-commit` and `.husky/post-merge`) already handle QMD re-indexing automatically during commits and merges, and manual `qmd` searches perform perfectly fine without dynamic session-level checking.
- **Result**: Successfully removed `.agents/hooks.json`, `scripts/qmd_hooks.py`, and `tests/test_qmd_hooks.py` to keep the repository extremely lean and free of unnecessary runtime complexity.

## [2026-05-25] decision | Revert Live QMD/Search-First CLI Hooks in Favor of Lean Pre-Commit/Manual Flows

Explored and implemented a workspace-level hook configuration (`.agents/hooks.json` mapping to a Python validation helper `scripts/qmd_hooks.py`) to enforce the **Search First (QMD)** principle and perform real-time QMD index updates during active agent sessions. 

Upon testing, the decision was made to roll back these live CLI hooks:
- **Overhead & Noise**: The `PreToolUse` grep validation injected warning messages directly into the agent's stream, which was determined to be too invasive and noisy for day-to-day workflow.
- **Workflow Sufficiency**: The project's existing Husky Git hooks (`.husky/pre-commit` and `.husky/post-merge`) already handle QMD re-indexing automatically during commits and merges, and manual `qmd` searches perform perfectly fine without dynamic session-level checking.
- **Result**: Successfully removed `.agents/hooks.json`, `scripts/qmd_hooks.py`, and `tests/test_qmd_hooks.py` to keep the repository extremely lean and free of unnecessary runtime complexity.

## [2026-05-25] fix | Memories Page Cache Backfilling & Filtering Resolution

Resolved the issue where filtering by "Events" on the Memories page displayed a very small subset of events (e.g., only two) by implementing complete cache backfilling to its 500-item capacity.

- **Frontend App (`web`)**: Imported `MAX_CACHE_SIZE = 500` from `cache.ts`. Updated the cache query logic in `MemoriesPage.tsx` to conditionally execute a full `fetchMemories(undefined, 500)` query if the local browser cache contains fewer than 500 items, backfilling it to completion. Once the cache is fully populated, subsequent page loads dynamically run the optimized background delta-sync (`fetchNewMemories`).
- **Tests**: Added a TDD unit test in `MemoriesPage.test.tsx` asserting that `fetchMemories(undefined, 500)` is correctly called when the cache is small. Updated existing delta-sync tests to seed 500 mock memories, ensuring perfect coverage and correctness.
- **Documentation**: Updated [[concepts/memory-feedback]] to detail the backfilling versus delta-sync logic and thresholds.

## [2026-05-25] autoresearch | Added Volatility Calculation Breakdown to Experiment Details

### Context
The user requested visual clarity on how the portfolio volatility metric is calculated within prompt experiments on the Auto-Research page, ensuring complete alignment with the design system.

### Changes
- **New Component**: Created `VolatilityCalculation` to render a step-by-step mathematical explanation of daily return weighting, standard deviation calculation, and √252 annualization.
- **Integration**: Placed the calculation breakdown directly underneath the Score Breakdown within `ExperimentDetails`.
- **Validation**: Added comprehensive unit tests in `VolatilityCalculation.test.tsx` achieving 100% test coverage for all component states (active vs. finalized). Verified clean Biome compliance and successful production builds.

## [2026-05-25] concept | Self-healing cache validation for memories page

The hybrid cache + delta-sync architecture on `/memories` gained a self-healing validation layer. Before entering delta-sync mode, the client now calls `validateCacheState()` — a lightweight API that checks whether the newest cached memory ID still exists in the database and whether the DB timeline has rolled back. Any anomaly triggers a full 500-item backfill, making the page resilient to database resets, re-seeds, and historical imports with zero user intervention.

Extracted `syncMemoriesCache`, `performFullBackfill`, and `fetchDeltaOrBackfill` helpers from the `queryFn` to keep cognitive complexity within Biome's limits. Added 3 new TDD regression tests for the self-healing paths (valid cache, ID-missing reset, timeline-rollback reset). The [[concepts/memory-feedback]] page was updated inline with these changes.

## [2026-05-26] fix | Preserve Unflattened Messages for Anthropic/Claude Hard Tool Enforcement

Resolved the issue where Anthropic/Claude models (e.g. Claude Haiku 4.5) were consistently getting their BUY/SELL decisions rejected with `REJECTED_TOOL_USAGE`.

- **Engine Core Fix**: Preserved a deep copy of the message history (`unflattened_messages`) in `apps/engine/core/llm/analysis.py` before flattening nested content blocks for Instructor. We now pass this unflattened copy to `_scan_history_for_tools` so it can scan structured `tool_use`/`tool_result` content blocks instead of raw strings.
- **TDD Test**: Added a new unit test `test_analyze_with_provider_hard_enforcement_anthropic` to `apps/engine/tests/test_tool_enforcement.py`. This test mocks the tool loop to call the sell tool and verifies that before the fix, the hard enforcement checker fails and rejects the trade; after the fix, it successfully confirms and approves the trade.
- **Documentation**: Updated [[concepts/tool-enforcement]] and [[sources/tool-enforcement-source]] with the unflattened message preservation logic.

## [2026-05-26] feature | Enriched Diagnostic Logging for Hard Tool Enforcement Rejections

Added comprehensive diagnostic details on Hard Tool Enforcement rejections to prevent silent failure states and streamline automated root-cause audits.

- **Diagnostic Helper**: Implemented `_get_history_tool_calls_diagnostic(messages: list) -> list[str]` in `apps/engine/core/llm/analysis.py` to extract and serialize friendly tool call strings (e.g. `get_stock_quote({"ticker": "AAPL"})`) from Anthropic, OpenAI, or Gemini history structures.
- **Enriched Warnings**: Updated all four hard tool enforcement warning logs in `apps/engine/core/llm/analysis.py` to output total message counts and the list of actual tool calls detected.
- **TDD Test**: Added a unit test `test_analyze_with_provider_hard_enforcement_logs_diagnostics` to `apps/engine/tests/test_tool_enforcement.py` asserting that log warnings contain `Total messages in history:` and `Tools called:` details.
- **Documentation**: Updated [[concepts/observability-standard]] with the new enriched diagnostic context standard.

## [2026-05-26] refactor | Improved Hard Tool Enforcement diagnostics for Anthropic message preservation

The staged diff contains changes already partially documented in wet-commits (log entries, concept updates). However, the diff itself represents a **refinement** of the tool enforcement diagnostics system:

- **`_get_history_tool_calls_diagnostic()`** is a comprehensive new diagnostic helper that recursively extracts tool call names/arguments from any provider message format (dict, object, nested content arrays, tool_use parts, etc.) — significantly more robust than the prior scan.
- **Enriched all four hard enforcement warning log statements** with total message count and actual tool calls detected.
- **New scratch scripts** (`check_logs.py`, `inspect_analysis.py`, `inspect_prompt_details.py`, `inspect_rejections.py`) for debugging LLM decision logs and rejection patterns.
- **New TDD tests** proving Anthropic hard enforcement works with the unflattened message copy, and that diagnostic details appear in log warnings on failure.

The wiki pages touched in the diff (observability-standard, tool-enforcement, tool-enforcement-source) are up to date. No new entity or concept pages are needed — this is a refinement of an existing system.

## [2026-05-27] update | ROADMAP.md — removed "Add statistics" item

The "Add statistics" task was removed from ROADMAP.md. This roadmap entry described checking current price changes in big indexes to gauge market moves, passing index prices to the LLM from the beginning (part of the global macro tracker). The downstream tracking line below it ("Pass the price of many indexes...") remains, as do the macro tracking entities/index references in the wiki. No structural change to code or architecture.

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
- **TDD Tests**: Implemented a comprehensive Python pytest suite `test_compile_how_it_works.py` and Vitest UI route test suite `how-it-works.test.tsx` achieving 100% test success and zero linter/formatting issues on both systems.

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

