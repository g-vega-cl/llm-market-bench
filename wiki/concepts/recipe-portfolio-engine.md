---
tags: [recipes, execution, portfolio, sizing, alpaca, broker, slippage]
category: concept
---

# Recipe Portfolio Engine

`apps/engine/recipes/portfolio_engine.py` is the single Long-Only portfolio stepper behind both `live_turn` execution and the point-in-time backtest of a Push v2 strategy recipe. `PortfolioState` is hydrated from the `strategy_recipes` JSON columns (`paper_cash`, `paper_positions`, `paper_trades`, `paper_equity_curve`), stepped by `apply_portfolio_step()`, and written back by the recipe worker.

## Sizing Rules

- Exits run before entries, so cash freed in a turn is reusable in the same turn. Each leg is capped at `max_equity_pct_per_trade` percent of **pre-step** equity (default 25%) and by available cash, floored to `_MIN_TRADE_NOTIONAL` ($10).
- **Whole shares only.** `shares = int(alloc // (entry_px * (1 + slippage_bps/10000)))`. The `cost_basis` charged to cash is the actual spend (`shares * entry_px * (1 + slip)`), never the full notional allocation, so cash never leaks when a leg rounds down. A leg whose allocation cannot buy one share records an `ALLOCATION_BELOW_ONE_SHARE` skip instead of rounding up past the cap.
- Because `apply_portfolio_step()` serves live and simulated modes alike, a sizing change also rewrites historical backtest numbers; there is deliberately no live-only flag that would let the two ledgers disagree.
- Every open position carries `shares`, `entry_price`, `entry_time`, and `cost_basis`; `enrich_open_positions()` adds mark price, market value, and net-of-slippage unrealized P&L for the web and prompt blocks. Legacy rows created before the whole-share rule can still hold fractional `shares` (e.g. `20.474849`); they exit normally and are displayed trimmed rather than rewritten.
- **Prompt rendering (`_format_shares`)** — `format_portfolio_prompt_block()` renders whole-share positions as bare integers (`NVDA: 25 shares`) and keeps legacy fractional rows readable at up to 4dp (`DIS: 20.4748 shares`), so the injected `[Current Portfolio State]` block never shows a misleading `25.0000`.

## Alpaca Mirror

`apps/engine/recipes/alpaca_mirror.py` mirrors live-turn fills to the shared Alpaca paper account. `position_snapshot()`/`compute_fills()` diff the book before and after `apply_portfolio_step()` (the step's `executed_signals` carry no share count), then `mirror_recipe_fills()` submits DAY market orders tagged `recipe-<id8>__<TICKER>__<BUY|SELL>__<slot UTC>`.

Guardrails, because one paper account aggregates every strategy (recipe mirrors, `sys-*` portfolios, the live SPY trader):

- SELL legs are capped to the shares Alpaca actually holds and are marked `SKIPPED_NO_POSITION` when the broker is flat for that ticker.
- Mirroring is fire-and-forget: a broker error logs and records `alpaca_status = "ERROR"`, never blocks or fails the Supabase ledger write.
- Order metadata (`alpaca_status`, `alpaca_order_id`, `alpaca_submitted_at`) is stamped onto the open position or closed trade dict inside the JSON columns by `record_mirror_status()` — no migration and therefore no edge-replica parity deploy.
- Every live recipe is mirrored independently, so two live recipes holding the same ticker send two legs into the account; the broker position is their aggregate.

`run_push_live()` snapshots positions before the step, calls `mirror_recipe_fills()`, stamps results via `record_mirror_status()`, and returns the per-fill outcome list as `alpaca_fills` on the live result alongside `executed_signals` and `updated_portfolio`. `_build_client()` returns `None` when `ALPACA_ENABLED` is false or credentials are absent, so the mirror is inert in unconfigured environments.

### Test Guard

`apps/engine/recipes/conftest.py` installs an autouse `_no_live_alpaca_broker` fixture that monkeypatches `alpaca_mirror._build_client` to return `None`, so a live-turn unit test never builds a real `TradingClient` and attempts an outbound HTTP call against the paper credentials shipped in the engine `.env`. Tests that assert on the mirror pass their own fake client explicitly.

## Related

- [[entities/recipe-live-status]]
- [[entities/recipe-studio]]
- [[concepts/alpaca-order-sync]]
