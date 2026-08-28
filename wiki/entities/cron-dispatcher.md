---
tags: [cron, dispatcher, edge, cloudflare, github-actions, multi-workflow]
category: entity
---

# Cron Dispatcher

The **Cron Dispatcher** is a Cloudflare Worker that provides high-precision, edge-native scheduling for GitHub Actions workflows. It replaces GitHub's built-in scheduler (which suffers from queue delays and reliability issues) with on-demand `workflow_dispatch` API calls, ensuring sub-5-second dispatch latency.

## Multi-Workflow Routing

The dispatcher supports multiple workflows beyond `daily-predictor.yml`. It evaluates the scheduled timestamp against the **`America/New_York`** local timezone via `getNewYorkTime()` before routing targets. This prevents duplicate executions when `wrangler.jsonc` exposes dual UTC cron hours to cover both EDT (UTC-4) and EST (UTC-5) seasonal shifts.

### Scheduled Time to Workflow Mapping

| UTC Time | ET Time (EDT / EST) | Minute | Workflow File | Inputs | Downstream Chaining |
|----------|----------------------|--------|---------------|--------|---------------------|
| 13:12 / 14:12 | 9:12 AM ET | 12 | `generate-newsletter.yml` | `{"session": "open"}` | Triggers `daily-predictor.yml` (`daily-predictor`) on completion |
| 13:35, 14:35, 15:35, 16:35 | 9:35, 11:35 AM ET | 35 | `ingest.yml` | none | None |
| 19:30 / 20:30 | 3:30 PM ET | 30 | `ingest.yml` | none | None |
| 21:00 / 22:00 | 5:00 PM ET | 0 | `generate-newsletter.yml` | `{"session": "close"}` | Triggers `daily-predictor.yml` (`evaluate-daily-predictions`) on completion |

> [!NOTE]
> All weekly and weekend auto-research tasks (Sunday & Wednesday 6:00 PM ET prompt autoresearch, Sunday macro autoresearch) run natively via GitHub Actions schedules (`daily-predictor.yml` and `autoresearch.yml`), decoupling background research jobs from Cloudflare edge triggers.

## Cron Triggers (wrangler.jsonc)

The Worker exposes 4 consolidated edge cron expressions (respecting Cloudflare Free plan's 5 cron trigger limit):

- `12 13,14 * * MON-FRI` — 9:12 AM ET (generate-newsletter open -> chains daily-predictor)
- `35 13-16 * * MON-FRI` — 9:35, 11:35 AM ET (ingest)
- `30 19,20 * * MON-FRI` — 3:30 PM ET (ingest)
- `0 21,22 * * MON-FRI` — 5:00 PM ET (market close newsletter -> chains evaluate-daily-predictions)

## Dispatch Request Structure

`dispatchWorkflow(target: DispatchTarget, env: Env)` constructs a `POST` to `https://api.github.com/repos/g-vega-cl/llm-market-bench/actions/workflows/{target.workflowFile}/dispatches` with a JSON body containing `ref: 'main'` and optional `inputs`.

### Retry Resilience
To prevent failures from transient network drops, rate-limiting, or temporary GitHub API downtime, `dispatchWorkflow` implements a retry loop:
- **Max Attempts**: 3
- **Backoff**: Exponential backoff with a base of 1 second (`1000ms * attempt` delay between retries)
- **Silent Failures Prevention**: If all 3 attempts fail, the worker logs the errors and throws an unhandled exception, ensuring visibility in the Cloudflare Worker console.

### Fetch Endpoint

When accessed via HTTP, the Worker accepts query parameters:

- `action` — maps to `inputs.action` for `daily-predictor.yml` (default `'daily-predictor'`)
- `target` or `workflow` — if set to `'ingest'` or `'ingest.yml'`, dispatches `ingest.yml` directly with no inputs.
- Returns JSON with dispatched workflow file name, inputs (if any), and status.

- **Edge Reliability**: Cloudflare Workers run globally with minimal cold start.

## Workflow Secrets & Environment Variables Protocol

Every GitHub Actions workflow YAML targeted by the dispatcher (`.github/workflows/*.yml`) executing python commands must explicitly declare all required runtime environment variables and secrets in its step `env:` block. For example:
- Financial & Macro Data: `FMP_API_KEY`, `FRED_API_KEY`
- Database: `SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- LLM Providers: `DEEPSEEK_API_KEY`, `MINIMAX_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`

Omitting API keys like `FMP_API_KEY` in workflow YAMLs causes live pre-market price quotes, gap analysis, and market data queries to fail silently on CI runners.

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
