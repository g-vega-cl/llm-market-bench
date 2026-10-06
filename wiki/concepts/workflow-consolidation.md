---
tags: [ci, github-actions, cron, scheduling, conventions]
category: concept
---

# Workflow Consolidation & Piggybacking

A mandatory project convention for GitHub Actions: secondary or periodic tasks are
**piggybacked** onto existing scheduled workflows rather than given their own
workflow files. This keeps the CI surface small, avoids redundant runners, and
ties side tasks to a cadence that already makes sense (market close, price
update, ingest).

## The Rule

1. **Never create a standalone workflow** for a secondary or periodic task when an
existing scheduled pipeline already runs on the appropriate cadence.
2. **Prefer piggybacking** the task into an established workflow
   (`update-prices.yml`, `update-earnings-alpha.yml`, `ingest.yml`) as a distinct
   step or a chained script call.
3. **Only introduce a new workflow file** when the cadence, trigger event, or
   execution runner environment is genuinely decoupled and cannot be shared with
   any existing pipeline.

## Rationale

- **Cadence reuse** — the existing pipeline already fires at the right time
  (e.g. market close), so a duplicate schedule just adds noise and cost.
- **Single source of scheduling truth** — fewer cron entries means fewer places
  for drift, overlapping runs, or missed execution.
- **Lower runner cost** — one job that runs several steps is cheaper than several
  independent workflow dispatches.
- **Discoverability** — a new task lives next to the pipeline it depends on,
  where the surrounding context (secrets, environment, checkout) is already set
  up.

## Decision Checklist

Before adding a new workflow file, verify all of the following:

- No existing scheduled workflow fires on a matching cadence.
- The trigger event (push, schedule, dispatch) genuinely differs.
- The runner environment cannot be shared.

If any answer is "an existing workflow already covers this," piggyback instead.

## Related

- [[entities/engine]] — the pipeline who's stages the piggybacked tasks extend
- [[entities/cron-dispatcher]] — cron scheduling for the engine
- [[concepts/project-linting]] — CI quality gates that also run via hooks/workflows
