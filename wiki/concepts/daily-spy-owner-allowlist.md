---
tags: [daily-spy, allowlist, portfolio, execution, guardrail, config]
category: concept
---

# Daily SPY Owner Allowlist

The Daily SPY arena runs a fixed set of models. To prevent phantom portfolios, accidental trades, and audit mutations for retired or non-SPY models, the engine enforces a canonical allowlist of approved Daily SPY models and their derived portfolio owner IDs. The allowlist lives in `apps/engine/core/config.py` and is enforced at every portfolio creation, trade execution, reconciliation, price-marking, backfill, and audit entry point.

## Canonical Definitions

`apps/engine/core/config.py` exports:

- `ALLOWED_DAILY_SPY_MODELS` — the set of active Daily SPY arena model names (e.g. `deepseek-flash`, `MiniMax-M3.1-Flash`, `~typesafe/jev-latest`).
- `SYS_DAILY_SPY_OWNER_PREFIX = "sys-daily-spy-"` — owner prefix for target (directional) portfolios.
- `SYS_DAILY_SPY_CLOSE_OWNER_PREFIX = "sys-daily-spy-close-"` — owner prefix for close-exit portfolios.
- `is_allowed_daily_spy_model(model_name) -> bool` — true when the model is in the allowlist.
- `is_allowed_daily_spy_owner(owner_id) -> bool` — true when the owner ID is a well-formed `sys-daily-spy[-close]-<allowed-model>` string.
- `assert_allowed_daily_spy_owner(owner_id)` — raises `ValueError` for unapproved owners.
- `resolve_daily_spy_owners(model_name, expected_return_pct) -> set[str]` — resolves which owner IDs should be created/traded for a given model and prediction.

### Owner ID Format

Owners are `sys-daily-spy-{model}` (target) and `sys-daily-spy-close-{model}` (close). The allowlist rejects:

- Non-SPY arena models (e.g. `gpt-6-luna`, `laya-local-autoresearched`).
- Archived/retired models (e.g. `MiniMax-M3`, `deepseek-v4-flash`, `jev-four-regime-champion`).
- Whitespace-padded or malformed names (`" sys-daily-spy-..."`, `sys-daily-spy`, `sys-daily-spy2`).
- Empty/`None` owners.

Non-SPY system portfolios (TLT, Picks) are **not** subject to this guard — only `sys-daily-spy*` owners are validated.

## Enforcement Points

### Portfolio Creation

- `execution/daily_trading.py::_load_or_create_system_portfolio` calls `assert_allowed_daily_spy_owner(owner_id)` before initializing. `get_or_create_system_portfolio` wraps it.
- `execution/portfolio.py::Portfolio.initialize()` calls `assert_allowed_daily_spy_owner(self.owner_id)` when creating a new portfolio row.
- `execution/system_portfolios.py::get_or_create_system_portfolio` delegates to `_load_or_create_system_portfolio`, so mechanical portfolios inherit the same guard.

### Trade Execution

- `execution/daily_trading.py::execute_daily_spy_trade` skips non-SPY tickers and raises `ValueError` for unapproved owners, even when a custom `portfolio_getter` is injected. The model name is stripped before owner derivation.

### Reconciliation & Marking

- `execution/daily_reconciliation.py::reconcile_daily_open_trades` filters portfolios through `is_allowed_daily_spy_owner`.
- `scripts/update_prices.py::_fetch_portfolio_owners` excludes archived owners and unapproved `sys-daily-spy*` owners from price marking.

### Backfill & Evaluation

- `tasks/backfill_daily_close_portfolios.py` queries only `ALLOWED_DAILY_SPY_MODELS` (via `.in_`) and filters models whose close owner is allowed. It selects a fixed `_BACKFILL_COLUMNS` projection instead of `*`.
- `tasks/evaluate_daily_predictions.py::_backfill_daily_prediction_trades` skips non-SPY models via `is_allowed_daily_spy_model` and uses `resolve_daily_spy_owners` to decide which target/close trades to run.

### Auditing

- `audit/portfolio_auditor.py::audit_system_portfolios` skips archived and non-SPY `sys-daily-spy*` portfolios, leaving them untouched.

## Why It Matters

Without the allowlist, retired models (e.g. `MiniMax-M3`, `jev-four-regime-champion`) and non-SPY arena models (e.g. `gpt-6-luna`) could spawn phantom portfolios from stale `daily_predictions` rows, receive price marks, or be mutated by the auditor. The allowlist centralizes "who is allowed to trade the Daily SPY arena" in one place so every subsystem agrees.

## Related

- [[concepts/daily-spy-live-trading]] — the Daily SPY live trading pipeline
- [[concepts/execution]] — execution and settlement
- [[concepts/system-portfolios]] — mechanical system portfolios
- [[entities/portfolio-auditor]] — portfolio audit and auto-heal
- [[entities/daily-market-predictor]] — daily prediction arena
