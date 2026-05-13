# Wiki Log

## [2026-05-14] fix | Alpaca order status sync — decoupled cron job (SUBMITTED → FILLED)

Fixed the bug where `alpaca_status` permanently showed `PENDING` in the dashboard
even though Alpaca had filled the order. Root cause: the original "fire-and-forget"
design had no sync mechanism back from Alpaca to Supabase.

**Changes**:
- `execution/alpaca_broker.py`: Renamed initial status `PENDING` → `SUBMITTED`
- `scripts/sync_alpaca_orders.py`: New standalone script — queries pending trades,
  checks Alpaca via `get_order_by_id()`, updates status
- `.github/workflows/sync-alpaca.yml`: Daily cron at 4pm ET + manual dispatch
- `TradesTable.tsx`: Handles both `PENDING` (legacy) and `SUBMITTED`
- `supabase/migrations/20260514000000_add_alpaca_filled_at_to_trades.sql`: New column
- `concepts/alpaca-order-sync.md`: New wiki page documenting the architecture

In-process polling was rejected because `asyncio.run()` cancels pending tasks
when the pipeline completes. The decoupled cron approach is simpler and more reliable.

## [2026-05-13] docs | Expanded macro tracker and ETF universe — copper, bonds, crypto, country coverage

Added 13 new tickers across three tracking systems to give LLM agents a more
complete picture of the global economy:

**Macro Tracker** (macro_tracker.py): 16→23 tickers, 4→6 categories.
New: Fixed Income (TLT, TIP, IEF), Crypto (BTCUSD), FX & Risk (UUP, VIXY).
New international: EWU (UK), EWC (Canada), INDA (India).
New commodities: UNG (Natural Gas).

**Benchmark Tickers** (update_prices.py): 9→16 tickers.
Added TLT, TIP, UNG, BTCUSD, EWU, EWC, CPER for benchmark tracking.

**Correlation Universe** (correlation_matrix.py): 57→70 tickers.
Added CPER, HYG, AGG, XOP, XME, XBI, KRE, XRT, INDA, EWA, DBA, XHB, EMLC.

**Frontend** (BenchmarkSelector.tsx): 9→16 benchmark options in the dropdown.

Documented at [[entities/macro-tracker]], [[sources/correlation-matrix-source]].

## [2026-05-13] docs | Supabase Data API grants — proactive migration and convention

Supabase announced that explicit GRANTs will be required for public schema
tables starting October 30, 2026 for existing projects. Created migration
`20260513000000_add_explicit_grants_for_data_api.sql` adding GRANT SELECT
to anon/authenticated (for web frontend reads) and GRANT ALL to service_role
(for engine writes) on all 18 existing tables. Documented the convention at
[[concepts/supabase-grant-convention]]. Updated [[entities/database]] and
`wiki/index.md` with cross-references.

## [2026-05-13] cleanup | Auto-research: delete dead code from metrics.py (~130 lines)

Removed the old 8-dimension composite score machinery left over from the
2026-05-12 simplification. TDD: updated test mocks first, then deleted.

**Deleted:**
- `compute_composite_score()` — old 8-weight composite, replaced by `compute_score()`
- `_normalize_sharpe()`, `_normalize_sortino()`, `_normalize_drawdown()`,
  `_normalize_profit_factor()`, `_normalize_info_ratio()` — all dead normalizers
- `_realized_pnl()` — only consumer was profit_factor in the old composite
- `TRADING_DAYS_PER_YEAR` (252), `RISK_FREE_RATE` (0.05) — only used for Sharpe/Sortino
- `from math import sqrt` — only used for Sharpe/Sortino/Info Ratio
- `spy_returns` parameter on `compute_wall_street_metrics()` — Info Ratio was the
  only consumer; evaluator already computes SPY return separately via `_spy_returns()`

**Slimmed:**
- `compute_wall_street_metrics()` now returns only `{"total_return_pct": X, "max_drawdown": Y}`
  (was an 8-field dict with sharpe/sortino/profit_factor/info_ratio/num_trading_days)

**Test changes:**
- 5 mock return values trimmed to 2 fields each
- `test_price_history_query_uses_fetched_at_and_price` now tests `_spy_returns()` directly
  instead of indirectly through `compute_wall_street_metrics()`

**Test suite: 582 passing (unchanged).**

## [2026-05-13] fix | Auto-research: hard ratchet — enforce Karpathy baseline revert

When an experiment fails to beat the baseline (score < baseline), the active prompt
is now reverted to the baseline via `revert_to_baseline()` BEFORE the meta-researcher
runs. This is code-level enforcement of the Karpathy ratchet — the meta-researcher
always builds from the known-good foundation, never from a failed experiment.

Previously this was a "soft ratchet" — `program.md` instructed the LLM to use the
baseline as foundation, but nothing in the code enforced it. A failed experiment's
prompt remained active, and the meta-researcher could drift further from the baseline.

**Changes:**
- `prompt_store.py` — new `revert_to_baseline()`: demotes current active to 'kept',
  promotes the all-time baseline variant to 'active'. Idempotent if baseline is
  already active.
- `runner.py` — calls `revert_to_baseline()` when `score < baseline_score`.
  Dry-run logs the intent without executing.
- `__init__.py` — exports `revert_to_baseline`.
- `test_autoresearch.py` — 4 updated tests: revert called when below baseline,
  NOT called when above or when baseline unavailable. Removed duplicate test.

**Test suite: 34 passing.**

## [2026-05-12] simplify | Auto-research: remove validator + decision_quality, single score

Major simplification of the auto-research system. TDD-driven with 30 passing tests.

**Deleted:**
- `autoresearch/validator.py` — 5 bypassable regex patterns + word cap. Replaced by trust in the safety checker.
- `autoresearch/decision_quality.py` — conviction calibration, regime awareness, mistake patterns, sample trades. All unnecessary for single-score target.

**New score formula:**
```
score = (portfolio_return_pct - spy_return_pct) - (max_drawdown_pct × 0.3)
```
Replaces the 8-dimension weighted composite (Sharpe, Sortino, MaxDD, Profit Factor, Info Ratio, Concordance, Conviction, Regime Awareness).

**Simplified:**
- `evaluator.py` — 301→126 lines. No more VIXY queries, concordance, stagnation checks, or long-formatted reports.
- `runner.py` — 180→168 lines. No validator call. Gate: score ≥ 0 → skip, score < 0 → deploy.
- `program.md` — 78→55 lines. Single-score focused.
- `bootstrap.py` — baseline score: 0 (was 0.5 composite).
- `__init__.py` — exports cleaned up.

**Test suite: 33 passing** — added TestBaselineTracking (3 tests): baseline is max, shows delta, handles first week.

## [2026-05-12] simplify | Auto-research: always deploy, target-to-beat

Removed the activation gate. Every week deploys a new prompt variant regardless of score.
The meta-researcher's goal is now explicit: beat last week's score (shown as "Target to beat" with Δ).

- `runner.py` — removed the `score >= 0 → skip` gate. Always calls save_variant.
- `evaluator.py` — report now includes "Target to beat: X (Δ: +/-Y vs last week)".
- `program.md` — updated goal: "beat last week's score."
- `TestActivationGate` — renamed methods, now asserts deploy on all score values (positive, negative, zero).

## [2026-05-12] simplify | Auto-research: remove validator + decision_quality, single score

Comprehensive TDD-driven fixes from a detailed codebase interview (the "grill me"
session). All 7 issues identified, tested, and resolved:

1. **`_close_client` removed from `researcher.py`** — the `finally` block that
   closed the singleton httpx client violated the wiki's own async-client contract.
   GitHub Actions kills the process anyway; in local runs the singleton must stay
   alive.

2. **`regime_awareness` wired into composite score** — was accepted as a
   parameter but silently discarded (dead code). Now computed from actual VIXY
   price data: compares pre-week VIXY to in-week average, scores how well the
   agent's BUY/SELL ratio matched the volatility regime. Gets 0.10 weight.
   Weights rebalanced: Sharpe 0.15, Sortino 0.15, Drawdown 0.15, Profit 0.15,
   Info 0.10, Concordance 0.10, Conviction 0.10, Regime 0.10.

3. **Double `get_week_window()` eliminated** — runner now computes the window
   once and passes it to `evaluate_week()`. Evaluator accepts optional params
   with fallback. Prevents midnight drift in window boundaries.

4. **`_check_safety` now queries `trades` table** — previously counted
   `status="EXECUTED"` in `decisions` table, which could differ from actual
   settled trades. Now joins through `portfolios!inner(owner_id)` to count
   real trades.

5. **Bootstrap fixed and tested** — removed `sys.path.append(os.path.join(
   os.getcwd(), "apps", "engine"))` CWD-dependent hack. Now uses proper relative
   imports. Added idempotency test.

6. **Validator uses word-count cap** — conservative 1000-word limit
   (roughly ~1300 tokens for English prose). No external tokenizer dependency.
   `program.md` constraint updated to match.

7. **Composite score edge cases** — now returns `"warnings"` list:
   `NO_TRADING_DATA` when `num_trading_days == 0`, `NO_BENCHMARK` when
   `info_ratio == 0` (missing SPY data). Tests for worst-case inputs,
   no-data scenarios, and function boundary values.

Files changed:
- `apps/engine/autoresearch/researcher.py`
- `apps/engine/autoresearch/metrics.py`
- `apps/engine/autoresearch/decision_quality.py`
- `apps/engine/autoresearch/evaluator.py`
- `apps/engine/autoresearch/runner.py`
- `apps/engine/autoresearch/validator.py`
- `apps/engine/autoresearch/bootstrap.py`
- `apps/engine/autoresearch/program.md`
- `apps/engine/tests/test_autoresearch.py`
- `wiki/entities/autoresearch.md`
- `wiki/concepts/auto-research-prompt-improver.md`

Test suite: 590 passed, 2 skipped, 1 warning. 17 new tests added across 7 test
classes.

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

## [2026-05-11] fix | Auto-research code audit — 7 fixes from deep code review

Comprehensive TDD-driven fixes from a detailed codebase interview (the "grill me"
session). All 7 issues identified, tested, and resolved:

1. **`_close_client` removed from `researcher.py`** — the `finally` block that
   closed the singleton httpx client violated the wiki's own async-client contract.
   GitHub Actions kills the process anyway; in local runs the singleton must stay
   alive.

2. **`regime_awareness` wired into composite score** — was accepted as a
   parameter but silently discarded (dead code). Now computed from actual VIXY
   price data: compares pre-week VIXY to in-week average, scores how well the
   agent's BUY/SELL ratio matched the volatility regime. Gets 0.10 weight.
   Weights rebalanced: Sharpe 0.15, Sortino 0.15, Drawdown 0.15, Profit 0.15,
   Info 0.10, Concordance 0.10, Conviction 0.10, Regime 0.10.

3. **Double `get_week_window()` eliminated** — runner now computes the window
   once and passes it to `evaluate_week()`. Evaluator accepts optional params
   with fallback. Prevents midnight drift in window boundaries.

4. **`_check_safety` now queries `trades` table** — previously counted
   `status="EXECUTED"` in `decisions` table, which could differ from actual
   settled trades. Now joins through `portfolios!inner(owner_id)` to count
   real trades.

5. **Bootstrap fixed and tested** — removed `sys.path.append(os.path.join(
   os.getcwd(), "apps", "engine"))` CWD-dependent hack. Now uses proper relative
   imports. Added idempotency test.

6. **Validator uses word-count cap** — conservative 1000-word limit
   (roughly ~1300 tokens for English prose). No external tokenizer dependency.
   `program.md` constraint updated to match.

7. **Composite score edge cases** — now returns `"warnings"` list:
   `NO_TRADING_DATA` when `num_trading_days == 0`, `NO_BENCHMARK` when
   `info_ratio == 0` (missing SPY data). Tests for worst-case inputs,
   no-data scenarios, and function boundary values.

Files changed:
- `apps/engine/autoresearch/researcher.py`
- `apps/engine/autoresearch/metrics.py`
- `apps/engine/autoresearch/decision_quality.py`
- `apps/engine/autoresearch/evaluator.py`
- `apps/engine/autoresearch/runner.py`
- `apps/engine/autoresearch/validator.py`
- `apps/engine/autoresearch/bootstrap.py`
- `apps/engine/autoresearch/program.md`
- `apps/engine/tests/test_autoresearch.py`
- `wiki/entities/autoresearch.md`
- `wiki/concepts/auto-research-prompt-improver.md`

Test suite: 590 passed, 2 skipped, 1 warning. 17 new tests added across 7 test
classes.

## [2026-05-11] fix | save_variant atomicity: insert before demotion

Reordered operations in `save_variant` to insert the new prompt variant BEFORE demoting the previous active variant. Previously, the demotion (UPDATE) ran first, which could leave no active variant if the subsequent INSERT failed. Now the INSERT happens first, and the demotion uses `neq()` to avoid demoting the just-inserted row. This ensures atomicity and prevents data loss. Added `TestSaveVariantAtomicity` in `test_autoresearch.py` to enforce the insert-before-demotion order.

## [2026-05-11] refactor | Convert autoresearch DB calls to async client

Converted all synchronous Supabase client calls in the autoresearch module to use the async client (`get_async_supabase_client`). Affected files: `metrics.py`, `decision_quality.py`, `evaluator.py`, `runner.py`. Internal helper functions (`_daily_returns`, `_spy_returns`, `_realized_pnl`, `_fetch_decisions`, `_fetch_trades`, `_compute_vixy_trend`, `_get_market_regime_summary`, `_check_safety`) were made async. Tests updated to use `_AsyncQueryRecorder` and `pytest.mark.asyncio`. Added `TestResearcherRetry` for `run_research` retry-loop coverage. Added `TestStagnationEdgeCases` for floor-level stagnation detection. Added `AUTORESEARCH_RESULT` summary log lines in `runner.py` for grep-ability. Renamed `_count_tokens` to `_count_words` in `validator.py` and fixed wiki tiktoken reference.

## [2026-05-12] feature | Auto-research dry-run mode

Added `--dry-run` flag to the `autoresearch` CLI command. When enabled, the auto-research cycle evaluates performance, generates a new prompt proposal, and validates it — but does not write to the database or change the active prompt. Useful for testing and previewing prompt changes before activation.

## [2026-05-12] feature | Auto-research dry-run mode

Added `--dry-run` flag to the `autoresearch` CLI command. When enabled, the auto-research cycle evaluates performance, generates a new prompt proposal, and validates it — but does not write to the database or change the active prompt. Useful for testing and previewing prompt changes before activation.

## [2026-05-12] refactor | Auto-research: concordance redefined and activation gate added

Replaced the old BUY/SELL pair concordance in `decision_quality.py` with new equity-change comparison (experiment vs control total_return_pct) in `evaluator.py`. Added a gate in `runner.py` that only activates a new prompt if the experiment composite score exceeds the baseline. Also optimized `compute_wall_street_metrics` to accept pre-fetched SPY returns to avoid duplicate API calls when evaluating both experiment and control groups.

## [2026-05-12] fix | Auto-research: activation gate logic inverted

The activation gate in `runner.py` was checking `exp_score <= baseline` — blocking
prompt changes when the experiment was UNDERperforming. This is backwards: you
want to change the prompt when it's failing, not when it's already winning.

Flipped to `exp_score >= baseline` — skip activation when the experiment already
beats the baseline (no change needed), activate when it's below (prompt needs
improvement). Result tag changed from `SKIPPED_NO_IMPROVEMENT` to
`SKIPPED_ALREADY_WINNING` to reflect the new semantics. Both dry-run and
real-run paths updated.

## [2026-05-12] refactor | Removed soft invariant enforcement from auto-research prompt validator

The auto-research prompt validator previously enforced soft invariants (presence of "calculate_buy_quantity", "calculate_sell_quantity", "5 Whys") with warnings. These have been removed to make the prompt an experiment space. Only hard invariants (forbidden patterns, empty/oversized prompts) remain. The `program.md` constraints were also simplified to match.

## [2026-05-12] refactor | Reordered market-regime fetch in evaluator for better query grouping

Moved `_get_market_regime_summary()` call in `evaluate_week()` from after
`get_previous_variants()` to right after the SPY fetch at the top of the
function. This groups its VIXY price_history query near the VIXY queries
that `compute_decision_quality` fires internally, instead of interleaving
them with the `prompt_experiments` queries from `get_previous_variants`
and `get_baseline_metrics`.

Considered and rejected deduplicating the SPY price_history query (fired
by both `_spy_returns` and `_get_market_regime_summary`). The fix required
adding side-effect parameters (`out_rows`) and conditional branching to
two private functions — complexity cost far outweighed saving one ~50ms
HTTP call against a local Supabase endpoint.

Files:
- `apps/engine/autoresearch/evaluator.py` — moved one function call up ~55 lines

## [2026-05-12] fix | Auto-research query timestamp and baseline ordering bugs

TDD-driven fixes for two bugs identified during a dry-run log review:

1. **price_history queries cut off at midnight on the last day** —
   `_spy_returns()` (metrics.py) and both VIXY/SPY branches of
   `_get_market_regime_summary()` (evaluator.py) used `.lte("fetched_at",
   week_end.isoformat())`, which resolves to `2026-05-10T00:00:00Z`. This
   silently dropped any end-of-day prices fetched on the last trading day.
   Fixed to use `f"{week_end.isoformat()}T23:59:59"`, consistent with how
   `trades`, `decisions`, and `_compute_vixy_trend` already filter.

2. **`get_baseline_metrics()` returned the oldest baseline** — ordered by
   `created_at` ascending (`desc=False`) with `limit(1)`, so it always
   fetched the bootstrap seed (`composite: 0.5`) instead of the most recent
   baseline. Changed to `desc=True`.

Tests added in `test_autoresearch.py`:
- `TestPriceHistoryEndOfDayFiltering` (3 cases)
- `TestBaselineMetricsOrdering` (1 case)

All 56 autoresearch tests pass.

Files:
- `apps/engine/autoresearch/metrics.py`
- `apps/engine/autoresearch/evaluator.py`
- `apps/engine/autoresearch/prompt_store.py`
- `apps/engine/tests/test_autoresearch.py`

## [2026-05-12] fix | Auto-research query timestamp and baseline ordering bugs

TDD-driven fixes for two bugs identified during a dry-run log review:

1. **price_history queries cut off at midnight on the last day** —
   `_spy_returns()` (metrics.py) and both VIXY/SPY branches of
   `_get_market_regime_summary()` (evaluator.py) used `.lte("fetched_at",
   week_end.isoformat())`, which resolves to `2026-05-10T00:00:00Z`. This
   silently dropped any end-of-day prices fetched on the last trading day.
   Fixed to use `f"{week_end.isoformat()}T23:59:59"`, consistent with how
   `trades`, `decisions`, and `_compute_vixy_trend` already filter.

2. **`get_baseline_metrics()` returned the oldest baseline** — ordered by
   `created_at` ascending (`desc=False`) with `limit(1)`, so it always
   fetched the bootstrap seed (`composite: 0.5`) instead of the most recent
   baseline. Changed to `desc=True`.

Tests added in `test_autoresearch.py`:
- `TestPriceHistoryEndOfDayFiltering` (3 cases)
- `TestBaselineMetricsOrdering` (1 case)

All 56 autoresearch tests pass.

Files:
- `apps/engine/autoresearch/metrics.py`
- `apps/engine/autoresearch/evaluator.py`
- `apps/engine/autoresearch/prompt_store.py`
- `apps/engine/tests/test_autoresearch.py`

## [2026-05-12] simplify | Auto-research: remove validator + decision_quality, single score

Major simplification of the auto-research system. TDD-driven with 30 passing tests.

**Deleted:**
- `autoresearch/validator.py` — 5 bypassable regex patterns + word cap. Replaced by trust in the safety checker.
- `autoresearch/decision_quality.py` — conviction calibration, regime awareness, mistake patterns, sample trades. All unnecessary for single-score target.

**New score formula:**
```
score = (portfolio_return_pct - spy_return_pct) - (max_drawdown_pct × 0.3)
```
Replaces the 8-dimension weighted composite (Sharpe, Sortino, MaxDD, Profit Factor, Info Ratio, Concordance, Conviction, Regime Awareness).

**Simplified:**
- `evaluator.py` — 301→126 lines. No more VIXY queries, concordance, stagnation checks, or long-formatted reports.
- `runner.py` — 180→168 lines. No validator call. Always deploys new variant.
- `program.md` — 78→55 lines. Single-score focused.
- `bootstrap.py` — baseline score: 0 (was 0.5 composite).
- `__init__.py` — exports cleaned up.

**Test suite: 33 passing** — added TestBaselineTracking (3 tests): baseline is max, shows delta, handles first week.

## [2026-05-13] cleanup | Auto-research: delete dead code from metrics.py (~130 lines)

Removed the old 8-dimension composite score machinery left over from the
2026-05-12 simplification. TDD: updated test mocks first, then deleted.

**Deleted:**
- `compute_composite_score()` — old 8-weight composite, replaced by `compute_score()`
- `_normalize_sharpe()`, `_normalize_sortino()`, `_normalize_drawdown()`,
  `_normalize_profit_factor()`, `_normalize_info_ratio()` — all dead normalizers
- `_realized_pnl()` — only consumer was profit_factor in the old composite
- `TRADING_DAYS_PER_YEAR` (252), `RISK_FREE_RATE` (0.05) — only used for Sharpe/Sortino
- `from math import sqrt` — only used for Sharpe/Sortino/Info Ratio
- `spy_returns` parameter on `compute_wall_street_metrics()` — Info Ratio was the
  only consumer; evaluator already computes SPY return separately via `_spy_returns()`

**Slimmed:**
- `compute_wall_street_metrics()` now returns only `{"total_return_pct": X, "max_drawdown": Y}`
  (was an 8-field dict with sharpe/sortino/profit_factor/info_ratio/num_trading_days)

**Test changes:**
- 5 mock return values trimmed to 2 fields each
- `test_price_history_query_uses_fetched_at_and_price` now tests `_spy_returns()` directly
  instead of indirectly through `compute_wall_street_metrics()`

**Test suite: 582 passing (unchanged).**

## [2026-05-13] fix | Auto-research: hard ratchet — enforce Karpathy baseline revert

When an experiment fails to beat the baseline (score < baseline), the active prompt
is now reverted to the baseline via `revert_to_baseline()` BEFORE the meta-researcher
runs. This is code-level enforcement of the Karpathy ratchet — the meta-researcher
always builds from the known-good foundation, never from a failed experiment.

Previously this was a "soft ratchet" — `program.md` instructed the LLM to use the
baseline as foundation, but nothing in the code enforced it. A failed experiment's
prompt remained active, and the meta-researcher could drift further from the baseline.

**Changes:**
- `prompt_store.py` — new `revert_to_baseline()`: demotes current active to 'kept',
  promotes the all-time baseline variant to 'active'. Idempotent if baseline is
  already active.
- `runner.py` — calls `revert_to_baseline()` when `score < baseline_score`.
  Dry-run logs the intent without executing.
- `__init__.py` — exports `revert_to_baseline`.
- `test_autoresearch.py` — 4 updated tests: revert called when below baseline,
  NOT called when above or when baseline unavailable. Removed duplicate test.

**Test suite: 34 passing.**

## [2026-05-13] test | Add single-agent daily returns test

Added `test_single_agent_returns_unchanged` to `test_autoresearch.py` to verify that the daily returns calculation works correctly when only one agent is present. The test confirms a +10% daily return is computed as 0.10.

## [2026-05-13] test | Add multi-agent daily returns averaging tests

Added `test_two_agents_two_days` to `test_autoresearch.py` to verify that `_daily_returns` correctly averages returns across multiple agents over multiple days. The test confirms that with two agents and three days of data, the two daily return values are properly averaged: Day 1→2 averages +10% and -10% to 0.0; Day 2→3 averages -9.09% and +11.11% to approximately 0.0101.

## [2026-05-13] refactor | Equal-weight daily returns in auto-research metrics

Refactored `_daily_returns` in `autoresearch/metrics.py` to compute per-agent percentage returns independently and average them across agents per day, instead of aggregating raw equity first. This ensures equal weighting regardless of portfolio size ($10K vs $5K both count equally). Added tests for single-agent and multi-agent scenarios.

## [2026-05-13] refactor | Equal-weight daily returns in auto-research metrics

Refactored `_daily_returns` in `autoresearch/metrics.py` to compute per-agent percentage returns independently and average them across agents per day, instead of aggregating raw equity first. This ensures equal weighting regardless of portfolio size ($10K vs $5K both count equally). Added tests for single-agent and multi-agent scenarios.

## [2026-05-13] refactor | Equal-weighted percentage returns in _daily_returns

Rewrote `_daily_returns()` in `autoresearch/metrics.py` to compute per-agent percentage returns independently and average them per day, instead of aggregating raw equity across agents. This ensures equal weighting regardless of portfolio size ($10K vs $5K both count equally). Added test class `TestDailyReturnsEqualWeighted` with four tests: two agents with different returns, single agent, multi-day averaging, and missing-day edge case.

**Files changed:** `apps/engine/autoresearch/metrics.py`, `apps/engine/tests/test_autoresearch.py`

## [2026-05-13] docs | Expanded macro tracker and ETF universe — copper, bonds, crypto, country coverage

Added 13 new tickers across three tracking systems to give LLM agents a more
complete picture of the global economy:

**Macro Tracker** (macro_tracker.py): 16→23 tickers, 4→6 categories.
New: Fixed Income (TLT, TIP, IEF), Crypto (BTCUSD), FX & Risk (UUP, VIXY).
New international: EWU (UK), EWC (Canada), INDA (India).
New commodities: UNG (Natural Gas).

**Benchmark Tickers** (update_prices.py): 9→16 tickers.
Added TLT, TIP, UNG, BTCUSD, EWU, EWC, CPER for benchmark tracking.

**Correlation Universe** (correlation_matrix.py): 57→70 tickers.
Added CPER, HYG, AGG, XOP, XME, XBI, KRE, XRT, INDA, EWA, DBA, XHB, EMLC.

**Frontend** (BenchmarkSelector.tsx): 9→16 benchmark options in the dropdown.

Documented at [[entities/macro-tracker]], [[sources/correlation-matrix-source]].

## [2026-05-13] docs | Expanded macro tracker and ETF universe — copper, bonds, crypto, country coverage

Added 13 new tickers across three tracking systems to give LLM agents a more complete picture of the global economy:

**Macro Tracker** (macro_tracker.py): 16→23 tickers, 4→6 categories. New: Fixed Income (TLT, TIP, IEF), Crypto (BTCUSD), FX & Risk (UUP, VIXY). New international: EWU (UK), EWC (Canada), INDA (India). New commodities: UNG (Natural Gas).

**Benchmark Tickers** (update_prices.py): 9→16 tickers. Added TLT, TIP, UNG, BTCUSD, EWU, EWC, CPER for benchmark tracking.

**Correlation Universe** (correlation_matrix.py): 57→70 tickers. Added CPER, HYG, AGG, XOP, XME, XBI, KRE, XRT, INDA, EWA, DBA, XHB, EMLC.

**Frontend** (BenchmarkSelector.tsx): 9→16 benchmark options in the dropdown.

Documented at [[entities/macro-tracker]], [[sources/correlation-matrix-source]].

## [2026-05-13] documentation | QMD runtime constraints and model download behavior

Added runtime notes to AGENTS.md and wiki/SCHEMA.md documenting that QMD's native module requires Node 22-25 (not 26+), with nvm workaround. Also documented that `qmd query` and `qmd vsearch` download a ~1.3GB embedding model on first use, while `qmd search` and `qmd get` work immediately without a model.

## [2026-05-13] documentation | QMD runtime constraints and model download behavior

Added runtime notes to AGENTS.md and wiki/SCHEMA.md documenting that QMD's native module requires Node 22-25 (not 26+), with nvm workaround. Also documented that `qmd query` and `qmd vsearch` download a ~1.3GB embedding model on first use, while `qmd search` and `qmd get` work immediately without a model.

## [2026-05-13] fix | Alpaca order status sync — decoupled cron job (SUBMITTED → FILLED)

Fixed the bug where `alpaca_status` permanently showed `PENDING` in the dashboard
even though Alpaca had filled the order. Root cause: the original "fire-and-forget"
design had no sync mechanism back from Alpaca to Supabase.

**Changes**:
- `execution/alpaca_broker.py`: Renamed initial status `PENDING` → `SUBMITTED`
- `scripts/sync_alpaca_orders.py`: New standalone script — queries pending trades,
  checks Alpaca via `get_order_by_id()`, updates status
- `.github/workflows/sync-alpaca.yml`: Daily cron at 4pm ET + manual dispatch
- `TradesTable.tsx`: Handles both `PENDING` (legacy) and `SUBMITTED`
- `supabase/migrations/20260514000000_add_alpaca_filled_at_to_trades.sql`: New column
- `concepts/alpaca-order-sync.md`: New wiki page documenting the architecture

In-process polling was rejected because `asyncio.run()` cancels pending tasks
when the pipeline completes. The decoupled cron approach is simpler and more reliable.

## [2026-05-13] fix | Alpaca order status sync — decoupled cron job (SUBMITTED → FILLED)

Fixed the bug where `alpaca_status` permanently showed `PENDING` in the dashboard
even though Alpaca had filled the order. Root cause: the original "fire-and-forget"
design had no sync mechanism back from Alpaca to Supabase.

**Changes**:
- `execution/alpaca_broker.py`: Renamed initial status `PENDING` → `SUBMITTED`
- `scripts/sync_alpaca_orders.py`: New standalone script — queries pending trades,
  checks Alpaca via `get_order_by_id()`, updates status
- `.github/workflows/sync-alpaca.yml`: Daily cron at 4pm ET + manual dispatch
- `TradesTable.tsx`: Handles both `PENDING` (legacy) and `SUBMITTED`
- `supabase/migrations/20260514000000_add_alpaca_filled_at_to_trades.sql`: New column
- `concepts/alpaca-order-sync.md`: New wiki page documenting the architecture

In-process polling was rejected because `asyncio.run()` cancels pending tasks
when the pipeline completes. The decoupled cron approach is simpler and more reliable.

## [2026-05-13] refactor | Ruff + Biome linting: massive import sort and code style cleanup

Applied `ruff check --fix` (Python engine) and `pnpm biome check --fix` (TypeScript web + packages) across the entire monorepo. Changes are purely cosmetic: import reordering (isort), type annotation modernization (`Optional[X]` → `X | None`, `List[X]` → `list[X]`, `Dict[X,Y]` → `dict[X,Y]`), `datetime.timezone.utc` → `datetime.UTC`, f-string cleanup, whitespace normalization, and Biome formatting (4-space indent, single quotes, trailing commas). Added `ruff.toml` and `biome.json` config files. Added `ruff` to `requirements.txt` and `@biomejs/biome` to root `package.json`. Updated `.husky/pre-commit` to run both linters before tests. No behavioral changes.
