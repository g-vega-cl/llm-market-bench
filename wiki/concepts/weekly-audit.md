---
tags: [audit, weekly, ingestion, consensus, sampling, log-analysis]
category: concept
---

# Weekly Ingestion & Consensus Audit

The weekly audit is a scheduled automatic analysis of recent ingestion and consensus pipeline runs to catch errors, anomalies, and data quality issues before they compound. It runs as part of the weekly Friday system audit and produces findings in both the database (`system_audits`) and CI logs.

## Sampling Strategy

To keep analysis cost and time bounded, the audit samples at most 3 logs from the past 7 days:

1. **Anchor**: The latest run (always included).
2. **Anomaly-prioritized**: Among remaining runs, those with highest anomaly scores (errors, tracebacks, SEMANTIC FRAGILITY alerts) are selected.
3. **Random fallback**: If fewer than 2 anomaly-rich runs exist, remaining slots are filled randomly.

The anomaly scorer (`_score_log_anomalies`) weights critical errors, tracebacks, and fragility alerts.

## Log Summarization

Each sampled log blob is condensed via `extract_log_summary` to at most 15,000 characters, preserving:
- Error tracebacks (fully included)
- Key markers (errors, warnings, fragility alerts, ingestion/consensus milestones)
- Stage metrics and completion lines

If the blob is already small, it is passed through unchanged.

## LLM Analysis

Summarized logs are sent to DeepSeek (via OpenRouter) with a structured prompt that asks for findings with `title`, `severity`, `suggestion`, and `run_id`. The model output is parsed as JSON. Stripping of `thinking` / `response` prefixes is applied.

## SQL Checks

In addition to log analysis, two new deterministic SQL checks run:

- **Empty Newsletter Snapshots**: Detects snapshots with content `< 50 characters` (HIGH severity).
- **Duplicate Consensus Event Memories**: Finds active `MARKET_EVENT` memories with identical `event_name` created within 7 days (HIGH severity).

## Output

- Findings are inserted into `system_audits` table with type `SYSTEM_LOG` or `SQL_CHECK`.
- A summary table is written to `GITHUB_STEP_SUMMARY` in CI (Markdown table with severity, title, run ID, suggestion).
- A `dry_run` mode prevents actual database inserts for validation.

## Retention

Ingestion logs are retained for 7 days (up from 48 hours) to support the weekly audit window.

## Related

- [[entities/cleanup]] — database maintenance and cleanup scheduling
- [[concepts/observability-standard]] — traceability and audit philosophy
- [[entities/engine]] — the pipeline that the audit monitors
