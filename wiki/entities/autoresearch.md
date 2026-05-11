---
tags: [autoresearch, prompt-improver, meta-learning]
category: entity
---

# Auto-Research (Prompt Improver)

The auto-research module at `apps/engine/autoresearch/` implements a
Karpathy-style autonomous prompt improvement loop. Every Sunday evening,
it evaluates the past week's live trading performance for the experiment
agents (Gemini Flash Lite and DeepSeek Flash), calls a meta-researcher
LLM (DeepSeek v4 Pro) to propose prompt improvements, and activates the
best variant for the coming week.

## Architecture

The module is organized into a clean pipeline:

- **`program.md`** — the meta-prompt: research instructions for the
  auto-research LLM, defining evaluation dimensions, constraints, and the
  local minima escape policy
- **`window.py`** — shared Mon–Sun week-boundary calculator used by both
  the evaluator and runner to avoid calendar drift. Runner computes the
  window once and passes it to the evaluator, eliminating the previous
  double-computation.
- **`metrics.py`** — computes Wall Street metrics (Sharpe, Sortino, Info
  Ratio, Max Drawdown, Profit Factor) from `portfolio_performance`,
  `price_history` (SPY benchmark for Information Ratio), and `trades`
  tables; normalizes to 0–1 via `compute_composite_score()`. Warns when
  benchmark data is missing (e.g., "NO_TRADING_DATA", "NO_BENCHMARK").
- **`decision_quality.py`** — scores signal concordance (did BUYs lead to
  profitable SELLs?), conviction calibration (do higher-confidence trades
  earn more?), and **regime awareness** (did the agent sell when VIXY
  spiked and buy when markets calmed?). All tied to realized PnL and
  actual VIXY price data.
- **`evaluator.py`** — gathers all data (portfolio performance, decision
  quality, price history for VIXY/SPY market regime), computes metrics,
  formats the structured markdown report fed to the auto-research LLM.
  Accepts optional `week_start`/`week_end` params from the runner.
- **`researcher.py`** — calls DeepSeek v4 Pro via Instructor, receives
  a `PromptResearchResult` (new prompt text, reasoning, confidence).
  Does NOT close the HTTP client (the singleton is process-scoped —
  closing it kills the next caller).
- **`prompt_store.py`** — DB CRUD for `prompt_experiments` table plus an
  in-process cache (60s TTL) for hot-path `get_active_prompt()` calls
- **`validator.py`** — post-LLM safety check with two tiers: **hard
  invariants** (forbidden phrases like "bypass guardrails", empty/oversized
  prompts, >1000 words) that block activation, and **soft
  invariants** (tool requirements, 5 Whys technique) that emit warnings but
  allow activation. The control portfolios and `<2 trades` safety checker
  provide the real guardrails.
- **`runner.py`** — top-level orchestrator: safety check → evaluate →
  research → validate → save → activate. Computes the week window once and
  passes it to `evaluate_week()` to prevent midnight drift.

## How It Integrates

The module is loaded lazily only when needed:

1. **`prompt_factory.py`** imports `prompt_store` only when building
   messages for an experiment-group agent — control agents never pay the
   import cost
2. **`main.py`** dispatches `autoresearch` CLI command to `runner.run()`,
   invoked by the weekly GitHub Actions cron
3. **`prompt_experiments`** table stores every variant with metrics,
   reasoning, and status (active/kept/discarded/crashed)

## Experiment vs. Control

Only two agent portfolios receive auto-researched prompts:

| Agent | Role | Prompt Source |
|-------|------|---------------|
| OpenAI (`gpt-5.4-nano`) | Control | Hardcoded baseline |
| Claude (`claude-haiku-4-5`) | Control | Hardcoded baseline |
| Gemini (`gemini-3.1-flash-lite`) | Experiment | DB active variant |
| DeepSeek (`deepseek-v4-flash`) | Experiment | DB active variant |

The control group provides a benchmark. The evaluator computes metrics for
both groups and presents them side-by-side in the research report.

## Safety Mechanisms

- **Crash detection**: <2 actual trades (queried from `trades` table joining
  through `portfolios!inner(owner_id)`) in the evaluation week → auto-revert
  to previous variant before the next research cycle. High rejection rates
  are normal (LLMs hallucinate often) and are handled by the verifier, not
  treated as crashes.
- **Prompt validation**: two-tier. Hard invariants (forbidden phrases like
  "bypass guardrails", empty/oversized prompts, >1000 words) block activation. Soft invariants (tool usage,
  5 Whys) emit warnings but let the researcher experiment — the control
  portfolios benchmark the impact.
- **Verifier unchanged**: only `CORE_ANALYSIS_SYSTEM_PROMPT` is modified;
  the verifier, contrarian, and all other prompts are never touched
- **Lazy activation**: bad prompts can't reach production overnight — the
  cron runs Sunday evening, giving a full week to observe

## Local Minima Escape

Per Karpathy's design:

- If composite score stays within 5% for 2+ weeks, the report flags
  stagnation and instructs the LLM to propose a radical variant
- The research program rotates between momentum-focused, value-focused,
  contrarian-focused, and macro-event-focused prompt structures
- When the control group significantly outperforms the experiment group,
  the LLM is instructed to consider reverting toward the baseline

## Database

`prompt_experiments` table: `variant_tag`, `prompt_name`, `prompt_content`,
`week_start`/`week_end`, `metrics` (JSONB), `status` (active/kept/discarded/crashed),
`experiment_type` (incremental/radical/baseline), `parent_tag`,
`change_description`, `research_output` (JSONB), `created_at`.

## Async-client contract (read before editing `prompt_store.py`)

`core/db.get_async_supabase_client()` is `async def` and caches the
client as a process-wide singleton. Three rules follow:

- Always `await` it: `sb_client = await get_async_supabase_client()`.
  Forgetting the `await` leaves `sb_client` as a coroutine, and the
  first attribute access (e.g. `sb_client.table(...)`) raises
  `AttributeError: 'coroutine' object has no attribute …`.
- Never close the underlying http client. Closing it kills the
  singleton's httpx transport, so the next caller in the same process
  gets a dead client. This is why `researcher.py` does NOT call
  `_close_client()` — in GitHub Actions the process dies on exit anyway,
  and in local runs the singleton must stay alive.

Unit tests must mock the dependency with an `async def` stub
(`async def fake_client(): return client`) — a sync `lambda: client`
masks production `await` semantics and lets the regression through CI.

## Related

- [[concepts/auto-research-prompt-improver]]
- [[concepts/memory-feedback]]
- [[entities/engine]]
- [[entities/pipeline]]
