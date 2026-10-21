---
tags: [autoresearch, ground-truth, ratchet, prompt-engineering, production-parity]
category: concept
---

# Single-Prompt Ground-Truth Ratchet

The Single-Prompt Ground-Truth Ratchet is a streamlined, production-aligned local prompt optimization architecture. It evaluates and evolves the core intraday trading prompt (`DAILY_PREDICTOR_PROMPT`) directly against real, un-simulated production market sessions materialized from live databases.

## Why It Matters

Historical backtesting and synthetic two-pass distillation (generating a simulated morning newsletter, then arbitrating a trade decision) introduced significant simulation gap:
1. **Context Shift**: Synthetic newsletters generated from historical price dumps lacked true point-in-time morning information (such as 8:30 AM CPI surprises, overnight corporate earnings announcements, pre-market options flow, and real editorial insights).
2. **Co-Evolution Drift**: The two-pass tournament frequently co-evolved to parse synthetic quirks rather than real market dynamics.
3. **Severe Compute Overhead**: Synthesizing 1,200-word newsletters for dozens of historical sessions required 60+ minutes per batch on local hardware.

The single-prompt ratchet eliminates all synthetic reconstruction by locking evaluation strictly to **genuine production sessions** (`.live_production_sessions.db`) and optimizing the exact single prompt that executes in live daily trading.

## Architecture

```text
[Materialized Live Sessions (SQLite: 47 Clean Premarket Days)]
                 │
                 ▼
     [DAILY_PREDICTOR_PROMPT]
  ┌─────────────────────────────┐
  │ Frozen Header (Identity)    │
  ├─────────────────────────────┤
  │ Mutated Strategy Block      │ ◀── (Strata ORCA Meta-Researcher, Date-Blind)
  ├─────────────────────────────┤
  │ Frozen Footer (JSON Schema) │
  └─────────────────────────────┘
                 │
                 ▼
[Stage 1: Screening Sieve (25 sessions)] ──(win_rate < 52%)──▶ [Early Prune]
                 │
           (win_rate >= 52%)
                 ▼
[In-Sample Gate (31 sessions)] ──(Score <= Champ OR BalAcc < 58%)──▶ [Reject]
                 │
           (Score > Champ AND BalAcc >= 58%)
                 ▼
[Out-of-Sample Holdout Gate (16 sessions)] ──(OOS BalAcc < 55%)──▶ [Reject Overfit]
                 │
           (OOS BalAcc >= 55%)
                 ▼
[Promote New Champion]
```

## Key Invariants

1. **Production Format Parity**: The evaluation prompt and user payload format match the production runner in `apps/engine/tasks/daily_predictor.py` verbatim.
2. **Frozen Interface Preservation**: Only the analytical reasoning and strategy instructions are exposed to mutation via `split_daily_predictor_prompt`. The system constraints header and the JSON output contract remain immutable.
3. **Zero Network Calls in Tests**: Colocated test suite `apps/engine/local_autoresearch/test_single_prompt_ratchet.py` operates 100% hermetically with mocked transports and zero external sockets.
4. **Leak-Free Ground Truth**: 47 strictly pre-market sessions (< 09:30 AM EDT) with 31 In-Sample / 16 OOS holdout gating. See [[concepts/ground-truth-autoresearch-leakage-guards]].
5. **Balanced Accuracy & Base-Rate Protection**: Evaluates two-sided classification using Balanced Accuracy and MCC to penalize one-sided short-bias heuristics.
6. **Unconstrained Reasoning on Strata ORCA**: Runs `orcarouter-qwen3.8-flash-next-uncensored-iq3_xxs` with `max_tokens: 16384` and `reasoning_budget_tokens: -1` (~12,288 token thinking budget), completing in ~105s average latency with zero timeouts.

## Implementation

- **Data Store**: `apps/engine/local_autoresearch/live_session_store.py` (`.live_production_sessions.db`)
- **Evaluator & Tournament Loop**: `apps/engine/local_autoresearch/single_prompt_ratchet.py`
- **Tests**: `apps/engine/local_autoresearch/test_single_prompt_ratchet.py`
- **Significance Engine**: `apps/engine/local_autoresearch/significance_funnel.py`

## Related

- [[concepts/ground-truth-autoresearch-leakage-guards]] — the 4 mathematical leakage & regime guards
- [[concepts/significance-funnel]] — multi-stage significance filter and hypothesis testing
- [[concepts/early-pruning]] — compute conservation via candidate aborts
- [[entities/daily-market-predictor]] — production inference task executing the evolved prompt
- [[entities/local-autoresearch]] — local runner orchestrator and Strata integration
