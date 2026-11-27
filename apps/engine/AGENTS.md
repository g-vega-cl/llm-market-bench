# Engine Rules (`apps/engine/AGENTS.md`)

Loaded progressively when working inside `apps/engine/` or backend workflows.

## Import Root & Working Directory Parity

- CI and test runners execute with `working-directory: apps/engine`.
- Import strictly relative to `apps/engine` (`from core.config import ...`, `from execution.portfolio import ...`). Never write `from apps.engine.` or `import apps.engine.` in production modules.
- Every subdirectory package under `apps/engine/` must include `__init__.py`.

## Tool-First, Agency-Driven Architecture (MANDATORY)

- **Autonomous Trading & Predictor Agents**: Never hardcode trading heuristics, ticker filters, or fixed tool-call sequences into baseline system prompts (`CORE_ANALYSIS_SYSTEM_PROMPT`, etc.).
- **Provide Tools, Not Data Dumps**: Expose new data sources as callable tools synchronized across all four locations:
  1. `packages/config/tools.json`
  2. `apps/engine/core/llm/tools.py`
  3. `apps/engine/autoresearch/program.md`
  4. `apps/engine/tests/test_tools_consistency.py`
- **Autoresearch Owns Prompt Evolution**: Prompt mutations belong strictly to the Autoresearcher loop (`PromptResearchResult`) and `apps/engine/autoresearch/prompt_blocks.py`. Deterministic editorial utilities (`cleaner.py`, `newsletter_generator.py`) may use direct prompts via `auto-go` (`[[concepts/auto-go-utility-llm]]`).
- **Hermetic Local Autoresearch**: Offline backtests and double-ratchet tournaments run 100% locally on Strata/Laya Qwen with zero cloud API fallbacks. `apps/engine/autoresearch/evaluator.py` and `apps/engine/local_autoresearch/single_prompt_ratchet.py` are protected Red-Line files: never modify them during routine coding tasks without explicit user approval.

## Financial, Timezone & API Invariants

- **Bounds & Error Handling**: Validate non-negative implied volatility, positive spot prices, valid option deltas, and explicit HTTP 401, 403, 429, and 400 handling. Never mix spot VIX with VIX futures ETFs.
- **Timezone & Calendar**: Never call naive `datetime.now()`. Localize market session, predictor, and point-in-time cutoffs (`09:15 ET` zero-lookahead contract) to `America/New_York` via `MarketCalendar`.
- **Order & Ledger Safety**: Keep ledger mutations idempotent (`ON CONFLICT` / idempotency keys), enforce FIFO lot matching, and prevent unintended short positions on exit `SELL` orders. Use Hypothesis property-based tests (`tests/test_portfolio_invariants_pbt.py`) when altering accounting or margin math.

## Database Migrations, Replica Cache & CI Secrets

- **RLS & Grants**: Every new table in `supabase/migrations/*.sql` must declare `ENABLE ROW LEVEL SECURITY` and explicit PostgREST `GRANT` statements (`tests/test_migration_grants.py`).
- **MiniPC Replica Reload (`PGRST205` Guard)**: Physical PostgreSQL streaming replication does not forward `NOTIFY pgrst, 'reload schema'`, while `docker/archive/nginx.secondary.conf` routes `GET` reads to MiniPC PostgREST. On `/ship` after any migration, run `./docker/archive/deploy_secondary.sh cv-minipc@minipc` to restart `archive-postgrest` and verify `200 OK` with zero `PGRST205` errors against `https://benchify-archive-db.clvg.uk`.
- **Workflow Secrets & Piggybacking**: Piggyback periodic tasks onto existing `.github/workflows/*.yml` files rather than adding standalone workflows, and inject all required secrets (`FMP_API_KEY`, `FRED_API_KEY`, `SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `FREE_LLM_PROXY_URL`, `FREE_PROXY_MASTER_KEY`, provider keys) in every `python main.py` step `env:` block.
