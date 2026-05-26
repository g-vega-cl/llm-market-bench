## [2026-05-26] fix | Fix Gemini GenerateContentConfig schema validation & DeepSeek API gateway deserialization errors

Resolved pipeline execution bugs affecting the daily ingestion and consensus stages:
- **Gemini Handler**: Correctly nested the `include_server_side_tool_invocations` flag inside a nested `types.ToolConfig` schema rather than passing it directly to `GenerateContentConfig` constructor (which violated the Pydantic constraints of the Google GenAI SDK and triggered fallbacks). Added a unit test validating full GenerateContentConfig parsing under the actual SDK schema.
- **DeepSeek Handler**: Implemented tool call and tool response message flattening inside `prepare_messages_for_instructor()` to convert raw `role: "tool"` and assistant `tool_calls` into standard user/assistant plain-text messages during the final Instructor extraction. This avoids the DeepSeek API Gateway `missing field tool_call_id` deserialization error in Mode.MD_JSON.
- **Wiki**: Updated `wiki/concepts/model-anomalies.md` with accurate root-resolution descriptions of both behaviors.

## [2026-05-19] feature | Auto-Research Arena Web UI & System-Heavy Prompt Architecture

Introduced the **Auto-Research Arena** web UI at `/autoresearch`, allowing exploration of prompt experiment history with scoring methodology, experiment details, and historical progression. Simultaneously refactored the interaction pattern into a **System-Heavy** architecture: all trading logic, risk rules, tool enforcement, and SOPs now reside in the System Prompt (mutated by the meta-researcher), while the User Prompt remains a static data skeleton. This increases the surface area for autonomous prompt evolution. Added bootstrap utility and database type for `prompt_experiments`. Updated auto-wiki with truncation safety and new default model.

## [2026-05-19] feature | System-Heavy Prompt Refactor & Auto-Research Arena Web UI

Implemented System-Heavy Prompt architecture: moved all trading logic, calendar strategies, SMA rules, and output format specifications into the System Prompt, leaving a minimal data-only User Prompt. Added bootstrap utility to seed the new baseline. Created Auto-Research Arena web pages with experiment list, detail view, and scoring methodology display. Also improved auto-wiki prompt parsing with regex-based JSON extraction and truncation handling, and updated default Ollama model to qwen3.5:latest.

## [2026-05-19] feature | System-Heavy Prompt Refactor & Auto-Research Arena Web UI

Implemented System-Heavy Prompt architecture: moved all trading logic, calendar strategies, SMA rules, and output format specifications into the System Prompt, leaving a minimal data-only User Prompt. Added bootstrap utility to seed the new baseline. Created Auto-Research Arena web pages with experiment list, detail view, and scoring methodology display. Also improved auto-wiki prompt parsing with regex-based JSON extraction and truncation handling, and updated default Ollama model to qwen3.5:latest.

## [2026-05-20] refactor | Complete scenario parsing consolidation with structured ParsedScenario interface

Replaced inline scenario-splitting logic in `MemoryCard.tsx` with the consolidated `parseScenarios()` utility. Introduced a structured `ParsedScenario` interface exposing `cleanHeader`, `percentage`, `outcome`, `tradingPlan`, and `fullText` fields. Added comprehensive unit tests covering structured parsing, header cleaning, and fallback behavior. Updated the web-app entity page with a new Scenario Analysis Parsing section documenting the consolidation. This completes the DRY migration started earlier today by unifying both `MemoryCard` and `FutureCatalysts` components onto a single, tested parser.

## [2026-05-20] fix | Add D3 Chart Defensive Sanitization for Malformed Data

Implemented defensive input cleaning and boundary controls in `PortfolioComparisonChart.tsx` to prevent rendering artifacts from invalid dates, NaN values, and duplicate time-series entries. Added `React.useMemo` filters to sanitize portfolio and benchmark data, deduplication by date key, and `.defined()` callbacks on the D3 line generator. Extended test coverage with edge case Vitest test for malformed data inputs.

## [2026-05-20] prompts | Pure Data-Injection User Prompt Refactor

Extended the System-Heavy Prompt Architecture to all 8 agent prompt pairs. Previously only `ANALYSIS_USER_PROMPT_TEMPLATE` was a pure data skeleton; the other 7 agents (`CONTRARIAN`, `VERIFIER`, `SYNTHESIS`, `MANAGER`, `RELATIONSHIP`, `CAUSE_AND_EFFECT`, `DE_ADVERTISEMENT`) still embedded personas, SOPs, and task instructions in their user prompts. Moved all static instruction content to their respective system prompts. User prompts now contain only section labels, `{placeholders}`, and a single closing directive. Autoresearch ratchet and DB baseline unaffected. TDD: 30 red-phase tests confirmed failing, all 40 tests green after implementation. Also updated `wiki/concepts/system-heavy-prompt.md` to reflect project-wide scope and document the prompt caching motivation (Anthropic/DeepSeek cache from the top down, so static system prompts are cached after the first request).

## [2026-05-20] refactor | System-Heavy Prompt Architecture — Full Agent Rollout

Extended the System-Heavy Prompt Architecture to all 8 agent prompt pairs in `apps/engine/core/llm/prompts.py`. Previously only `ANALYSIS_USER_PROMPT_TEMPLATE` was a pure data skeleton; the other 7 agents (`CONTRARIAN`, `VERIFIER`, `SYNTHESIS`, `MANAGER`, `RELATIONSHIP`, `CAUSE_AND_EFFECT`, `DE_ADVERTISEMENT`) still embedded personas, SOPs, and task instructions in their user prompts. Moved all static instruction content to their respective system prompts. User prompts now contain only section labels, `{placeholders}`, and a single closing directive. Autoresearch ratchet and DB baseline unaffected. TDD: 30 red-phase tests confirmed failing, all 40 tests green after implementation. Updated `wiki/concepts/system-heavy-prompt.md` to reflect project-wide scope and document the prompt caching motivation (Anthropic/DeepSeek cache from the top down, so static system prompts are cached after the first request).

## [2026-05-20] refactor | Standardized yfinance Logging with Fallback Warnings and Traceback Hardening

Refactored `apps/engine/execution/providers/yfinance.py` to align with the [[concepts/observability-standard]]:
- Replaced `core.config.logger` with a dedicated module-level logger (`engine.execution.providers.yfinance`).
- Added explicit warning logs for price fallback chains (`currentPrice` → `regularMarketPrice` → `previousClose`) and market cap fallback chains (`marketCap` → `totalAssets` → `netAssets`).
- Hardened exception handling in `get_ticker_data` and `get_history` to use `logger.exception()` for full traceback capture.
- Added comprehensive TDD tests in `test_yfinance_provider.py` verifying logger naming, fallback warning triggers, and traceback preservation under failure states.

## [2026-05-21] test | Supabase client missing-config test coverage

Added tests for `get_supabase_client()` and `get_async_supabase_client()` to verify they raise `ValueError` when Supabase configuration (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) is missing and the singleton client is not already cached. Covers a gap in error-handling coverage for the database client layer.

## [2026-05-21] feature | PostHog Stealthy Same-Origin Reverse Proxy

Implemented a stealthy reverse proxy for PostHog to prevent ad blockers from blocking client-side analytics and error tracking. The PostHogProvider now routes all telemetry through the same-origin path `/p`. Local development uses Vite proxy rules in `vite.config.ts`, while production uses Netlify Edge CDN redirects in `netlify.toml` with `status=200` rewrites. Server-side tracking continues to call PostHog directly. Added a unit test verifying the `/p` api_host configuration.

## [2026-05-21] feature | Empirical Asset Pricing Papers Seeding

Added a dedicated seeding script (`seed_academic_papers.py`) and reproduction test to ingest the top 10 empirical asset pricing academic papers into the pgvector memory store. These papers are seeded as `LESSON_LEARNED` with maximum importance (10) to ensure they reliably bubble up in the Tier 2 RAG (Verifier Path) to ground agent reasoning in established financial science (e.g., Fama-French, momentum, behavioral anomalies).

## [2026-05-22] refactor | auto_wiki.py: extract apply_changes() and add page deletion enforcement

Extracted the inline write-changes block from `main()` into a testable `apply_changes()` function. Added `apply_page_deletions()` to physically delete wiki pages whose scope has been removed from the codebase, strip their `[[link]]` entries from `index.md`, and validate against path traversal. The LLM diff agent can now emit `deleted_pages` in its JSON output. Updated `wiki/SCHEMA.md` Maintenance Rule 5 to document the deletion policy and required log format. Covered by 7 new tests in `apps/engine/tests/test_wiki_schema.py`.

## [2026-05-22] refactor | Button and Badge Solid Text Contrast and Glass Hover Fix

Adjusted the styling configurations in the `@llm-market-bench/ui-design-system` package to resolve readability and contrast issues on solid primitives:
- **Solid Button and Badge Variants**: Changed text from `text-zinc-950` to `text-white` on dark/medium backgrounds (`accent`, `danger`, and `info` schemes, including `medium` severity). Kept `text-zinc-950` for naturally light backgrounds (`success`, `warning`, `high`).
- **Glass Hover Corrections**: Rectified copy-paste hover bugs in `Button.tsx` for `success`, `danger`, `info`, and `warning` variants to correctly use their respective dark background hover color tokens instead of the fallback `accent`.
- **TDD Regression Suite**: Created a unit test `ButtonAndBadgeReadability.test.tsx` in `apps/web` verifying exact styling and mapping across all color schemes.

## [2026-05-22] update | Remove saved correlation matrix task from ROADMAP

Removed the task "Make sure we save the historical correlation/returns table/matrix" from the project roadmap. No code changes, just deprioritization of a planned feature.

## [2026-05-22] feature | Add South Korea ETF (EWY) to correlation matrix

Added EWY (iShares MSCI South Korea ETF) to the correlation matrix TICKER_UNIVERSE in the engine, expanding the Emerging Markets category from 6 to 7 tickers. Updated the web dashboard's SectorPerformanceGrid and etf-descriptions to include EWY. Updated correlation-matrix-source wiki page to reflect the new 71-asset universe.

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

