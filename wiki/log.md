## [2026-05-25] refactor | Unified Database Memory Types and Frontend Filters

Unified database `memory_type` discriminators, Python constants/models, API queries, and Frontend UI filter selectors into a consistent first-class schema. Overloaded `LESSON_LEARNED` records are promoted to `POST_MORTEM` and `ACADEMIC_PAPER` to eliminate complex JSONB metadata querying, maximize index efficiency, and establish a clean ubiquitous domain vocabulary.

- **Database (`supabase`)**: Added a SQL migration to update existing memories table records to use new categories.
- **Python Engine (`engine`)**: Updated academic paper seeding and post-analysis engine scripts to write first-class `ACADEMIC_PAPER` and `POST_MORTEM` memory types. Prevented relevance decay in new memory types.
- **Frontend App (`web`)**: Simplified API category filters to execute direct, highly indexed database column queries. Standardized UI components (filters, badges, insights) to use the new types.
- **Tests**: Refactored both Python engine (pytest) and TypeScript web (vitest) tests to verify the unified categories under strict TDD.

## [2026-05-25] fix | Removed empty Lessons filter pill from Memories page

Removed the redundant and permanently empty "Lessons" filter pill from the `/memories` page on the frontend. 

- **Frontend (`web`)**: Removed `{ id: 'lesson_learned', label: 'Lessons' }` from `FILTERS` in `MemoriesList.tsx`.
- **Tests**: Updated `MemoriesList.test.tsx` to assert exactly 5 active filter buttons and expect that the "Lessons" text is absent.
- **Documentation**: Updated [[concepts/memory-feedback]] to reflect the filter tab removal, explaining that post-mortems and academic principles fully cover all recorded lessons learned.

## [2026-05-25] documentation | Wiki codebase reference validation audit

Audited the dual-linter pipeline (`wiki_lint.py` and `wiki_lint_llm.py`) and identified that neither validates codebase references on disk.

- **New Concept**: Created [[concepts/code-reference-validation]] documenting the structural and LLM linter scopes and proposing a deterministic, path-only pre-commit validation strategy to avoid doc rot.
- **Cross-References**: Integrated the concept page into the index ([[index]]) and wiki linter entity page ([[entities/wiki-linter]]).

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

## [2026-05-25] fix | Resolve memories category filter SQL casting error with ->> operator

Fixed a PostgreSQL casting error (22P02) in the memories category filter by migrating from JSONB object extraction (`->`) to text extraction (`->>`) in Supabase queries. This resolves `invalid input syntax for type json` errors when filtering by `academic_paper`, `post_mortem`, or `lesson_learned` categories. Added comprehensive Vitest test suite for the fetchMemories function. Updated database entity documentation with JSONB querying conventions.

