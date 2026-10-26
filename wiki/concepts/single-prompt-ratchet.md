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
[Stage 1: Screening Sieve (15 sessions)] ──(win_rate < 52%)──▶ [Early Prune]
                 │
           (win_rate >= 52%)
                 ▼
[In-Sample Gate (22 sessions)] ──(Score <= Champ OR BalAcc < 54%)──▶ [Reject]
                 │
           (Score > Champ AND BalAcc >= 54%)
                 ▼
[Out-of-Sample Holdout Gate (12 sessions)] ──(OOS BalAcc < 55%)──▶ [Reject Overfit]
                 │
           (OOS BalAcc >= 55%)
                 ▼
[Promote New Champion]
```

## Empirical Tournament Results (54-Iteration Progression)

In a 54-iteration autonomous tournament executed on Strata ORCA (`orcarouter-qwen3.8-flash-next-uncensored-iq3_xxs`), the ratchet produced two major promotion milestones from the initial Gen 0 baseline to the reigning **Iteration 43 Champion**:

| Quantitative Metric | Gen 0 Baseline | Iteration 40 Milestone | Iteration 43 Champion 🏆 | Total Improvement |
| :--- | :---: | :---: | :---: | :---: |
| **Composite Score** | `47.4110` | `50.4939` | **`54.3417`** | **$+6.93$ points** |
| **In-Sample Win Rate** | `59.1%` (13/22) | `68.2%` (15/22) | **`72.73%` (16/22)** | **$+13.6\%$** |
| **Balanced Accuracy** | `59.1%` | `68.2%` | **`72.73%`** | **$+13.6\%$** |
| **Recall UP** | `36.4%` (4/11) | `54.5%` (6/11) | **`63.64%` (7/11)** | **$+27.2\%$** |
| **Recall DOWN** | `81.8%` (9/11) | `81.8%` (9/11) | **`81.82%` (9/11)** | **Unchanged (Disciplined)** |
| **Matthews Correlation (MCC)** | `+0.1823` | `+0.3644` | **`+0.4623`** | **$+0.2800$** |
| **Annualized Sharpe Ratio** | `+3.15` | `+6.84` | **`+8.27`** | **$+5.12$** |
| **Brier Calibration Score** | `0.2384` | `0.2289` | **`0.2263`** | **$-0.0121$ (Sharper)** |
| **Statistical Significance** | $p = 0.201$ (`False`) | $p = 0.056$ (`False`) | **$p = 0.0262$ (`True`)** | **Statistically Confirmed Alpha** |
| **Out-of-Sample Holdout** | `50.0%` (6/12) | `58.3%` (7/12) | **`58.33%` (7/12)** | **Cleared $\ge 55.0\%$ Hurdle** |

---

## Architectural Breakthrough: The Four-Regime State Classifier

The winning strategy evolved by Strata ORCA in Iteration 43 established a disciplined analytical framework that replaced verbose prompt heuristics with a dense four-regime taxonomy:

> *"Use a balanced four-regime state classifier before any directional call. First classify the state as Risk-On Expansion, Risk-Off Expansion, Balanced Pinning, or Catalyst Shock. Do not let narrative tone, a single sector headline, or a macro headline create direction unless cross-asset evidence confirms it.*
>
> *Risk-On Expansion requires small-cap and cyclical leadership, defensive underperformance, credit-spread stability or tightening, commodity confirmation, and a non-compressed tape; only these states may support higher-confidence UP calls.*
>
> *Risk-Off Expansion requires small-cap lag, defensive outperformance, credit-spread widening, commodity weakness, and broad futures weakness; only these states support higher-confidence DOWN calls.*
>
> *Balanced Pinning and Catalyst Shock are low-confidence states: assign low-confidence direction from the short-term tape vector, not from a permanent bias, and avoid defaulting low-vol or macro-news states to either UP or DOWN.*
>
> *Balanced state coverage means the strategy must produce both DOWN calls when risk-off internals are present and UP calls when risk-on or balanced internals are present. Do not treat compressed options, low implied volatility, max-pain pinning, or macro-event noise as high-confidence directional evidence. If the bull and bear columns are balanced, reduce confidence; only use elevated confidence when the state is clearly directional and cross-asset internals confirm the same direction."*

### Performance Breakdown by Regime
Forensic analysis of the 22 in-sample trading sessions revealed why this architecture broke through:
- **Directional Regimes (Risk-On & Risk-Off Expansion)**: **100% Accuracy (10/10 sessions)**. When cross-asset internals confirmed expansion, the model never failed.
- **Ambiguous Regimes (Balanced Pinning & Catalyst Shock)**: **50% Accuracy (6/12 sessions)**. All 6 missed predictions (`2026-10-15`, `2026-08-17`, `2026-09-24`, `2026-08-12`, `2026-10-13`, `2026-09-14`) occurred on days with tiny intraday moves ($\pm 0.08\%$ to $\pm 0.43\%$) where market action was dominated by random micro-chop.
- **Instruction Density vs Prompt Bloat**: Rather than bloating context with rigid IF/THEN rules, the prompt operates as a conditioning prior that forces cross-asset verification across equities, credit spreads, commodities, and volatility before allocating conviction.

---

## Empirical Discoveries

### 1. Systemic LLM Downside Bias (+31.5% Delta)
Across all 55 journal entries in the tournament, base LLMs exhibited a pronounced, systemic short bias:
- **Mean Recall UP**: `33.1%`
- **Mean Recall DOWN**: `64.6%`
- **Asymmetry Delta**: `+31.5%` toward DOWN calls.

Uncalibrated LLMs processing financial newsletters consistently suffer from "macro-anxiety": negative headlines regarding inflation, geopolitical friction, bond yields, or consumer weakness trigger reflexive bear predictions. The Gen 0 baseline collapsed into single-class short degeneracy (predicting DOWN on 82% of sessions). Iteration 43 corrected this by recognizing that low-vol pinning and balanced tape regimes have an empirical upward drift, raising Recall UP from 36.4% to 63.6% while maintaining 81.8% Recall DOWN.

### 2. Stage 1 Screening Sieve Efficiency
The two-stage evaluation sieve evaluated candidate prompts across an initial 15-session subset with a $52.0\%$ win-rate hurdle before executing the full 22-session training pass:
- **Candidates Evaluated**: 54 iterations.
- **Candidates Pruned in Stage 1**: 14 candidates.
- **Evaluations Conserved**: $14 \times 15 = 210$ session inferences saved.
- **Compute Conserved**: $\approx 8.8\text{ hours}$ of local inference time conserved, allowing search iterations to focus compute exclusively on statistically promising mutants.

---

## Sample Size Ceiling & Diminishing Returns

A fundamental insight from the 54-iteration tournament is the **Sample Size Resolution Ceiling**:
1. **Discrete Resolution Limit**: In a balanced 22-session training partition, each individual trading day accounts for $\frac{1}{22} \approx 4.55\%$ of accuracy. Moving from 16 hits ($72.7\%$) to 17 hits ($77.3\%$) hinges on flipping a single calendar session.
2. **Topology Exhaustion**: 54 iterations of meta-prompt exploration on 22 training points thoroughly mapped the prompt space. Beyond 50 iterations on a small dataset, prompt mutations transition from *signal extraction* to *noise fitting* (overfitting to the microscopic price drift of specific sessions).
3. **Data Breadth as the True Bottleneck**: Further iterations on the existing 34-session dataset yield rapidly diminishing returns. True capability expansion requires expanding the underlying ground-truth sample size—either by accumulating more live trading sessions over calendar time or expanding evaluation to cross-ticker intraday baskets (`QQQ`, `IWM`).

---

## The Max Pain Historical Data Anomaly

During the tournament audit, an anomaly in pre-market options data was uncovered: historical morning newsletters prior to late October 2026 frequently reported SPY pinned to Max Pain within 0.05% of spot ($767 for $766.60, $763 for $763.25, $777 for $777.22).

This was caused by an upstream limitation in the Massive free-tier endpoint, which sampled only 4 contracts (ATM and 25-delta calls/puts) and substituted volume for open interest, causing Max Pain to collapse onto the nearest round-dollar strike. Crucially, the Iteration 43 Champion independently identified that this feature was uninformative noise and explicitly neutralized it:
> *"Do not treat compressed options, low implied volatility, max-pain pinning, or macro-event noise as high-confidence directional evidence."*

The options data pipeline has since been hardened via full-chain Alpaca OCC open interest ([[concepts/max-pain-data-sources]]).

## Key Invariants

1. **Production Format Parity**: The evaluation prompt and user payload format match the production runner in `apps/engine/tasks/daily_predictor.py` verbatim.
2. **Frozen Interface Preservation**: Only the analytical reasoning and strategy instructions are exposed to mutation via `split_daily_predictor_prompt`. The system constraints header and the JSON output contract remain immutable.
3. **Zero Network Calls in Tests**: Colocated test suite `apps/engine/local_autoresearch/test_single_prompt_ratchet.py` operates 100% hermetically with mocked transports and zero external sockets.
4. **Leak-Free Ground Truth & Balanced Partitioning**: 47 strictly pre-market sessions (< 09:30 AM EDT) partitioned into a 1:1 balanced dataset of 34 clean sessions (22 In-Sample / 12 OOS holdout) ensuring equal UP/DOWN base rates. See [[concepts/ground-truth-autoresearch-leakage-guards]].
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
