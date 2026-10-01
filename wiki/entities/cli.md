---
tags: [cli, entry-point, routing, engine]
category: entity
---

# CLI Package

The `apps/engine/cli/` package is the command-line interface layer for the engine. It was extracted from the former monolithic `apps/engine/main.py` (which had grown past 1,200 LOC) so that argument parsing, command routing, and domain dispatch live in small, isolated vertical slices. `main.py` is now a thin entry point (< 150 LOC) that simply calls `run_cli()`.

## Structure

| Module | Responsibility |
| :--- | :--- |
| `cli/parser.py` | `build_parser()` — the single argparse schema. Declares the `command` positional (all 26 `COMMAND_*` choices) and every shared flag (`--dry-run`, `--force`, `--track-id`, `--model`, `--action`, `--timeframe`, `--situation`, etc.). |
| `cli/router.py` | `DISPATCH_MAP` maps each command constant to its handler; `dispatch(args)` looks up and invokes the handler; `run_cli(args_list)` is the top-level entry point that parses then dispatches. |
| `cli/ingest.py` | Ingestion, calendar, government, cause-and-effect, post-analysis, and LIN Renko handlers. |
| `cli/predictions.py` | Daily predictor, prediction evaluation, daily/gainers postmortems, newsletter generation, and historical analog research. |
| `cli/trading.py` | Sector rotation, daily SPY MOO/target/close trades, Frontier Tech, and Future Forces thematic portfolios. |
| `cli/autoresearch.py` | Continuous autoresearch loops, bootstrap, daily autoresearch, and multi-week backtests. |
| `cli/audit.py` | Pipeline integrity audit, Alpaca reconciliation, portfolio audit, and database cleanup. |

## Dispatch Flow

1. `run_cli()` builds the parser and parses `sys.argv` (or an explicit arg list).
2. `dispatch(args)` looks up `args.command` in `DISPATCH_MAP`.
3. The matched handler lazily imports its domain module and runs it via `asyncio.run(...)`. Unknown commands raise `ValueError`.

Handlers import their heavy dependencies lazily (inside the function body) so that unrelated commands do not pay the import cost and so tests can patch the domain modules directly.

## Design Notes

- Each router file is kept under 200 LOC, enforced by `apps/engine/tests/test_cli_decomposition.py`.
- `DISPATCH_MAP` completeness against all `COMMAND_*` constants is asserted by the same test suite.
- The `--action` flag is shared across `sector-trade` and `daily-trade`; `daily-trade` routes `entry`/`open`, `target-orders`, and `exit`/`close` to distinct execution functions.

## Related

- [[entities/engine]] — the engine as a whole
- [[entities/pipeline]] — the orchestration layer the CLI dispatches into
- [[concepts/vertical-slice-islands]] — the decomposition principle behind this package
