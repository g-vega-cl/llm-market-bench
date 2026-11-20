---
tags: [concept, backtesting, database, simulation, sandbox]
category: concept
---

# Temporal Sandboxing & Backtesting Simulation

The temporal database sandboxing system enables full walk-forward simulation of model portfolios (e.g., Gemini, DeepSeek, MiniMax) without modifying historical database state, colliding with live execution environments, or leaking future data.

## Architecture

During backtest simulation, the engine executes sequential ticks simulating historical points in time ($t_{\text{sim}}$). To isolate database access, all queries to the database are wrapped in a simulated Point-in-Time database client.

```mermaid
graph TD
    A[Engine Execution Loop] --> B[MockSimulatedSupabaseClient]
    B --> C{Table Type}
    C -->|Local State| D[SQLiteTable & SQLiteQueryBuilder]
    C -->|Read-Only Data| E[TemporalQueryBuilderWrapper]
    D --> F[Local Cache: .backtest_portfolios.db]
    E -->|LTE t_sim Constraint| G[Remote Supabase API]
```

### 1. Dynamic Namespace Attribute Patching
Standard module-level mock patches fail when target files import functions (like `get_supabase_client`) at import time using `from core.db import get_supabase_client`. To prevent queries from bypassing the mock, `global_supabase_patch(mock_sync, mock_async)` dynamically inspects all modules loaded in `sys.modules` at runtime and overwrites the bindings to the mock client, ensuring complete, leakproof query redirection.

### 2. Unified SQLite Mock Query Builder
Local portfolio operations, trades ledging, and decision audits are redirected to a local SQLite database (`.backtest_portfolios.db`). The mock query builder (`SQLiteQueryBuilder`) provides a unified, chainable interface supporting `SELECT`, `UPDATE`, and `DELETE` actions, alongside standard postgrest-py operators:
* `.eq()`, `.neq()`, `.gt()`, `.gte()`, `.lt()`, `.lte()`, `.in_()`, `.match()`
* `.order()`, `.limit()`, and `.maybe_single()`
* Supports variable arguments inside `select(*args)` by joining inputs into a comma-separated select filter string.

### 3. Point-in-Time Data Sandboxing & Redirection
To ensure complete isolation of the simulated environment:
* **Redirection of Price Caching**: Large price cache tables (`price_history` and `market_data_cache`) are redirected to the local SQLite database. This eliminates network roundtrip times, prevents remote 504 Gateway Timeout errors, and shields production data.
* **Redirection of Performance Logs**: To prevent backtest runs from contaminating the production database performance history (which breaks frontend chart visualization), `portfolio_performance` daily snapshots are redirected to the local SQLite database.
* **Local `position_pnl` VIEW**: The portfolio ledger computes positions and unrealized PnL using the database. Since positions are local to the backtest run, `position_pnl` is recreated in SQLite as a local view. This view dynamically joins `portfolios`, `portfolio_positions`, and the local `market_data_cache`, ensuring that LLM verifiers evaluate compliance using correct point-in-time mock portfolios.
* **Simulated `"now()"` Time Substitution**: Simulated mock writes (`SQLiteInsertBuilder`) substitute Postgres server-side `"now()"` literals with the exact ISO-formatted simulated date-time ($t_{\text{sim}}$). This enables correct calculations of trade age relative to the simulation clock.
* **Equity-Based Return Calculations**: Weekly backtest evaluation calculates returns using `total_equity` (which incorporates the current value of held positions) rather than `cash_balance` (which was negative due to margin loans). This correctly aligns simulated performance with the actual growth of the accounts.

### 4. Live Account Mirror Prevention
Backtesting executes mock trades using actual simulated pricing. To prevent these trades from being mirrored to the live third-party broker (Alpaca paper endpoint), the execution is configured with `skip_alpaca_mirror=True`. This prevents API authentication or buying power errors and guarantees that backtest runs are entirely mock-only.

### 5. Offline RPC Sandbox (`apps/engine/tasks/backtest_sandbox_rpc.py`)

`MockSimulatedSupabaseClient.rpc()` no longer proxies arbitrary RPCs to the real client. Every RPC call is routed through the offline sandbox module, which either executes locally in SQLite or fails closed:

* **`execute_portfolio_trade` runs locally in SQLite** — `execute_sqlite_portfolio_trade(params, t_sim, db_path)` reproduces the PostgreSQL RPC contract inside a single `BEGIN IMMEDIATE` transaction: it reads the locked `portfolios` row, validates ticker/signal/quantity/price, applies the BUY/SELL to `portfolio_positions` (weighted-average cost basis on adds, `LEAST(p_quantity, held)` capping and `realized_pnl` on sells), inserts the `trades` ledger row, and derives the cash-only metrics (`cash_balance`, `sma`, `total_equity`, `buying_power`, `excess_liquidity`, `maintenance_margin = 0`, `realized`) from the post-trade position set. Any exception rolls back and re-raises, so a simulated trade is all-or-nothing exactly like production. See [[concepts/atomic-trade-execution]].
* **Idempotent replay** — `_replay_sqlite_trade` looks up `trades.idempotency_key`; a matching replay returns the original `trade_id` with `idempotent_replay: true` and writes nothing, while a key already used by a different portfolio/ticker raises `Idempotency key … already used by another trade`. `init_backtest_db()` adds `idempotency_key TEXT UNIQUE` to the local `trades` schema.
* **Simulated timestamps** — `executed_at` and `last_updated_at` are written as the ISO-formatted $t_{\text{sim}}$ (falling back to `datetime.now(UTC)` when no simulation clock is supplied), never as `now()`.
* **Allowlisted read-only RPCs only** — `build_temporal_rpc_wrapper` accepts only `match_memories` and `match_decisions` (`ALLOWED_TEMPORAL_RPCS`). Any other RPC raises `ValueError("RPC '<name>' is not allowlisted in offline backtest sandbox")`, so a backtest can never mutate production state through an unmodelled RPC.
* **Point-in-time filtering** — `_filter_temporal_rpc_rows` drops any returned row whose `created_at` is after $t_{\text{sim}}$, preserving the no-lookahead guarantee for semantic retrieval.
* **Small, testable helpers** — the module is decomposed into `_apply_sqlite_buy`, `_apply_sqlite_sell`, `_compute_sqlite_equity`, `_replay_sqlite_trade`, and `_filter_temporal_rpc_rows`, each kept at or below a cyclomatic complexity of 6.

## Related

- [[entities/autoresearch]] — Karpathy-style autonomous prompt improvement loop
- [[concepts/execution]] — Pre-market validation, Reg T checks, trade settlement
- [[concepts/atomic-trade-execution]] — the production RPC this sandbox mirrors
- [[sources/reg-t-calculations-source]] — Margin account formulas & guardrails
