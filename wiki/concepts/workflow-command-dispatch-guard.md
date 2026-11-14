---
tags: [ci, github-actions, workflow, dispatch, idempotency, daily-predictor]
category: concept
---

# Workflow Command Dispatch Guard

`.github/workflows/daily-predictor.yml` is a single consolidated workflow that serves many `workflow_dispatch` actions (the `action` input). One generic step — **Run Daily Predictor Command** — executes `main.py ${{ steps.cmd.outputs.command }}` for whatever action was dispatched. Because the workflow also contains dedicated steps for other actions (stock picker, sector predictors, audits, etc.), an ungated generic step would re-run the dispatched command a second time. The **dispatch guard** is the explicit `if:` allow-list that restricts the generic step to the commands it is actually responsible for.

## The Guard

The step only runs when the resolved command is one of five values:

```yaml
- name: Run Daily Predictor Command
  if: >-
    steps.cmd.outputs.skip != 'true' && (
      steps.cmd.outputs.command == 'daily-predictor' ||
      steps.cmd.outputs.command == 'evaluate-daily-predictions' ||
      steps.cmd.outputs.command == 'daily-autoresearch' ||
      steps.cmd.outputs.command == 'daily-postmortem' ||
      steps.cmd.outputs.command == 'daily-trade'
    )
```

- `daily-predictor` — morning prediction generation.
- `evaluate-daily-predictions` — post-close evaluation of the day's predictions.
- `daily-autoresearch` — weekly prompt ratchet for the daily predictor.
- `daily-postmortem` — post-close diagnosis and memory feedback (see [[entities/daily-postmortem]]).
- `daily-trade` — systematic SPY/TLT entry and exit legs (see [[concepts/daily-spy-live-trading]] and [[entities/daily-bond-trading]]).

Every other dispatched action is handled exclusively by its own named step, so it is never executed twice.

## Fail-Safe Semantics

An action that is **not** in the allow-list evaluates the guard to `false`, so the generic step is skipped rather than falling through to an unintended `main.py <command>` invocation. This makes the workflow safe to extend: adding a new `action` option without touching the guard can never cause the generic step to run an unknown command — it simply does nothing there, and the new action's own step owns the execution.

## Enforcement Test

`apps/engine/tests/test_workflow_schedule.py::test_daily_predictor_no_duplicate_subcommand_execution` parses `daily-predictor.yml` and asserts the invariant mechanically:

1. It reads the `workflow_dispatch.inputs.action.options` list as the authoritative set of dispatchable actions.
2. It locates the **Run Daily Predictor Command** step and asserts the guard evaluates to `false` for an `unknown-future-action` sentinel — proving the fail-safe default.
3. For every declared action it walks all steps, evaluates each step's `if:` expression against that action via the `_eval_gh_if` helper (which rewrites `always()`, the `skip` check, and the `steps.cmd.outputs.command` reference into a plain Python expression), substitutes `${{ steps.cmd.outputs.command }}` into each `run:` script, and counts how many steps end with `main.py <action>`.
4. It asserts exactly **one** invocation per action, so a future edit that removes the guard, duplicates a step, or adds a second generic runner fails the suite immediately.

## Related

- [[entities/cron-dispatcher]] — the edge scheduler that dispatches these workflow actions
- [[entities/pipeline]] — the pipeline phases the dispatched commands drive
- [[entities/daily-market-predictor]] — the `daily-predictor` and `evaluate-daily-predictions` commands
- [[entities/daily-postmortem]] — the `daily-postmortem` command
- [[concepts/daily-spy-live-trading]] — the `daily-trade` command
- [[concepts/workflow-consolidation]] — the principle of consolidating many jobs into one workflow
