## [2026-05-14] perf | Parallel newsletter cleaning + snapshot optimization

### Changes
- **Parallel ad removal**: `ingest_newsletters()` now fetches all Gmail bodies first, then runs `clean_newsletter_content()` on all newsletters concurrently via `asyncio.gather()`. Previously each newsletter was cleaned sequentially (7 newsletters × ~7s = ~49s; now ~13s). Extracted `_fetch_raw_message()` from `_process_message()` to separate Gmail API fetch from LLM cleaning.
- **Snapshot filtering**: `_stage_snapshots_and_pca()` now only snapshots portfolios that hold actual positions. Empty cash-only portfolios (test_model, gpt-5-mini, etc.) are skipped, reducing 11 snapshots to ~5 per run.
- **Batch market data**: Snapshot price fetching switched from individual `get_quote()` calls (25+ sequential FMP API calls) to `get_quotes()` batch fetch (single batched API call). Also eliminated the double-call bug where `get_quote()` was called twice per ticker (once for truthiness, once for value).

### Files changed
- `apps/engine/ingest/newsletter.py`: +import asyncio, +`_fetch_raw_message()`, refactored `ingest_newsletters()` to three-phase (fetch → parallel-clean → assemble)
- `apps/engine/main.py`: `_stage_snapshots_and_pca()` — filter `if p.positions:`, use `get_quotes()` instead of dict comprehension with `get_quote()`
- `apps/engine/tests/test_newsletter.py`: +`test_ingest_newsletters_parallel_cleaning`, updated mocks from `_process_message` → `_fetch_raw_message`
- `apps/engine/tests/test_performance_snapshot.py`: +`test_stage_snapshots_skips_portfolios_without_positions`, +`test_stage_snapshots_uses_batch_get_quotes`
- `wiki/entities/pipeline.md`: noted parallel ad removal + snapshot filtering + batch fetch
- `wiki/concepts/ingestion.md`: noted parallel cleaning

### Test results
589 passed, 0 failed, no regressions.

## [2026-05-14] chore | Add batch-fix scripts for Biome lint rules

Added two utility scripts: `scripts/fix_button_types.py` adds `type="button"` to all `<button>` elements lacking a type attribute, and `scripts/fix_svg_titles.py` adds `<title>SVG</title>` as the first child of `<svg>` elements without a title. These automate fixing the Biome lint rules `useButtonType` and `noSvgWithoutTitle` across the entire codebase.

## [2026-05-16] infra | Wiki Lint CI stabilized — 75k context, DeepSeek V4 Pro, auto-issue creation

Successfully executed the full Wiki Lint GHA workflow after resolving multiple CI/CD and LLM parsing issues.
- **Milestone**: First successful end-to-end run of `wiki_lint_llm.py` in GitHub Actions.
- **Findings**: Identified 8 semantic issues (1 high, 3 medium, 4 low) and automatically created GitHub Issue #20 for remediation.
- **Stabilization**:
    - Implemented 75k character context cap to prevent window saturation.
    - Upgraded semantic model to `deepseek/deepseek-v4-pro`.
    - Resolved CI dependency errors (`python-dotenv`) and `PYTHONPATH` issues.
    - Hardened JSON extraction from LLM responses to handle duplicate or conversational output.
- **Documentation**: Created [[entities/wiki-linter]] to document the dual-linter architecture.

## [2026-05-16] fix | wiki_lint_llm.py AttributeError & observability

Fixed `AttributeError: 'NoneType' object has no attribute 'strip'` in `wiki_lint_llm.py` that occurred when OpenRouter returned `None` for message content. Also hardened against `IndexError` on empty choices and improved observability by logging the raw JSON response to `stderr` on any failure.

- **Robust Error Handling**: Added explicit checks for `error` keys, empty `choices`, and `None` content in OpenRouter responses.
- **Observability**: Raw response body is now printed to `stderr` before raising `RequestException`, enabling easier debugging in GitHub Actions logs.
- **TDD**: Created `apps/engine/tests/test_wiki_lint_llm.py` with 4 test cases mocking various failure modes.
- **Gemini Config**: Updated `.gemini/settings.json` to automatically load `AGENTS.md` as a foundational mandate.
- **DX**: Installed `ruff` in the engine venv (documented in `AGENTS.md`).

## [2026-05-14] design-system | Full design system adoption across all web app pages

### Context

The design system at `packages/ui-design-system/` was well-structured but inconsistently used: 14 files imported from it, but 7 pages used zero DS components, relying entirely on raw Tailwind. MarketOverviewPage had a 60-line raw copy-paste of HeroBackground. ReasoningPage used `gray-*` colors instead of the app's `zinc-*` palette. Five different raw "Load More" button implementations existed across the codebase.

### Changed files

- `apps/web/src/features/market-overview/pages/MarketOverviewPage.tsx` — HeroBackground replaces 60-line raw copy; Card for sentiment; Badge for status/direction; ConfidenceBar for scores; EmptyState for correlation pending; Card for sector grid. **-78 lines.**
- `apps/web/src/features/reasoning/pages/ReasoningPage.tsx` — 24 `gray-*` → `zinc-*` replacements
- `apps/web/src/features/portfolios/pages/PortfolioDetailPage.tsx` — Card + MetricTile for equity/cash; SectionHeading for section titles; Badge for "Audit Trail"; Card for empty state
- `apps/web/src/features/portfolios/pages/PortfoliosPage.tsx` — Card replaces raw portfolio cards; MetricTile for equity/cash/buying-power; Badge for active/retired; SectionHeading everywhere
- `apps/web/src/features/memories/pages/MemoriesPage.tsx` — Button for "Load More"; ErrorCard for errors; LoadingBoundary for loading; SectionHeading for header
- `apps/web/src/features/audits/pages/AuditsPage.tsx` — Button for "Load More"; ErrorCard; LoadingBoundary; LoadingSpinner for fetch indicator; SectionHeading
- `apps/web/src/features/cause-and-effect/pages/CauseAndEffectPage.tsx` — SectionHeading replaces raw h1
- `apps/web/src/routes/__root.tsx` — cn() utility replaces raw string concatenation; bg-white/80 replaces bg-opacity-80
- `packages/ui-design-system/README.md` — added Adoption section + Usage Patterns reference
- `wiki/sources/web-design-system-source.md` — updated takeaways with current state
- `wiki/entities/web-app.md` — removed stale Stack/Cluster/Grid/AgentPills/Timeline; added actual component inventory + cross-cutting conventions

### Before / After

- **Before**: 7 pages with zero DS usage; duplicate HeroBackground; 5 ad-hoc "Load More" implementations; inconsistent color palettes
- **After**: Every page uses the DS; unified loading/error/button patterns; consistent zinc palette; HeroBackground deduplicated; 86 tests all green; biome + ruff clean

### Key decisions

1. **Fix adoption before aesthetics** — user chose to get the DS consistently used everywhere before rethinking the visual language. This gives a clean foundation for the aesthetic refresh.
2. **No new DS components added** — existing primitives/patterns covered every use case. No abstraction was needed; just consistent usage.
3. **cn() utility for clean classNames** — replaced raw string concatenation patterns with the DS's cn utility where it improved readability.
4. **Patterns page in README** — documents which DS components each page uses, serving as a quick reference for contributors and a living inventory.

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

## [2026-05-18] fix | Resolved entities/gemini wiki lint errors

Fixed `[index-gap]` and `[orphan]` errors for `entities/gemini.md` by:
- Adding `[[entities/gemini]]` to `wiki/index.md`.
- Linking to `[[entities/gemini]]` from `[[concepts/agent-workflow]]`.

These issues were leftovers from the `AGENTS.md` → `GEMINI.md` rename session.

