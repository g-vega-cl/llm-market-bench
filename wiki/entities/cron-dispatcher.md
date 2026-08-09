---
tags: [cron, dispatcher, edge, cloudflare, github-actions, multi-workflow]
category: entity
---

# Cron Dispatcher

The **Cron Dispatcher** is a Cloudflare Worker that provides high-precision, edge-native scheduling for GitHub Actions workflows. It replaces GitHub's built-in scheduler (which suffers from queue delays and reliability issues) with on-demand `workflow_dispatch` API calls, ensuring sub-5-second dispatch latency.

## Multi-Workflow Routing

The dispatcher now supports multiple workflows beyond `daily-predictor.yml`. It routes based on the scheduled time via a `resolveScheduledTarget()` function, supporting both `ingest.yml` and `daily-predictor.yml` with specific input actions.

### Scheduled Time to Workflow Mapping

| UTC Time | ET Time | Minute | Workflow File | Inputs |
|----------|---------|--------|---------------|--------|
| 13:00 | 9:00 AM | 0 | `daily-predictor.yml` & `generate-newsletter.yml` | `{"action": "daily-predictor"}` / `{"session": "open"}` |
| 13:35, 14:35, 15:35 | 9:35, 10:35, 11:35 AM | 35 | `ingest.yml` | none |
| 18:00 | 2:00 PM | 0 | `ingest.yml` | none |
| 21:00 | 5:00 PM | 0 | `generate-newsletter.yml` | `{"session": "close"}` |
| 21:15 | 5:15 PM | 15 | `daily-predictor.yml` | `{"action": "evaluate-daily-predictions"}` |
| 22:00 (Sun & Wed) | 6:00 PM (Sun & Wed) | 0 | `daily-predictor.yml` | `{"action": "daily-autoresearch"}` |

## Cron Triggers (wrangler.jsonc)

The Worker exposes these cron expressions:

- `0 13,18,21 * * MON-FRI` — 9:00 AM, 2:00 PM, 5:00 PM ET (daily-predictor, ingest, generate-newsletter)
- `35 13-15 * * MON-FRI` — 9:35, 10:35, 11:35 AM ET (ingest)
- `15 21 * * MON-FRI` — 5:15 PM ET (evaluate daily predictions)
- `0 22 * * SUN,WED` — 6:00 PM ET (daily-autoresearch on Sundays and Wednesdays)

## Dispatch Request Structure

`dispatchWorkflow(target: DispatchTarget, env: Env)` constructs a `POST` to `https://api.github.com/repos/g-vega-cl/llm-market-bench/actions/workflows/{target.workflowFile}/dispatches` with a JSON body containing `ref: 'main'` and optional `inputs`.

### Fetch Endpoint

When accessed via HTTP, the Worker accepts query parameters:

- `action` — maps to `inputs.action` for `daily-predictor.yml` (default `'daily-predictor'`)
- `target` or `workflow` — if set to `'ingest'` or `'ingest.yml'`, dispatches `ingest.yml` directly with no inputs.
- Returns JSON with dispatched workflow file name, inputs (if any), and status.

## Architecture Benefits

- **Eliminates Queue Bottlenecks**: No wait for GitHub-provided scheduler queuing; workflow is triggered instantly via API.
- **Edge Reliability**: Cloudflare Workers run globally with minimal cold start.
- **Precise Timing**: Sub-5-second dispatch latency ensures time-sensitive market hour operations fire on time.
- **Single Point of Management**: All scheduled workflows (prediction, ingest, evaluation, autoresearch) are controlled by one Worker with clear routing rules.

## Related

- [[entities/daily-market-predictor]] — predictions and evaluation workflow
- [[concepts/ingestion]] — ingest workflow and timing
- [[entities/pipeline]] — full pipeline overview
- [[concepts/execution]] — execution phase
- [[entities/web-app]] — dashboard
