# Wiki Log

## [2026-05-11] refactor | Two-tier prompt validator + simplified safety checker

Changed auto-research validator from single-tier to two-tier:

- **Hard invariants** (block activation): forbidden patterns ("bypass guardrails",
  "ignore verification feedback", "skip tool use", "ignore portfolio limits",
  "guess the price"), empty prompt, >3000 words
- **Soft invariants** (warn but allow): `calculate_buy_quantity`,
  `calculate_sell_quantity`, `5 Whys`

Rationale: the control portfolios (OpenAI + Claude on hardcoded baseline) and the
`<2 trades` safety checker already provide real guardrails. Over-constraining the
validator prevents the researcher from experimenting with alternative reasoning
techniques (MECE, first-principles, pre-mortem, etc.).

Also removed the `>90% rejection rate` crash detection threshold — high rejection
rates are normal (LLMs hallucinate often) and are handled by the verifier.
Safety checker now only reverts on `<2 executed trades`.

Files changed:
- `apps/engine/autoresearch/validator.py`
- `apps/engine/autoresearch/runner.py`
- `apps/engine/tests/test_autoresearch.py`
- `wiki/entities/autoresearch.md`
- `wiki/concepts/auto-research-prompt-improver.md`

## [2026-05-11] fix | Auto-research price_history column name mismatch

Fixed auto-research queries that used non-existent columns `date` and `close_price` on
the `price_history` table. The real columns are `fetched_at` and `price` (established in
migration `20260124020631_create_price_history.sql`). Affected files:

- `apps/engine/autoresearch/evaluator.py` — VIXY and SPY market-regime queries
- `apps/engine/autoresearch/metrics.py` — `_spy_returns()` SPY benchmark query

Added regression tests in `test_autoresearch.py`:
- `TestQuerySyntax.test_price_history_query_uses_fetched_at_and_price`
- `TestEvaluator.test_market_regime_queries_use_fetched_at_and_price`

Updated wiki pages to list `price_history` as a data source for metrics and
market regime context.

## [2026-05-11] fix | Auto-research crash after singleton refactor

Restored auto-research after the [2025-04-10] singleton refactor of
`core/db.py` left `apps/engine/autoresearch/prompt_store.py` calling
`get_async_supabase_client()` without `await`. Every call site passed a
coroutine where the supabase client was expected; the visible failure
was `'coroutine' object has no attribute 'auth'` from a `finally` block
that tried to close `sb_client.auth.http_client`. The same code path
also broke `core/llm/prompt_factory.py` on the trading hot path for
experiment agents.

- Added `await` to all 5 `get_async_supabase_client()` call sites in
  `prompt_store.py` and deleted the `try`/`finally` blocks that closed
  the http client — closing the singleton's transport would break the
  next caller.
- Updated the three `monkeypatch` stubs in `tests/test_autoresearch.py`
  to be `async def` so production `await` semantics are exercised in
  unit tests (the sync `lambda: client` was the reason CI stayed green
  while production failed).
- Removed unused `asyncio` import from the test file.
- 22 autoresearch tests pass.



Implemented a Karpathy-style autonomous prompt improvement loop:
- Created `apps/engine/autoresearch/` package: `program.md`, `metrics.py`,
  `decision_quality.py`, `evaluator.py`, `researcher.py`, `prompt_store.py`,
  `validator.py`, `window.py`, `runner.py`
- Added `prompt_experiments` DB table for versioned prompt storage with JSONB
  metrics and research output
- Only Gemini Flash Lite and DeepSeek Flash receive auto-researched prompts;
  OpenAI and Claude use hardcoded baseline as control group
- Only `CORE_ANALYSIS_SYSTEM_PROMPT` is modified — verifier, contrarian,
  and all other prompts are never touched
- Safety: prompt validator checks required tokens and forbidden phrases before
  activation; >90% rejection rate triggers auto-revert
- Weekly cron: Sunday 6 PM ET via `.github/workflows/autoresearch.yml`
- 22 tests covering metric math, decision quality, prompt store, validator,
  window helper, evaluator, query syntax, and migration
- Wiki: added [[entities/autoresearch]] and [[concepts/auto-research-prompt-improver]]

## [2026-05-08] init | Bootstrap Karpathy Wiki

Created the initial wiki structure for the LLM Market Bench project:
- Scaffolded wiki directory layout (SCHEMA.md, index.md, log.md, overview.md)
- Created entity pages for engine, web-app, database, pipeline
- Created concept pages for ingestion, reasoning, consensus, execution, memory-feedback, tool-enforcement, rag-strategy
- Created source summary pages for all docs/ files
- Installed QMD and configured wiki collection
- Generated initial embeddings
- Updated AGENTS.md with wiki operations guide

## [2026-05-08] audit | Full docs coverage audit — closed 8 gaps

Performed cross-reference between `docs/` (19 files) and `wiki/` (25 files).
Found 8 missing source summaries — all engine and web docs that were skipped
during the initial seeding. Created source pages for:

- `docs/engine/account-buying-power-reg-t4-calculations.md` → [[sources/reg-t-calculations-source]]
- `docs/engine/agent-specific-semantic-overlap.md` → [[sources/agent-specific-semantic-overlap-source]]
- `docs/web/README.md` → [[sources/web-architecture-source]]
- `docs/web/DESIGN_SYSTEM.md` → [[sources/web-design-system-source]]
- `docs/web/TANSTACK_BEST_PRACTICES.md` → [[sources/web-tanstack-best-practices-source]]
- `docs/web/portfolios-ui.md` → [[sources/web-portfolios-ui-source]]
- `docs/web/tanstack-start-deploy-official.md` → [[sources/web-deployment-source]]
- `docs/web/testing.md` → [[sources/web-testing-source]]

Enriched [[entities/web-app]] with web architecture, design system, deployment,
and testing details. Updated index.md. Wiki now covers 100% of existing docs/.
Re-indexed QMD (33 files, ~35 chunks).

## [2026-05-08] polish | Wiki automation & DX polish

- Created `apps/engine/wiki_lint.py` — structural lint (frontmatter, orphans, broken links, index gaps)
- Created `apps/engine/wiki_lint_llm.py` — OpenRouter LLM lint via `deepseek/deepseek-v4-flash`
- Created `.github/workflows/wiki-lint.yml` — weekly GH Action (Saturday 10:00 ET) + manual `workflow_dispatch`
- Updated `.husky/pre-commit` — conditional structural lint + QMD re-index when wiki/ changes
- Created `.husky/post-merge` — QMD re-index after pulling wiki changes
- Fixed AGENTS.md: `[[entity/page-name]]` → `[[entities/page-name]]`, added QMD fallback strategy
- Added `raw/README.md` — self-documenting ingest instructions for the raw/ directory
- Updated `wiki/SCHEMA.md` — documented automated lint tools (structural + LLM)

## [2026-05-08] consolidate | Single source of truth — archive docs/, delete wiki/sources/

Moved all 19 `docs/` files into `raw/docs/` as immutable frozen snapshots. Deleted
all 18 `wiki/sources/*.md` pages — they were mirrors of mutable internal docs, not
true Karpathy-style source summaries of external material.

- `docs/` → `raw/docs/` (preserved directory structure: engine/, web/, reference/)
- `wiki/sources/` — deleted (18 pages removed, going from 33 → 15 wiki pages)
- `wiki/index.md` — rebuilt without sources section (now: 4 entities, 7 concepts)
- `wiki/SCHEMA.md` — removed source-summary rules and naming conventions
- `wiki/entities/web-app.md` — replaced broken `[[sources/...]]` links with `raw/docs/web/` refs
- `README.md` — rewrote Documentation section: wiki/ is primary, raw/docs/ is reference
- `AGENTS.md` — removed stale `## Docs` links, updated directory layout (no sources/)
- `ROADMAP.md` — updated `docs/web/DESIGN_SYSTEM.md` → `raw/docs/web/DESIGN_SYSTEM.md`
- Python code references (`reg_t_validation.py`, `test_reg_t_validation.py`, `test_portfolio.py`) — updated `docs/` → `raw/docs/engine/` paths

The wiki is now the single canonical knowledge layer. `raw/docs/` preserves the
originals as auditable snapshots.

## [2026-05-15] audit | "Proper Setup" Audit & Karpathy Method Compliance

Performed a deep audit of the wiki against Andrej Karpathy's LLM Wiki pattern.
Restored the "Sources" layer for better provenance and established an "Interactions"
layer for compounding knowledge.

- **Sources Layer**: Created 19 synthesized summaries in `wiki/sources/` for all
  immutable docs in `raw/docs/`. These capture "why it matters" and key takeaways
  to provide a provenance trail without duplicating content.
- **Interactions Layer**: Created `wiki/interactions/` and added the first entry
  [[interactions/wiki-proper-setup-audit]] documenting the requirements for a
  "properly set up" Karpathy wiki.
- **Scaffold Updates**: Rebuilt [[index]] with Sources and Interactions sections.
  Updated [[SCHEMA]] with new categories and conventions.
- **Quality Audit**: Fixed environment to support `wiki_lint.py` (added `pyyaml`).
  Executed structural lint, fixed 1 broken link in interactions. Wiki is 100%
  clean (35 pages).
- **Compounding Knowledge**: Promoted this audit session to the wiki to ensure
  setup principles are preserved for future LLM sessions.

## [2026-05-10] feature | Auto-wiki documentation generation

Added `apps/engine/auto_wiki.py` — a script that reads staged git diffs, sends them to an LLM (OpenRouter with ollama fallback), and automatically creates/updates wiki pages, log entries, and index entries. Integrated into the pre-commit hook via `scripts/auto-wiki.sh`, which runs non-blocking and only triggers on code changes (skips wiki/raw/docs-only commits). The script supports dry-run mode, keychain-based API key resolution, and configurable models.

## [2026-05-11] refactor | Centralized model name constants

Extracted hardcoded model name strings into shared constants across the codebase:
- Created `apps/web/src/config/models.ts` with `MODELS` object for all LLM identifiers
- Updated `agent-info.ts`, `AgentInsights.test.tsx`, and `how-it-works.tsx` to use the new constants
- Updated `test_post_analysis.py` to use `GEMINI_MODEL` from config
- Renamed Gemini model from `gemini-3.1-flash-lite-preview` to `gemini-3.1-flash-lite` in `packages/config/models.json`

This eliminates magic strings and ensures model names are consistent across engine and web layers.

## [2026-05-11] refactor | Centralized model name constants

Extracted hardcoded model name strings into shared constants across the codebase:
- Created `apps/web/src/config/models.ts` with `MODELS` object for all LLM identifiers
- Updated `agent-info.ts`, `AgentInsights.test.tsx`, and `how-it-works.tsx` to use the new constants
- Updated `test_post_analysis.py` to use `GEMINI_MODEL` from config
- Renamed Gemini model from `gemini-3.1-flash-lite-preview` to `gemini-3.1-flash-lite` in `packages/config/models.json`

This eliminates magic strings and ensures model names are consistent across engine and web layers.

## 2025-04-10 refactor | Singleton Supabase client pattern

Refactored `core/db.py` to implement singleton caching for both sync and async Supabase clients. The `get_supabase_client()` and `get_async_supabase_client()` functions now cache their respective clients globally, avoiding redundant client creation on every call. The async client now uses `AsyncClientOptions` instead of `ClientOptions`. The `_get_market_regime_summary` function in `autoresearch/evaluator.py` was updated to call `get_supabase_client()` internally rather than accepting it as a parameter. A `requirements.lock` file was added with pinned versions for reproducible builds, and `supabase` dependency was pinned to `~=2.27.0`.

## 2025-04-10 enhancement | Auto-wiki now includes staged raw/ documents in context

Enhanced `auto_wiki.py` to read staged `raw/` documents via `git diff --cached` and include them in the LLM context. This ensures the auto-wiki generator sees human-written design intent alongside existing wiki pages, improving documentation quality and relevance.

## [2026-05-11] fix | Auto-research price_history column name mismatch

Fixed auto-research queries that used non-existent columns `date` and `close_price` on
the `price_history` table. The real columns are `fetched_at` and `price` (established in
migration `20260124020631_create_price_history.sql`). Affected files:

- `apps/engine/autoresearch/evaluator.py` — VIXY and SPY market-regime queries
- `apps/engine/autoresearch/metrics.py` — `_spy_returns()` SPY benchmark query

Added regression tests in `test_autoresearch.py`:
- `TestQuerySyntax.test_price_history_query_uses_fetched_at_and_price`
- `TestEvaluator.test_market_regime_queries_use_fetched_at_and_price`

Updated wiki pages to list `price_history` as a data source for metrics and
market regime context.

## [2026-05-11] fix | Auto-research price_history column name mismatch

Fixed auto-research queries that used non-existent columns `date` and `close_price` on
the `price_history` table. The real columns are `fetched_at` and `price` (established in
migration `20260124020631_create_price_history.sql`). Affected files:

- `apps/engine/autoresearch/evaluator.py` — VIXY and SPY market-regime queries
- `apps/engine/autoresearch/metrics.py` — `_spy_returns()` SPY benchmark query

Added regression tests in `test_autoresearch.py`:
- `TestQuerySyntax.test_price_history_query_uses_fetched_at_and_price`
- `TestEvaluator.test_market_regime_queries_use_fetched_at_and_price`

Updated wiki pages to list `price_history` as a data source for metrics and
market regime context.
