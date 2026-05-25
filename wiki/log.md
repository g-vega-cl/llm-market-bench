## [2026-05-25] feature | Server-side memories filtering with PostgREST JSONB

Transitioned the `/memories` page from the legacy hybrid client-side filtering system to a high-performance, purely database-driven server-side architecture:
- **API Category Filtering**: Refactored `fetchMemories` in `fetch-memories.ts` to execute precise indexed database queries using PostgREST JSONB filtering on the Supabase backend.
- **Cognitive Complexity Helper**: Extracted query construction to `applyCategoryFilter` to keep functional complexity within standard Biome limits.
- **Query Caching & Router passing**: Integrated active categories into TanStack Query keys to trigger automatic server-side refetching during tab transitions. Updated TanStack Start's `createServerFn` validator to support parameter objects.
- **Filter Cleanup**: Removed the empty "Decisions" filter pill since decisions live on the dedicated Reasoning page.
- **TDD & Unit Verification**: Updated unit test suite in `MemoriesList.test.tsx` to align with the prop-driven server-side filter signature. All 166 unit tests passed successfully.
- **Documentation**: Updated `wiki/concepts/memory-feedback.md` to detail the server-side queries and classification mappings.

## [2026-05-25] feature | Memory filtering and dynamic categorization frontend fix

Implemented a dynamic frontend memory categorization system to resolve empty filters for Decisions and Post-Mortems, and added support for all memory types in the `/memories` page:
- **Dynamic Categorization**: Introduced `getMemoryCategory(memory)` function to classify database memories into specific semantic types (Events, Calendar Events, Decisions, Post-Mortems, Principles, Lessons) based on their `memory_type` and `metadata` schemas.
- **Enhanced Badge Styling**: Refactored `MemoryCard` to badge categorized memories with distinct, curated colors from the design system.
- **TDD Verification**: Implemented robust unit tests in `MemoriesList.test.tsx` verifying classification and filtering correctness on database memory shapes.
- **Documentation**: Updated `wiki/concepts/memory-feedback.md` to document the dynamic UI categorization architecture.

## [2026-05-24] refactor | Parameterized LLM client factories for isolated unit testing in CI/CD

Refactored the LLM client factories to follow clean Dependency Injection best practices, resolving a credentials dependency blocker in CI/CD unit testing environments:
- **Parameterized factories**: Updated `get_openai_client`, `get_anthropic_client`, `get_deepseek_client`, and `get_gemini_client` to support an optional `api_key: str | None = None` parameter, falling back dynamically to global `core.config` attributes if unset.
- **Isolated Testing**: Simplified `test_get_deepseek_client_mode` to pass dummy/mock credentials directly, eliminating global state manipulation (`monkeypatch` or env var overrides) and achieving 100% test isolation.
- **Documentation**: Updated `wiki/sources/engine-testing-source.md` to reflect the new dependency injection and client testing paradigms.

## [2026-05-22] feature | Advanced memory reinforcement, tiered decay, and sleep consolidation


Implemented a robust and advanced LLM memory management system to prevent context pollution and reasoning degradation:
- **Memory Reinforcement**: Semantically similar duplicate records now reset `relevance_score` to `1.0` and bump `created_at` timestamp rather than being silently ignored. The duplicate check window is extended to **168 hours (7 days)** to capture repeating signals across weekends.
- **Tiered Decay & Purging**: Custom decay rates applied to memories based on their type during weekly cleanup (`MARKET_EVENT` decays standardly by 50%, `GOVERNMENT_INCENTIVE` decays mildly by 25%, and `LESSON_LEARNED`/`UNCROWDED_TRADE` never decay). Added a step to hard-delete `SUPERSEDED` memories older than **180 days** to prevent pgvector size bloat.
- **Sleep Cycle Consolidation**: An offline weekly consolidation loop that clusters active memories using cosine similarity `>= 0.85`, synthesizes them using instructor-wrapped DeepSeek into canonical consolidated entries (`ACTIVE`, `UPDATE` relationship, parent-linked), and marks original entries as `SUPERSEDED`. Added a scale-safety cap of the **500 most recent active memories** for DFS clustering.
- **TDD & Verifications**: Implemented comprehensive unit tests (`test_memory_reinforce.py`, `test_tiered_decay.py`, and `test_memory_consolidation.py`) to verify the behaviors in TDD style. Ruff checks and formatting fully completed.

## [2026-05-22] refactor | Unify dark theme and enforce design system default primitives

Fixed badge legibility and design system compliance globally. Eliminated all light/dark mode distinctions and `dark:` conditional classes from `Badge` and `Button` primitives to standardize on a single, high-contrast premium theme. Refactored application pages (Today, Market Overview, and Auto-Research status lists) to consume standard component properties (`colorScheme` and `variant`) without custom utility overrides. Updated wiki entities accordingly.

## [2026-05-22] feature | Add South Korea's ETF (EWY) to correlation matrix

Added South Korea's ETF (EWY) to the correlation matrix engine's TICKER_UNIVERSE and the web dashboard's "Emerging Markets" categories. Updated ETF descriptions and correlation-matrix-source documentation.

## [2026-05-15] fix | Fix price backfill to use pre-injected price_map for consistency

Changed the `injected_market_price` backfill logic in `analyze.py` to first use the price from the `price_map` that was injected into the LLM's prompt. Previously, it always fetched a fresh price from the market, which could cause false drift detections when compared to the JIT execution price. Now it stamps the price the LLM actually saw, falling back to a fresh fetch only for tickers discovered via tool calls.

## [2026-05-15] infra | Node.js version bump to 24 and audit workflow consolidation

Updated the entire monorepo to require Node.js >= 24. Added `.nvmrc` with `24`, updated `netlify.toml`, all `package.json` files, and development documentation. The QMD wiki search tool now uses `nvm use 24` instead of `nvm use 22`. Also consolidated the weekly audit workflow: merged the cleanup job into the audit job and added automatic cleanup of `market_feeling` records older than 30 days.

## [2026-05-15] Update | Align with Karpathy's LLM-Wiki "Living Synthesis"

Updated `AGENTS.md` and `wiki/SCHEMA.md` to move away from the "Never delete" (strikethrough) policy. The wiki now favors **Refining Synthesis** by replacing or removing stale content to keep pages sharp and context-efficient. History is preserved via `log.md` and Git. Cleaned up `wiki/sources/web-design-system-source.md` as a first example.

## [2026-05-15] policy | Wiki maintenance rule change: strikethrough → refine synthesis

Updated `AGENTS.md` and `wiki/SCHEMA.md` to replace the "never delete" (strikethrough) policy with a "Refine Synthesis" approach. The wiki now favors replacing or removing stale content to keep pages sharp and context-efficient, relying on Git and `log.md` for history. Cleaned up `wiki/sources/web-design-system-source.md` as a first example of the new policy.

## [2026-05-15] feature | Database cleanup module

Extracted database cleanup logic from CI workflow into a dedicated `core/cleanup.py` module with a new `cleanup` command. The module provides `run_cleanup()` for periodic deletion of stale ingestion logs, resolved audits, and market feeling records. Added unit tests in `tests/test_cleanup.py`.
- 2026-05-15: Synchronized wiki with new AGENTS.md mandates by adding [[concepts/agent-workflow]].

## [2026-05-15] fix | Engine bug fixes and agent workflow update

- `market_data.py`: Added 24-hour staleness check to `_get_last_known_price` to prevent returning prices older than 24 hours.
- `fmp.py`: Added ticker symbol verification to prevent using data from a different ticker due to FMP list shifting.
- `reg_t_validation.py`: Fixed margin requirement calculation to use absolute stock value; added buying power sanity guardrail capped at 4x total equity to prevent inflation from negative positions.
- Added reproduction tests for both bugs.
- `AGENTS.md`: Reordered and clarified principles to enforce Search-First, Plan-First, and TDD-First sequence.
- Added [[concepts/agent-workflow]] wiki page documenting the new mandatory workflow.

## [2026-05-15] removal | IBKR integration and proxy application removed

Removed all IBKR-related components to reduce codebase noise, as FMP and YFinance are the primary providers.
- **Applications**: Deleted `apps/ibkr-proxy/`.
- **Engine**: Deleted `ibkr.py` and `proxy_ibkr.py` providers.
- **Factory**: Removed IBKR imports and factory logic from `factory.py`.
- **Infrastructure**: Removed IBKR environment variables from `config.py`, `.env.example`, and all GitHub Actions workflows (`ingest.yml`, `update-prices.yml`, `weekend-ingest.yml`).
- **Tests**: Deleted `test_ibkr_manual.py`, `test_ibkr_concurrency.py`, and `verify_refinement.py`.
- **Dependencies**: Removed `ib-async` from `requirements.txt`.
- **Documentation**: Updated `README.md` and sanitized references in `validation.py` and `test_etf_validation.py`.

## [2026-05-15] update | Agent workflow rules refined

Added Research & Strategy and TDD Requirement sub-bullets under Plan First in AGENTS.md: agents must stay in Default mode for research, wait for explicit 'Go ahead' before execution, and include a reproduction test in every plan.

Updated [[concepts/agent-workflow]] to reflect these changes.

## [2026-05-15] removal | IBKR integration and proxy application removed

Removed all IBKR-related components to reduce codebase noise, as FMP and YFinance are the primary providers.
- **Applications**: Deleted `apps/ibkr-proxy/`.
- **Engine**: Deleted `ibkr.py` and `proxy_ibkr.py` providers.
- **Factory**: Removed IBKR imports and factory logic from `factory.py`.
- **Infrastructure**: Removed IBKR environment variables from `config.py`, `.env.example`, and all GitHub Actions workflows (`ingest.yml`, `update-prices.yml`, `weekend-ingest.yml`).
- **Tests**: Deleted `test_ibkr_manual.py`, `test_ibkr_concurrency.py`, and `verify_refinement.py`.
- **Dependencies**: Removed `ib-async` from `requirements.txt`.
- **Documentation**: Updated `README.md` and sanitized comments in `validation.py` and `test_etf_validation.py`.

## [2026-05-15] note | yfinance reliability concern flagged

Added a ROADMAP item questioning yfinance as a backup data source due to reliability issues, with a note to at least log its usage thoroughly.

## [2026-05-16] fix | Wiki Lint pipeline stabilization and documentation

Resolved multiple failures in the LLM-powered wiki linting pipeline, ranging from CI/CD permission issues to LLM parsing errors.

- **Robust JSON Extraction**: Replaced fragile string stripping with a robust regex + `JSONDecoder.raw_decode` strategy in `wiki_lint_llm.py`. This correctly handles models that output duplicate JSON objects or conversational prefaces.
- **Model Upgrade**: Upgraded the default model to `deepseek/deepseek-v4-pro` in both `wiki_lint_llm.py` and `auto_wiki.py` for increased reasoning power.
- **Context & Truncation Guard**: Implemented a strict **75k character limit** on wiki content collection with explicit `logger.warning` on truncation. This prevents context window saturation and "Unterminated string" errors from truncated LLM responses.
- **CI/CD Stabilization**: Fixed a `ModuleNotFoundError` by setting `PYTHONPATH=.` in `.github/workflows/wiki-lint.yml`. Explicitly granted `contents: read` and `issues: write` permissions and added a check-then-create pattern for the `wiki-lint` label to prevent workflow failures.
- **Input/Output Management**: Tuned `max_tokens` to 4096 to prevent truncation and "Unterminated string" errors during high-volume linting. Excluded `log.md` from context to avoid hallucinations about missing pages.
- **Structural Link Resolution**: Confirmed that the structural linter (`wiki_lint.py`) treats all `[[...]]` text as paths. Documentation now uses escaped or modified examples to avoid false-positive broken link reports.
- **TDD & Regression Fixes**: Restored test suite stability in `test_wiki_lint_llm.py` by ensuring error message assertions match the latest implementation. Added a specific test for truncated JSON handling.
- **Documentation**: Created [[entities/wiki-linter]] to document the dual-linter architecture and updated [[index]] for discoverability.

## [2026-05-19] design-system | Enhanced design system with SubHeading and Table primitives

### Context
While the design system was adopted, several pages still used raw HTML for subsections and data tables, leading to visibility issues in dark mode and inconsistent styling. The `/portfolios` page was specifically reported to have invisible text in dark mode due to hardcoded `text-zinc-900` without dark mode alternatives.

### Changes
- **New Primitives**:
    - `SubHeading`: Standardized component for secondary titles with optional divider and right-side elements.
    - `Table` Suite: Composable `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, and `TableCell` components with built-in dark mode support and hover states.
- **Migrations**:
    - `PortfoliosPage.tsx`: Replaced raw retired agent headers with `SubHeading`; fixed card title dark mode visibility.
    - `AuditsPage.tsx`: Migrated all section titles to `SubHeading`.
    - `PositionsTable.tsx` & `TradesTable.tsx`: Fully migrated to the new `Table` primitive.
    - `UncorrelatedPairs.tsx`: Migrated market overview table to use design system components.
- **Documentation**: Updated `packages/ui-design-system/README.md` and `wiki/entities/web-app.md` with the new components.

### Before / After
- **Before**: Invisible text in dark mode on portfolio cards; inconsistent table padding and borders; raw `h2` elements with hardcoded styles.
- **After**: Perfect dark mode contrast across all portfolios and audit views; unified table styling; semantic usage of `SubHeading`.

### Verification
- `biome check` passed.
- `tsc --noEmit` passed for `apps/web`.
- `PositionsTable.test.tsx` and `TradesTable.test.tsx` both passed (9/9 tests).

## [2026-05-18] fix | Resolved entities/gemini wiki lint errors

Fixed `[index-gap]` and `[orphan]` errors for `entities/gemini.md` by:
- Adding `[[entities/gemini]]` to `wiki/index.md`.
- Linking to `[[entities/gemini]]` from `[[concepts/agent-workflow]]`.

These issues were leftovers from the `AGENTS.md` → `GEMINI.md` rename session.

## [2026-05-19] design-system | Added SubHeading and Table primitives to the design system

Added new composable design system components:

- **SubHeading pattern** — Standardized secondary heading with optional `withDivider`, `uppercase`, and `rightElement` props for consistent section headers across pages.
- **Table primitive suite** — Composable `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, and `TableCell` components with built-in dark mode, alignment support, hover states, and container styling.

All three data tables and two section headers in the web app were migrated to use these new components: `PositionsTable`, `TradesTable`, `UncorrelatedPairs`, `AuditsPage`, and `PortfoliosPage`. Fixes dark mode visibility issues on portfolio cards.

## [2026-05-19] refactor | Badge primitive expansion and design-system-wide standardization

Expanded the **Badge** primitive with new `xs` size, `dot` variant (colored indicator dot + text), and consistent `text-zinc-950` contrast on solid variants across all color schemes. Replaced dozens of raw inline badge styles across the web app (MemoryCard, TradesTable, HumanFriendlyPrompt, FutureCatalysts, NewsletterFeed, TradeActivity) with the updated Badge component, standardizing on design tokens. Also updated the **Button** primitive's solid variant text color to `text-zinc-950` for matching contrast. Added a TODO roadmap item for portfolio badges with auto-research status.

## [2026-05-19] feature | Auto-Research Arena web page

The feature `apps/web/src/features/autoresearch` has been implemented, adding a dedicated page for the Auto-Research system. This includes:

- **New route**: `/autoresearch` with a server-side loader for fetching experiments.
- **API layer**: `fetchExperiments()` queries the `prompt_experiments` table from Supabase.
- **React components**: `AutoresearchPage`, `ExperimentDetails`, `ExperimentList`, and `ScoreCalculation` to visualize experiment history, metrics, research logic, and prompt content.
- **Data types**: Added `PromptExperiment` type to the shared `@llm-market-bench/database` package, mapping the new `prompt_experiments` table.
- **Navigation**: Link added to the root layout navigation bar.

The Auto-Research Arena allows users to explore past prompt experiments, view the risk-adjusted scoring formula, and see the meta-researcher's rationale for each prompt iteration.

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
