---
tags: [autoresearch, prompt-improver, karpathy, meta-learning]
category: concept
---

# Auto-Research Prompt Improver

A Karpathy-style autonomous feedback loop that iteratively improves the
LLM trading prompt based on live performance. The central idea: a meta-
researcher LLM evaluates 1 week of live trading data across four
evaluation dimensions and proposes prompt changes to maximize next week's
composite score.

## The Karpathy Pattern

The design follows the `autoresearch` repo pattern directly:

| Karpathy Concept | Trading Equivalent |
|---|---|
| Single file to modify (`train.py`) | Single prompt to modify (`CORE_ANALYSIS_SYSTEM_PROMPT`) |
| Fixed evaluation budget (5 min GPU) | Fixed evaluation window (1 week of live trading) |
| One metric to beat (`val_bpb`) | Composite score (Sharpe + Sortino + DD + PF + concordance + conviction) |
| Git commit / reset for state | DB `prompt_experiments` with active/kept/discarded |
| `results.tsv` for logging | `prompt_experiments` table with JSONB metrics |
| Never-stop autonomous loop | Weekly cron job (Sunday 6 PM ET) |
| Simplicity criterion | Prefer shorter, clearer prompts for equal performance |

## Four Evaluation Dimensions

The auto-research LLM receives a structured report with:

### 1. Wall Street Metrics (Quant Fund Standards)
Computed from `portfolio_performance`, `price_history`, and `trades` tables, not by the LLM:
- **Sharpe Ratio** — return per unit of total risk (annualized)
- **Sortino Ratio** — return per unit of downside risk only
- **Information Ratio** — outperformance vs. SPY per unit of tracking error
- **Maximum Drawdown** — worst peak-to-trough loss
- **Profit Factor** — gross profit / gross loss from realized SELL trades

When benchmark data is unavailable (e.g., missing SPY price history), the
composite score includes `NO_BENCHMARK` and `NO_TRADING_DATA` warning flags
so the researcher LLM knows which metrics are unreliable.

### 2. Decision Quality (Tied to Realized PnL)
- **Signal Concordance** — fraction of BUY decisions that led to profitable
  SELL closes within the evaluation window (not keyword-based)
- **Conviction Calibration** — correlation between the agent's confidence
  score and the actual realized PnL (bucketed: low ≤33, med 34–66, high ≥67)
- **Regime Awareness** — measures whether the agent's BUY/SELL ratio matched
  the VIXY volatility regime. VIXY up (fear) + selling = high awareness.
  VIXY down (calm) + buying = high awareness. Formula: 1.0 - abs(VIXY trend
  - sell ratio). Computed from actual `price_history` VIXY data, not
  keyword-based.
- **Mistake Patterns** — top-3 rejection reason clusters (e.g.,
  REJECTED_TOOL_USAGE: 14x, REJECTED_VERIFICATION: 8x)

### 3. Structural Analysis (Report Context Only)
The report includes the full current prompt text, sample winning/losing/
rejected trades with reasoning, market regime context (VIXY/SPY from
`price_history`), and the previous 5 variants with their scores. The LLM decides what structural changes to make.

### 4. Local Minima Escape
- Stagnation flag: if composite score is within 5% for 2+ weeks
- Variance injection: rotation through momentum/value/contrarian/macro
  prompt structures when stagnation is detected
- Control group comparison: if OpenAI/Claude on baseline significantly
  outperform the experiment group, the LLM considers reverting

## The Weekly Cycle

```
SUNDAY 6 PM ET:
  1. runner.py checks for crash (<2 executed trades → revert)
  2. evaluator.py gathers data, computes metrics, formats report
  3. researcher.py sends program.md + report to DeepSeek v4 Pro
  4. validator.py checks the proposed prompt for safety invariants
  5. prompt_store.py saves the variant and activates it
  6. Gemini + DeepSeek Flash get the new prompt Monday
```

## Safety

The verification layer (`verification.py`) never changes — it always runs
the baseline verifier prompt. This means even a catastrophic auto-research
failure produces rejected trades, not executed bad trades. Additionally:
- **Two-tier validation**: Hard invariants (forbidden phrases like "bypass
  guardrails", empty/oversized prompts, >1000 words) block
  activation. Soft invariants (tool usage, 5 Whys) emit warnings but let
  the researcher experiment.
- The control portfolios (OpenAI + Claude on baseline) provide a permanent
  benchmark — if an experimental prompt degrades performance, it's visible
  in the side-by-side metrics each week.
- <2 actual executed trades (queried from the `trades` table, not decisions)
  triggers auto-revert at the start of the next cycle. High rejection rates
  are expected and handled by the verifier.
- The singleton HTTP client is never closed by the auto-research code —
  in GitHub Actions the process dies on exit; in local runs the singleton
  must stay alive for subsequent callers.

## Related

- [[entities/autoresearch]]
- [[entities/engine]]
- [[entities/pipeline]]
- [[concepts/memory-feedback]]
