---
tags: [ingestion, dry-run, simulation, safety, pipeline]
category: concept
---

# Dry-Run Simulation Mode

End-to-end simulation mode for the ingestion pipeline. It runs the complete multi-model extraction → consensus → decision → execution path without placing any live orders or mutating production database tables, and without requiring US market hours. This lets developers and automated health checks exercise the full pipeline at night, on weekends, or on holidays.

## Invocation

- CLI: `python main.py ingest --dry-run` (see `apps/engine/main.py` → `run_ingest(force, dry_run)`)
- GitHub Actions: `Ingestion & Consensus` workflow (`github/workflows/ingest.yml`) exposes a `workflow_dispatch` boolean input `dry_run` that appends `--dry-run`. The same workflow also accepts a `force` input that appends `--force`; its job timeout is 45 minutes.

## Behavior

- **Market-hours bypass**: When `dry_run=True`, the `is_market_open_with_logging()` gate is skipped entirely (an alternate branch to `--force`), so the pipeline runs regardless of session status.
- **Snapshot fallback**: If no fresh Gmail newsletters have arrived, the ingestion stage falls back to the most recent records from the `newsletter_snapshots` Supabase table (latest 5, ordered by `received_at DESC`) to provide realistic inputs. Snapshot upserts are skipped.
- **Zero-mutation guardrails**: Pre-analysis dust cleanup, portfolio ledger mutations (`Portfolio.execute_trade`), Alpaca limit-order submissions, systematic weekly sector entry/exit hooks, the isolated LIN Renko flow, and daily performance/PCA snapshot stages are all skipped.
- **Mock decision attribution**: Signal attribution routes through an internal `_record_decision` helper that returns a mock decision ID (`"dry_run_decision_id"`) and logs `[DRY RUN]` simulated attribution instead of writing to the `decisions` table. Dry-run trades are tagged with status `EXECUTED_DRY_RUN` and `trade_id: "dry_run"`.
- **Logging**: Ingestion logs are not persisted to the `ingestion_logs` table; a summary of the captured log size is emitted instead.

## Verification

The mode is exercised by the hermetic test `apps/engine/tests/test_ingest_pipeline_optimizations.py::test_run_ingest_dry_run_bypasses_market_and_executes_no_trades`, which asserts the market check is not called, `execute_trade` is never invoked, and `save_decision` is never called. A live verification script lives at `apps/engine/scripts/dry_run_ingest_optimizations.py`.

## Related

- [[concepts/ingestion]]
- [[entities/pipeline]]
- [[entities/engine]]
