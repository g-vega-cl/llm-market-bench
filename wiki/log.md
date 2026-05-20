## [2026-05-20] fix | Prevent D3 Comparison Chart Spurious Vertical Line Anomalies

Implemented defensive input cleaning, sorting, and boundary checks in `PortfolioComparisonChart.tsx` to handle malformed data points safely:
- Added `React.useMemo` to filter out invalid dates, missing/NaN prices, and null indices from portfolio and benchmark data props at the component boundary.
- Deduplicated time-series coordinates by date to enforce a single data point per day, preventing x-axis duplicate coordinate ticks from rendering vertical overlapping segment spikes.
- Configured the D3 line path generator with `.defined()` checks to omit disjoint segments safely.
- Added comprehensive Vitest coverage to verify chart resilience against malformed datasets.

## [2026-05-20] refactor | Consolidate Scenario Analysis Parser Logic (DRY Migration)


Consolidated scenario-splitting, percentage-extracting, and outcome/trading-plan parsing logic from both `FutureCatalysts.tsx` and `MemoryCard.tsx` into a single, fully-tested utility `parseScenarios` in `apps/web/src/lib/parse-scenario-percentages.ts`. Refactored `MemoryCard.tsx` to use this consolidated helper. All unit tests, Biome linting, and production builds pass successfully.

## [2026-05-20] fix | Upgrade parseScenarioPercentages split logic for single-block text

Upgraded `parseScenarioPercentages` utility in `apps/web/src/lib/parse-scenario-percentages.ts` to support regex-based splitting (`/(Scenario [A-Z][^:]*:)/`) matching the design in `MemoryCard.tsx`. This ensures scenarios in `FutureCatalysts.tsx` are cleanly broken out with their respective badges regardless of database newline formatting, resolving cases where LLM responses output single blocks.


## [2026-05-20] docs | Enhance wiki cross-reference linking

Fixed weak/plain-text references in the wiki: changed plain-text mention of `Biome` in `wiki/concepts/type-safety.md` to `[[entities/biome-linter]]`, and plain-text mention of `correlation matrix` in `wiki/entities/engine.md` to `[[sources/correlation-matrix-source]]`. Verified with the structural wiki linter.

## [2026-05-20] docs | Align linter documentation with Biome rules and pre-commit hook

Aligned `wiki/concepts/project-linting.md` and `wiki/entities/biome-linter.md` with the active codebase rules, documenting that `noExplicitAny` is an error in `biome.json` and that any use of `Record<string, any>` or `as any` requires an inline `// biome-ignore` comment to pass the blocking pre-commit checks.

## [2026-05-20] docs | Standardized Source ID generation format in wiki

Standardized the Source ID generation description between `wiki/concepts/ingestion.md` and `wiki/entities/pipeline.md` to reference the actual Python implementation in `newsletter.py` (`news_{sender_clean}_{MD5[:8]}`).

## [2026-05-14] refactor | Design System Consolidation

Consolidated design system usage across all 9 web pages. Migrated all pages to use PageLayout wrapper, replaced raw headings with SectionHeading, fixed ReasoningPage (zero DS usage → full DS adoption), migrated ConceptsPage from gray→zinc color tokens, and updated PageLayout to remove min-h-screen (now handled by page-level divs). Satoshi font import removed in favor of system-ui fallback.

## [2026-05-14] refactor | EventChainPage UI refactor to use design system components

Refactored `EventChainPage.tsx` to use `Badge`, `Button`, `PageLayout`, and `SectionHeading` from the shared `@llm-market-bench/ui-design-system` package. Replaced inline styling and conditional class logic with centralized `getTypeBadgeColor` and `getImpactBadgeColor` helper functions. This improves consistency with the rest of the web app and reduces duplication.

## [2026-05-14] refactor | Design system Button migration & primitive cleanup

Replaced raw `<button>` elements with the design system's `Button` primitive across 10 components: ThoughtProcessFlow, DefaultCatchBoundary, NotFound, MemoriesList, PortfolioComparisonChart, HumanFriendlyPrompt, HumanFriendlyResponse, Auth, Login. Also removed unused primitives from `ui-design-system`: ErrorBoundary, Skeleton, CardHeader/CardBody/CardFooter, ErrorMessage. The Auth component additionally adopted `Input` and `Label` primitives. Added test coverage to verify DS component usage.

## [2026-05-14] refactor | Design system simplification

Removed Select primitive entirely, reduced Badge variants (removed `dot` variant, stripped `critical` and `low` severity), trimmed LoadingSpinner sizes (removed `xs` and `lg`), removed `elevated` Card variant and `accentBorder` props, eliminated `alert` gradient from HeroBackground and SectionHeading, and simplified severity mappings in AuditCard/FutureCatalysts severity mapping simplified to only `high`/`medium`. This is a>

## [2026-05-14] refactor | Design system simplification

Removed Select primitive entirely, reduced Badge variants (removed `dot` variant, stripped `critical` and `low` severity), trimmed LoadingSpinner sizes (removed `xs` and `lg`), removed `elevated` Card variant and `accentBorder` props, eliminated `alert` gradient from HeroBackground and SectionHeading, and simplified severity mappings in AuditCard/FutureCatalysts to only `high`/`medium`.

## [2026-05-14] investigation | MiniMax empty response & Gemini-3.1-flash-lite zero decisions

Added two investigation items to ROADMAP to ROADMAP.md:
- MiniMax market feeling analysis returning empty JSON responses, and Gemini-3.1-flash-lite generating zero trading decisions. These are non-trivial behavioral anomalies that may indicate model-specific issues requiring deeper analysis.

## [2026-05-14] investigation | MiniMax empty response & Gemini-3.1-flash-lite zero decisions

Added two investigation items to ROADMAP.md documenting behavioral anomalies: MiniMax market feeling analysis returning empty JSON responses, and Gemini-3.1-flash-lite generating zero trading decisions. These are non-trivial model-specific issues that may indicate reliability problems requiring deeper analysis.

## [2026-05-15] removal | Government incentive tracking removed; model upgraded to deepseek-v4-pro

- Removed `is_government_incentive` field from MacroEvent model and all related validation/enrichment logic (`_validate_and_enrich_government_events()`).
- Removed government incentive prompt instructions from the analysis prompt.
- The consensus `_is_vague_government_event()` helper remains for synthesis quality control.
- Upgraded default model from `deepseek-v4-flash` to `deepseek-v4-pro` across engine, web, and wiki linting.
- Updated raw/docs/reference/government-incentive-quick-ref.md to a removal notice.

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
