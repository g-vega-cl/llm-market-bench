## [2026-07-14] fix | Fix pipeline timing to run earlier (9:35 AM EST/EDT)

Resolved the issue where the daily ingestion and consensus pipeline ran late (~12:00 EST):
- **Schedule Expansion**: Updated `.github/workflows/ingest.yml` to trigger at `14:35 UTC` (matching `9:35 AM EST` / `10:35 AM EDT`), alongside the existing `13:35 UTC` (`8:35 AM EST` / `9:35 AM EDT`), `15:35 UTC`, and `18:00 UTC` triggers.
- **FMP Status Overriding**: Refactored `is_market_open` in `apps/engine/execution/market_data.py` to add a weekday market-open buffer (9:30 AM - 9:50 AM ET). If the FMP API reports the market as CLOSED during this window (due to transient status cache lag right at open), the check gracefully overrides status to OPEN to prevent the run from aborting.
- **TDD Verification**: Ensured all 840 unit and integration tests (including GHA workflow schema assertions) pass successfully.

## [2026-07-14] feature | Detailed audit breakdown and portfolio constituents in DailyScoreDisplay

Implemented a highly detailed mathematical breakdown and portfolio constituent view in the daily calculations audit panel inside the Autoresearch ("autoreturn") dashboard:
- **Mathematical Transparency**: Added precise base math equations for the components (Excess Return, Portfolio Return, Do-Nothing Return, Opportunity Cost, Risk Penalty, and Final Score Assembly) to show exactly how daily scores are calculated from portfolios and benchmark returns.
- **Portfolio Constituents Breakdown**: Individual portfolios (e.g., Gemini 3.1 Flash Lite, DeepSeek V4 Pro) and their specific base and scaled actual or do-nothing returns are displayed inside the Day Inspection panel.
- **Async Actual Returns Loading**: Fetches the `portfolio_performance` histories for active portfolios dynamically from the database to compute the actual weekly returns.
- **TDD Integration Tests**: Created a robust test in `DailyScoreDisplay.test.tsx` mocking Supabase queries and verifying that the formulas, equations, and individual portfolio constituents render correctly.
- **Formatting and Linting**: Fully verified clean Biome checks and 100% passing tests (329 tests total).

**See**: [DailyScoreDisplay.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/autoresearch/components/DailyScoreDisplay.tsx), [DailyScoreDisplay.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/autoresearch/components/DailyScoreDisplay.test.tsx)

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

## [2026-07-07] enhancement | DiscoveryAgent supports client dependency injection

The DiscoveryAgent now accepts an optional `client` parameter in its constructor, enabling dependency injection for testing or alternative providers. This allows the agent to be instantiated without requiring actual API keys when a mock client is provided. A new test validates the injection behavior.

## [2026-07-07] fix | Gemini synthesis fix and ticker false-positive filter

- Changed `synthesize_event` to use `SynthesisResponse` directly (not a list) for Gemini responses, removing array handling.
- Fixed `close_client` to use `"gemini"` instead of `"openai"`.
- Added common political and macro acronyms to `_TICKER_FALSE_POSITIVES` to prevent false ticker extraction (TRUMP, BIDEN, HARRIS, USA, FED, FOMC, CPI, GDP, PCE, PMI, VIX, WACC, DCF).

## [2026-07-08] feature | Derive Forward P/E, CAPE, and Book-to-Market in key metrics tool

Enhanced `execute_key_metrics_tool` to dynamically calculate three new valuation metrics:
- **Book-to-Market Ratio** — computed as `1 / pbRatio` for each historical period entry
- **Forward P/E** — `price / next_fy_estimated_eps` using analyst estimates (requires quote + estimate data)
- **CAPE (Cyclically Adjusted P/E)** — `price / average_eps` over up to 10 annual periods (minimum 3 years; requires quote + historical EPS data)

A new "Current Valuation Metrics (Derived)" summary section is appended to the tool output. If quote or estimate data is unavailable, the section gracefully reports N/A. Tests added in `test_key_metrics_tool.py` verify formatting and mathematical correctness with defensive mock isolation.

**ROADMAP.md**: Marked this item as completed.

**See**: [[concepts/fundamental-analysis]], `apps/engine/core/llm/tools.py`

## [2026-07-10] fix | PCA index shifting and Government pipeline async crash

- **PCA utils**: Fixed index shifting bug when malformed vectors cause some concepts to be skipped during PCA coordinate updates. The mapping now uses valid concepts only, ensuring correct (id, pca_x, pca_y) alignment.
- **Government pipeline**: Fixed a TypeError when the Gemini client returns a synchronous response object but the pipeline awaited it. Added coroutine detection to handle both sync and async calls.
- **Gemini client**: Updated `get_gemini_client` to wrap the instructor client's `chat.completions.create` as an async function using `asyncio.to_thread`, enabling async operations without blocking.
- **Tests**: Added unit tests for both fixes in `test_pca_utils.py` and `test_government_pipeline.py`.

## [2026-07-10] fix | Verifier safeguards, JIT adjusted failsafe, and transient error retries

- **JIT Adjusted Failsafe**: Fixed a critical gap where status `ADJUSTED_ALLOCATION` with an empty or invalid `adjusted_quantity` would silently bypass adjustments and execute the full unadjusted quantity. The JIT engine now rejects the trade with `REJECTED_VERIFICATION` (failing safe).
- **Specialized Provider Mapping**: Fixed a potential model provider mismatch crash by introducing `AGENT_PROVIDER_MAPPING` to dynamically update the `provider` parameter alongside specialized agent model mappings.
- **HOLD Gate Case-Insensitivity**: Updated the verifier's early-exit check to `decision.signal.upper() == "HOLD"`, making the signal gate case-insensitive.
- **Transient API Retries**: Implemented up to 3 retries with exponential backoff inside `verify_trading_decision` for transient client and network errors (429 rate limits, connection timeouts, gateway issues) before defaulting to fail-safe rejection.
- **TDD Verification**: Created `test_verification_adjusted_failsafe.py` and updated `test_verification.py` to cover all new safeguards and retry mechanisms. All tests pass with 100% style compliance.

**See**: [[concepts/agents]], [[concepts/tool-enforcement]], `apps/engine/core/llm/verification.py`, `apps/engine/main.py`, `apps/engine/tests/test_verification_adjusted_failsafe.py`

## [2026-07-10] fix | Enforce agent-level model scoping for memory RAG

Enforced strict agent model-level scoping across all memory retrieval paths to eliminate cross-agent decision contamination:
- **Scoping Fix**: Modified `retrieve_context` and `retrieve_context_batch` in `apps/engine/memory/store.py` to require a `model_name` parameter. This parameter is propagated as `filter_model_name` to the Supabase `match_decisions` RPC call.
- **Agent Integration**: Updated the `search_past_memories` tool in `apps/engine/core/llm/tools.py` and the tool dispatcher in `apps/engine/core/llm/handlers/base.py` to pass the executing agent's `model_name` to the context retriever.
- **Contrarian Agent**: Updated `apps/engine/analysis/contrarian.py` to pass `model_name="contrarian_agent"`, scoping its RAG queries to its own historical decisions.
- **TDD Tests**: Added `TestRetrieveContextModelFilter` to `apps/engine/tests/test_store_sanitization.py` to assert correct parameter propagation. Updated all existing `retrieve_context` calls in `test_memory_rag.py`, `verify_step_15.py`, and `test_newsletter_menu_flow.py` to satisfy the updated signature.

**See**: [[concepts/rag-strategy]], [[concepts/memory-feedback]], [store.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/memory/store.py), [tools.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/tools.py), [base.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/handlers/base.py), [contrarian.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/analysis/contrarian.py)

## [2026-07-13] feature | Sequential Decoupling (Consensus-First Trading)

- **Decoupled Pydantic Schemas**: Split combined analysis output into `MacroEventsResponse` and `TradingDecisionsResponse` to give LLMs a single objective.
- **Prompt Templates Updated**: Refactored core prompts to separate macro event extraction (`MACRO_ANALYSIS_SYSTEM_PROMPT`/`MACRO_ANALYSIS_USER_PROMPT_TEMPLATE`) from trading decisions (`ANALYSIS_USER_PROMPT_TEMPLATE`), injecting synthesized consensus context into the trading pass.
- **Dynamic Prompt Builder**: Updated `PromptFactory.build_analysis_messages` to support dynamic reconstruction of database prompt strategies under the trading-only constraints with backward-compatible defaults.
- **Sequential Execution Passes**: Refactored `analyze_chunks` in `analyze.py` to run `analyze_macro_events` to extract and group consensus events first, and then run `analyze_trading_decisions` to generate final trading signals.
- **TDD Verification**: Created `test_decoupled_analysis.py` and updated legacy tests to assert correctness under the sequential decoupling architecture.

**See**: [[concepts/ingestion]], [[concepts/consensus]], [[entities/engine]], `apps/engine/core/models.py`, `apps/engine/core/llm/prompts.py`, `apps/engine/core/llm/prompt_factory.py`, `apps/engine/core/llm/analysis.py`, `apps/engine/analysis/analyze.py`, `apps/engine/tests/test_decoupled_analysis.py`

## [2026-07-13] wiki | Update How It Works page and compile pipeline to json

Restored and updated the 7-phase daily pipeline flow inside `wiki/entities/pipeline.md` to match the newly decoupled two-pass sequential architecture (macro consensus-first trading) and satisfy compilation regex constraints.
- **Wiki Refinement**: Updated [[entities/pipeline]] to define all 7 phases with their respective icons, badges, tags, descriptions, and list bullets mapping the real execution flow.
- **TDD Test Suite**: Added `test_actual_pipeline_markdown` in [test_compile_how_it_works.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_compile_how_it_works.py) to assert correct extraction of exactly 7 phases from the living wiki document.
- **JSON Recompilation**: Re-ran the compiler script `compile_how_it_works.py` to regenerate the dynamic `how-it-works.json` config loaded by the frontend.
- **Validation**: All tests pass successfully (72 test files, 328 tests) with clean Biome check formatting.

**See**: [[entities/pipeline]], [test_compile_how_it_works.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_compile_how_it_works.py), [how-it-works.json](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/config/how-it-works.json)


