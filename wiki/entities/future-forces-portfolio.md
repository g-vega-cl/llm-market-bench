---
tags: [entity, portfolio, future-forces, task]
category: entity
---

# Future Forces Portfolio

The Future Forces Portfolio is a system-managed portfolio that invests against long-horizon structural trends ("future forces" such as Autonomous Defense or energy transition) mapped to candidate tickers. Its periodic rebalance is driven by `run_future_forces_task` in `apps/engine/tasks/future_forces_task.py`.

## Task Flow

`run_future_forces_task` loads the active forces from Supabase (falling back to `DEFAULT_FUTURE_FORCES` when none are active), gathers quotes for the candidate tickers, evaluates existing holdings for exit, and computes rebalance orders via `compute_future_forces_rebalance_orders`. In live mode it executes the resulting buys/sells through the portfolio's `execute_trade`.

## Holdings & Quote Resolution

The task builds `current_holdings` from `portfolio.positions`, which may hold either `Position` dataclass instances or plain dicts. Ticker, quantity, and average cost basis are read with `getattr` and a dict fallback, so both representations are handled uniformly. Only positions with a positive quantity are treated as holdings.

Before evaluation, the task fetches live quotes for every candidate ticker **and** every existing holding ticker, deduplicated by an uppercased ticker key. Each holding's `current_price` is resolved in priority order: live quote price → `average_cost_basis` → `100.0` fallback. This keeps exit evaluation and rebalance math grounded in current market prices rather than stale cost basis.

## Tools

Autonomous agents inspect and stress-test the strategy through two canonical pull tools:

- `get_future_forces`: Deterministic query for active forces across horizons and archetypes.
- `research_future_force`: Adversarial research tool using `gpt-5.6-luna` with thinking.

## Related

- [[entities/pipeline]]
- [[entities/engine]]
- [[concepts/future-forces]]
- [[concepts/execution]]
