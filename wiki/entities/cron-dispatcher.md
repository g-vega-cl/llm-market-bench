---
tags: [cron, dispatcher, edge, cloudflare, github-actions, multi-workflow]
category: entity
---

# Cron Dispatcher

The **Cron Dispatcher** is a Cloudflare Worker that provides high-precision, edge-native scheduling for GitHub Actions workflows. It replaces GitHub's built-in scheduler (which suffers from queue delays and reliability issues) with on-demand `workflow_dispatch` API calls, ensuring sub-5-second dispatch latency.

## Multi-Workflow Routing

The dispatcher supports multiple workflows beyond `daily-predictor.yml`. It evaluates the scheduled timestamp against the **`America/New_York`** local timezone via `getNewYorkTime()` before routing targets. This prevents duplicate executions when `wrangler.jsonc` exposes dual UTC cron hours to cover both EDT (UTC-4) and EST (UTC-5) seasonal shifts.

### Scheduled Time to Workflow Mapping

| UTC Time | ET Time (EDT / EST) | Minute | Workflow File | Inputs |
|----------|----------------------|--------|---------------|--------|
| 13:00 / 14:00 | 9:00 AM ET | 0 | `daily-predictor.yml` & `generate-newsletter.yml` | `{"action": "daily-predictor"}` / `{"session": "open"}` |
| 13:35, 14:35, 15:35, 16:35 | 9:35, 11:35 AM ET | 35 | `ingest.yml` | none |
| 19:30 / 20:30 | 3:30 PM ET | 30 | `ingest.yml` | none |
| 21:00 / 22:00 | 5:00 PM ET | 0 | `generate-newsletter.yml` | `{"session": "close"}` |
| 21:15 | 5:15 PM ET | 15 | `daily-predictor.yml` | `{"action": "evaluate-daily-predictions"}` |
| 22:00 (Sun & Wed) | 6:00 PM ET (Sun & Wed) | 0 | `daily-predictor.yml` | `{"action": "daily-autoresearch"}` |

## Cron Triggers (wrangler.jsonc)

The Worker exposes these edge cron expressions:

- `0 13,14,18,19,21,22 * * MON-FRI` — 9:00 AM, 5:00 PM ET (EDT & EST offsets for daily-predictor, generate-newsletter)
- `35 13-16 * * MON-FRI` — 9:35, 11:35 AM ET (ingest)
- `30 19,20 * * MON-FRI` — 3:30 PM ET (ingest)
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
## Deployment & Operational Protocol

> [!IMPORTANT]
> Modifying `apps/cron-dispatcher/` code (e.g., `src/index.ts` or `wrangler.jsonc`) in Git does **NOT** automatically deploy worker changes to Cloudflare. Whenever Cloudflare Worker code or cron schedules are updated, you MUST deploy the changes using `wrangler deploy`.

### Deployment Command

```bash
cd apps/cron-dispatcher
npx wrangler deploy
```

### Inspecting Active Deployments

To list deployment history and verify the active version timestamp on Cloudflare:

```bash
cd apps/cron-dispatcher
npx wrangler deployments list
```

## Related

- [[entities/daily-market-predictor]] — predictions and evaluation workflow
- [[concepts/ingestion]] — ingest workflow and timing
- [[entities/pipeline]] — full pipeline overview
- [[concepts/execution]] — execution phase
- [[entities/web-app]] — dashboard
