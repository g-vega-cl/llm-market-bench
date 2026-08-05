---
tags: [cron, cloudflare, edge, dispatch, github-actions]
category: entity
---

# Cron Dispatcher

The **Cron Dispatcher** is a Cloudflare Worker (`apps/cron-dispatcher`) that triggers GitHub Actions workflows via the GitHub REST API using high-precision edge cron triggers. It bypasses GitHub Actions' native scheduled event queue delays, launching workflows in under 5 seconds.

## Trigger Schedule

Defined in `wrangler.jsonc`:

- `0 13 * * MON-FRI` — Pre-market daily predictor (13:00 UTC / 9:00 AM EDT)
- `15 21 * * MON-FRI` — Evaluate daily predictions (21:15 UTC / 5:15 PM EDT)
- `0 22 * * SUN` — Weekly auto-research (22:00 UTC / 6:00 PM EDT)
- `0 22 * * WED` — Mid-week auto-research (22:00 UTC / 6:00 PM EDT)

## Dispatch Mechanism

The worker's `scheduled()` handler maps the UTC hour of `event.scheduledTime` to the appropriate workflow action (`daily-predictor`, `evaluate-daily-predictions`, or `daily-autoresearch`) and sends a `POST` to `https://api.github.com/repos/g-vega-cl/llm-market-bench/actions/workflows/daily-predictor.yml/dispatches` with a `GITHUB_PAT` bearer token.

A `fetch()` handler is also exposed for manual invocation: `GET /?action=<name>`.

## Market-Open Safety Guardrail

The dispatched `daily-predictor.yml` workflow includes a safety check in the `Determine command to run & verify safety window` step. If the `daily-predictor` command runs after 13:30 UTC (9:30 AM EDT market open) and before 20:00 UTC, the step sets `skip=true` and logs a warning — preventing stale intraday predictions from being recorded.

## Related

- [[entities/daily-market-predictor]] — Downstream prediction pipeline
- [[entities/autoresearch]] — Weekly prompt improvement loop
