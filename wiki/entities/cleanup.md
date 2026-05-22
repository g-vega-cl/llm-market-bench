---
tags: [database, maintenance, cleanup]
category: entity
---

# Database Cleanup

The database cleanup module (`core/cleanup.py`) provides a reusable, testable function for periodic database maintenance. It is invoked via the `cleanup` command in `main.py` and replaces the inline cleanup script previously embedded in the CI workflow.

## Schedule & Lifecycle

The cleanup module is tightly coupled with the system's weekly audit cycle:
- **Trigger**: Runs automatically every Friday at 16:00 EST (21:00 UTC) as the final step of the `System Audit` (`audit.yml`) GitHub Actions workflow.
- **Workflow Pipeline**: The workflow first executes `python main.py audit` to analyze logs and flag any system or model anomalies. Immediately following the audit step, it triggers `python main.py cleanup` to prune expired or resolved data.

## Retention Policy & Database Operations

The `run_cleanup()` function in `apps/engine/core/cleanup.py` connects to Supabase using a service role client and executes direct, interval-based PostgreSQL deletions to maintain optimum table performance and indexing speed:

1. **Ingestion Logs (`ingestion_logs` table)**:
   - **Retention**: 48 hours
   - **Operator**: `.delete().lt("created_at", 'now() - interval "48 hours"')`
   - **Rationale**: Keeps the ingestion stream log table compact to speed up metadata indexing and JIT parsing during the daily run.
2. **Resolved/Ignored System Audits (`system_audits` table)**:
   - **Retention**: 30 days
   - **Operator**: `.delete().in_("status", ["RESOLVED", "IGNORED"]).lt("created_at", 'now() - interval "30 days"')`
   - **Rationale**: Purges historical audit records that have been explicitly marked as closed (`RESOLVED` or `IGNORED`), while **permanently preserving open/active audits** for ongoing developer attention.
3. **Market Feeling Records (`market_feeling` table)**:
   - **Retention**: 30 days
   - **Operator**: `.delete().lt("created_at", 'now() - interval "30 days"')`
   - **Rationale**: Purges outdated market sentiment and classification logs that are older than 30 days, as trailing analysis displays only require recent metrics.

## Usage

```sh
python main.py cleanup
```

## Related

- [[entities/engine]]
- [[concepts/observability-standard]]
