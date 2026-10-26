---
tags: [engine, tooling, portfolio, reset, operations]
category: entity
---

# Reset State Script

`apps/engine/scripts/reset_state.py` wipes portfolio state and historical trade records so a benchmark run can restart from a clean slate. It is an operational tool, not part of the daily pipeline.

## Scope Selection

By default the script resets **only LLM portfolios** — any `portfolios` row whose `owner_id` does not start with `sys-`. Mechanical benchmark strategies (`sys-sector-*`, `sys-daily-spy-*`, `sys-max-pain`, `sys-pead-drift`, `sys-future-forces`, `sys-frontier-tech`, `sys-smid-quality-compounder`, …) are preserved so their live track records survive an LLM-side reset.

Passing `--all` resets every portfolio, including the system strategies.

```sh
# Reset LLM portfolios only (default)
./apps/engine/.venv/bin/python3 apps/engine/scripts/reset_state.py

# Reset every portfolio, including mechanical benchmarks
./apps/engine/.venv/bin/python3 apps/engine/scripts/reset_state.py --all
```

## What It Deletes

For the selected portfolio set:

1. **`decisions`** — scoped by `model_name` when running LLM-only, otherwise a full-table delete.
2. **`trades`** — scoped by `portfolio_id`.
3. **`portfolio_positions`** — scoped by `portfolio_id`.
4. **`portfolio_performance`** — scoped by `portfolio_id`.

## What It Writes

Each targeted portfolio row is reset to the Cash-Only default state:

| Column | Value |
| :--- | :--- |
| `cash_balance` | `10000.00` |
| `total_equity` | `10000.00` |
| `buying_power` | `10000.00` (equal to cash — no leverage) |
| `excess_liquidity` | `10000.00` |
| `maintenance_margin` | `0.0` |
| `sma` | `10000.00` |
| `realized` | `10000.00` |
| `last_updated_at` | `now()` |

See [[concepts/execution]] for the Cash-Only account model and [[concepts/portfolio-metrics-initialization]] for how these metrics are derived on load.

## Tests

`apps/engine/tests/test_reset_state.py` asserts that `reset_database(llm_only=True)` skips `sys-` portfolios and writes `buying_power == 10000.00` (not the legacy 4× cash value).

## Related

- [[concepts/execution]] — Cash-Only trade capacity and guardrails
- [[concepts/portfolio-metrics-initialization]] — metric derivation on portfolio creation
- [[concepts/system-portfolios]] — the mechanical strategies preserved by the default reset
- [[entities/engine]] — the engine hosting the script
