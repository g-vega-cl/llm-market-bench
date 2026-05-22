## [2026-05-22] feature | Historical Progression Explorer & Selector Clarity Refinements

Implemented the new **Historical Progression Explorer** tab / page and D3 progression chart on the Market Overview page:
- **Resilient Bidirectional Queries**: The Supabase data engine queries the chronological weekly records using a bidirectional `.or` filter (`ticker_a`/`ticker_b` match check), mapping and aligning the `returns_a_90d` and `returns_b_90d` values in-memory to perfectly match the user's selected ticker display order.
- **Interactive Cursor Metrics Status Board**: Plotted using a custom D3 line chart displaying Pearson/Spearman coefficients and 90D returns with vibrant HSL design system tokens. Instead of using high, obstructive floating HTML tooltips, active hover states are driven through a clean **Cursor Metrics Board** positioned directly above the chart, which falls back to the latest weekly data point upon pointer exit.
- **ETF Description Clarity**: Integrates descriptive ETF names (e.g. `QQQ — Invesco QQQ Trust (NASDAQ 100)`) next to bare tickers inside searchable select dropdown elements for increased readability.
- **Verification**: Verified using Biome check, Vite build, and 156/156 green Vitest test suites. Added dedicated TDD tests verifying the bidirectional logic, order independence, and selector rendering.

## [2026-05-22] fix | Resolve Gemini 3 Multi-Tool 400 API Error & Enable Tool Context Circulation

Resolved the `400 INVALID_ARGUMENT` error when running Gemini 3 models with both custom function calling and Google Search grounding tools:
- **API Circulation**: Enabled `include_server_side_tool_invocations = True` in the `GenerateContentConfig` constructor (SDK-version-guarded to preserve backward compatibility).
- **ID Echoing**: Ensured the unique function call `id` assigned by Gemini 3 is preserved and echoed back within the `FunctionResponse` part of multi-turn user messages. This prevents agent recommendations from getting rejected by the platform's `HARD ENFORCEMENT` guardrail when web search is enabled.
- **Verification**: Added TDD unit tests (`test_gemini_tool_loop_sets_include_server_side_tool_invocations`, `test_gemini_tool_loop_afc_fallback_when_sdk_lacks_flag`, and `test_gemini_tool_loop_echoes_function_call_id`) and verified the entire `test_gemini_tools.py` suite passes successfully.
- **Documentation**: Updated [[concepts/model-anomalies]] and [[sources/web-search-source]] to reflect the resolution and the new multi-tool configuration capabilities of the engine.

## [2026-05-22] doc | Remediate "Thin" Wiki Pages & Add Model Anomalies & Cleanup Schedule

Enhanced the concepts page [[concepts/model-anomalies]] and database maintenance page [[entities/cleanup]] to resolve structural knowledge gaps flagged in the project's documentation audit. Aligned the descriptions directly with the codebase and recent ingestion logs:
- **Model Anomalies**: Documented the DeepSeek empty content anomaly (thinking mode populated `reasoning_content` while returning empty main `content`) and its mitigation via `prepare_messages_for_instructor()` and JSON recovery prompts. Also documented the Gemini-3.1-flash-lite built-in search tool calling conflict (API error 400 with function calling) and the corresponding hard enforcement safety guardrail rejections (e.g., BUY recommended without executing buy quantity calculations).
- **Database Cleanup**: Specified the precise schedule (runs automatically every Friday at 16:00 EST / 21:00 UTC as part of the `audit.yml` GHA workflow, immediately following the audit execution) and the exact PostgreSQL interval retention policies for `ingestion_logs` (>48 hours), resolved/ignored `system_audits` (>30 days), and `market_feeling` (>30 days).

Verified that the wiki is clean and passes all structural checks via the wiki linter `wiki_lint.py`.

## [2026-05-22] feature | Include CPER in Commodities Sector Analysis

Added `'CPER'` (United States Copper Index Fund) to the Commodities sector performance grid on the market overview dashboard, allowing users to view trailing 90-day copper performance. The ETF's descriptions and metadata are fully integrated via `etf-descriptions.ts`. Added a robust frontend unit test in `MarketOverviewPage.test.tsx` (TDD-first) to prevent regressions, formatted and verified the changes against the Biome linter, and confirmed that the full test suite passes.

## [2026-05-21] feature | Wiki Page Deletion on Scope Removal

Added explicit page-deletion enforcement to the wiki system. When a subsystem, entity, or concept is fully removed from the codebase, its wiki page must now be deleted (not struck through). Two layers of enforcement:

1. **`wiki/SCHEMA.md`** — new Maintenance Rule 5 documents the policy, required log-entry format (`## [YYYY-MM-DD] delete | <path> — scope removed: <reason>`), and the expectation that `index.md` entries are cleaned up.
2. **`apps/engine/auto_wiki.py`** — the LLM diff agent can now emit `deleted_pages` in its JSON output. The new `apply_page_deletions()` function physically deletes the files, strips their `[[link]]` lines from `index.md`, and validates against path traversal. The inline write-changes block was extracted into a testable `apply_changes()` function.

Covered by 7 new tests in `apps/engine/tests/test_wiki_schema.py`.

## [2026-05-21] feature | Empirical Asset Pricing Papers Seeding

Added a dedicated seeding script (`seed_academic_papers.py`) and reproduction test to ingest the top 10 empirical asset pricing academic papers into the pgvector memory store. These papers are seeded as `LESSON_LEARNED` with maximum importance (10) to ensure they reliably bubble up in the Tier 2 RAG (Verifier Path) to ground agent reasoning in established financial science (e.g., Fama-French, momentum, behavioral anomalies).

## [2026-05-21] doc | Align Score Calculation Page and Wiki with Backend Formula

Updated the `/autoresearch` web page's score calculation component ([ScoreCalculation.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/autoresearch/components/ScoreCalculation.tsx)) and its test ([ScoreCalculation.test.tsx](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/features/autoresearch/components/ScoreCalculation.test.tsx)) to display the actual risk-adjusted formula which includes the Opportunity Cost penalty and the Treasury Bond yield hurdle. Additionally, aligned the project wiki by updating outdated formulas on [[entities/autoresearch]] and [[entities/autoresearch-arena]].

## [2026-05-21] audit | TanStack Query Codebase Audit & Centralized Factory Deletion

Audited the project's use of TanStack Query across the `apps/web` frontend. Identified two parallel query options factory implementations: the active, vertical feature-specific factories in `features/*/queries/` and the duplicate centralized factory in `src/lib/queries.ts`. Deleted the dead centralized files `apps/web/src/lib/queries.ts` and `apps/web/src/lib/query-keys.ts` to preserve a clean vertical codebase structure. Documented type safety conventions, generic `CursorPage` constraints for infinite scroll queries, and SSR-safe `QueryClient` initialization inside a new wiki page [[concepts/tanstack-query]].

## [2026-05-21] fix | PostHog Stealthy Same-Origin Reverse Proxy Implementation

Configured a secure same-origin reverse proxy for PostHog to bypass browser ad blockers on client-side tracking and telemetry. Client api_host in the `PostHogProvider` is now routed through `/p` on the same domain, with local development proxying managed in `vite.config.ts` and production Edge routing handled server-side in `netlify.toml` via `status = 200` rewrites. Server-side tracking client continues to connect directly to official endpoints since server-to-server traffic is immune to ad blockers. Added a failing TDD unit test in `-__root.test.tsx` verifying correct client configuration and verified all 122 frontend tests pass with clean formatting and no lint warnings under Biome.

## [2026-05-21] fix | Auto-Research Ratchet Baseline Schema Migration and Testing

Demoted the older prompt variant `v20260517-221731`'s score metric to `old_score` to prevent it from hijacking the ratchet baseline system and overwriting the new System-Heavy prompt architecture. Added unit tests in `test_autoresearch.py` verifying that `get_all_time_baseline()` correctly ignores prompt variants that do not contain a `"score"` key (handling both older composite metrics and demoted/archived schemas).

## [2026-05-15] removal | Government incentive tracking feature removed

Removed the `is_government_incentive` field from `MacroEvent` model, the `_validate_and_enrich_government_events()` function from analysis.py, and all related GOV-DETECT keyword matching and UNFLAGGED POLICY EVENT warnings. The model-level flag was unreliable and produced noise. The consensus `_is_vague_government_event()` helper remains for synthesis quality control. Also upgraded default model from `deepseek-v4-flash` to `deepseek-v4-pro` across engine, web, and wiki lint configurations.

## [2026-05-15] config | Update default model from deepseek-v4-pro to deepseek-v4-flash

Changed the default OpenRouter model in `auto_wiki.py` and `wiki_lint_llm.py` from `deepseek/deepseek-v4-pro` to `deepseek/deepseek-v4-flash`. This is a non-trivial configuration change affecting both the auto-wiki documentation generator and the LLM wiki lint runner.

## 2025-04-07 refactor | Eliminated `any` types across web app

Replaced all remaining `any` type annotations with proper TypeScript types across the web app codebase. This includes:
- Replacing `any` with `Record<string, unknown>`, `unknown`, and specific interfaces in components, pages, and API functions
- Adding explicit type definitions for `StratifyData`, `PriceUpdate`, `TradeItem`, `DecisionItem`, `ChainMemory`, `EventChainData`, `DiscoveredAsset`, `TodayData`, `CursorPage`, `SignupVariables`, `AuthResult`, `LoginVariables`, and `MockSupabaseChain`
- Updating `biome.json` to promote `noExplicitAny` from `warn` to `error` and removing all override exemptions for this rule
- Updating `packages/database/index.ts` to use `Record<string, unknown>` instead of `Record<string, any>`
- Fixing route handler type assertions for `createServerFn` and `useServerFn`
- Fixing `d3` type usage in `ConceptMap.tsx` and `MemoryFlow.tsx`

This completes the migration to a fully typed frontend with zero `any` usage.

## [2026-05-15] refactor | Eliminated any types across web app and consolidated database types

Replaced all remaining `any` type annotations with proper TypeScript types across the web app codebase, promoted `noExplicitAny` from `warn` to `error` in Biome, and rewrote `packages/database/index.ts` to use Supabase generated types with `Omit` for flexible JSON fields. Route handlers were updated to use `createServerFn` with `.inputValidator()` pattern. Infinite query factories now enforce `extends CursorPage` constraint for safe `getNextPageParam` access. Three D3 components (`ConceptMap`, `MemoryFlow`) received proper type annotations. All `any` overrides removed from `biome.json` except where genuinely required.

## [2026-05-15] refactor | Replace array index keys with stable content-hash keys

Changed `FormattedContent.tsx` to use a deterministic `partKey()` hash function instead of array index as React key. This improves React reconciliation stability when list order changes. Also removed the `noArrayIndexKey` Biome lint rule from `biome.json` since the codebase no longer uses array index keys.

## [2026-05-15] audit | Comprehensive Logging Audit & Traceback Hardening

Performed a system-wide audit of logging practices and implemented improvements to ensure rich, audit-ready observability data.

### Changes
- **Core Engine**: Updated `apps/engine/core/config.py` with an enhanced `LOG_FORMAT` that includes module names (`[%(name)s]`).
- **Traceback Hardening**: Replaced 100+ `logger.error()` calls with `logger.exception()` across the engine, providers (FMP, IBKR), and proxy. This ensures that the automated LLM log analyzer (DeepSeek) can perform root-cause analysis on the full stack trace.
- **Pipeline Observability**: Added granular success/total tracking to ingestion, snapshotting, and decision stages in `main.py`.
- **IBKR Proxy**: Hardened error handling and logging to match engine standards.
- **Documentation**: Established [[concepts/observability-standard]] as the project's canonical logging convention. Updated `AGENTS.md`, `ROADMAP.md`, and `apps/ibkr-proxy/README.md`.

### Result
The system now provides deterministic tracebacks for all critical failures, enabling the "anomaly detector" audit layer to accurately identify and suggest fixes for ingestion or execution errors without manual log mining.

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


