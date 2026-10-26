---
tags: [concept, autoresearch, leakage-guards, statistics, balanced-accuracy]
category: concept
---

# Ground-Truth Autoresearch Leakage Guards

When evaluating and evolving predictive LLM trading prompts against real production records, subtle temporal lookahead leaks, class imbalance base rates, and meta-prompter date memorization can create deceptive in-sample performance that collapses in live execution.

This document details the four mathematical and structural leakage guards enforced in [[entities/local-autoresearch]] and [`apps/engine/local_autoresearch/single_prompt_ratchet.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/local_autoresearch/single_prompt_ratchet.py).

---

## 1. Lookahead Timestamp Leakage

### The Vulnerability
In live automated systems, pipeline retry delays, network stalls, or manual triggers can cause newsletters or predictions to be serialized after market open (09:30 AM EDT). In our live Supabase records, 7 of 51 recorded sessions were stamped post-open (e.g. 2026-09-23 at 03:18 PM EDT), allowing the model to observe midday price collapses and assign an artificial 84% confidence on DOWN moves.

### The Guard (`is_premarket_timestamp_clean`)
All live sessions are strictly filtered during materialization in [`apps/engine/local_autoresearch/live_session_store.py`](file:///home/cv/Documents/Code/llm-market-bench/apps/engine/local_autoresearch/live_session_store.py):
1. **UTC Source Ceiling**: `source_created_at` timestamp must be strictly `< 13:30:00 UTC` (09:30:00 AM EDT).
2. **Payload Context Regex**: The serialized `Exact Current Time` inside the market context string is parsed. Any time in `PM` or with `hh == 9 and mm >= 30` is purged immediately.

Filtering reduced the raw dataset from 51 sessions to **47 strictly pre-market sessions** (17 UP / 30 DOWN).

---

## 2. The Majority-Class Base-Rate Trap

### The Vulnerability
In asymmetric market regimes, raw directional win rate is vulnerable to the **Base-Rate Trap**. In the 47 clean sessions, the empirical distribution is:
- **UP**: 17 sessions (36.2%)
- **DOWN**: 30 sessions (63.8%)

A naive bot predicting **DOWN on 100% of days** achieves a deceptive **63.8% raw win rate**, appearing to beat a 50% coin-flip null hypothesis ($p < 0.05$), while generating zero trading edge on bullish days ($\text{Recall}_{UP} = 0.0\%$).

### The Guard (Balanced Accuracy & MCC)
The ratchet evaluates two-sided classification using **Balanced Accuracy** and the **Matthews Correlation Coefficient (MCC)**:

$$\text{Balanced Accuracy} = \frac{1}{2} \left( \text{Recall}_{UP} + \text{Recall}_{DOWN} \right) = \frac{1}{2} \left( \frac{TP}{TP + FN} + \frac{TN}{TN + FP} \right)$$

$$\text{MCC} = \frac{TP \times TN - FP \times FN}{\sqrt{(TP + FP)(TP + FN)(TN + FP)(TN + FN)}}$$

- For the always-down bot:
  $$\text{Balanced Accuracy} = \frac{0.0 + 1.0}{2} = 50.0\% \quad (\text{Failed})$$
  $$\text{MCC} = 0.000 \quad (\text{No correlation})$$
- Promotion requires both:
  1. Primary Ratchet Score improvement over champion.
  2. Balanced Accuracy $\ge 58.0\%$ with positive MCC.

---

## 3. In-Sample Overfitting & Date Memorization

### The Vulnerability
With 47 trading sessions, iterating a meta-researcher over 20+ mutation cycles allows the prompt to overfit to localized idiosyncrasies of specific calendar dates (e.g. "If today is August 12, fade the CPI print").

### The Guard (Stratified Holdout Gating & 1:1 Balanced Partitioning)
Sessions are deterministically partitioned (seed 42) into two isolated sets:
- **Default 1:1 Balanced Split (`create_balanced_stratified_split`)**: 34 clean sessions paired to strictly equal UP/DOWN base rates:
  - **In-Sample Training Set (22 sessions)**: 11 UP (50.0%) / 11 DOWN (50.0%).
  - **Out-of-Sample Holdout Set (12 sessions)**: 6 UP (50.0%) / 6 DOWN (50.0%).
- **Full Stratified Split (`create_stratified_split`)**: All 47 clean sessions preserving raw empirical base rates:
  - **In-Sample Training Set (31 sessions)**: 11 UP (35.5%) / 20 DOWN (64.5%).
  - **Out-of-Sample Holdout Set (16 sessions)**: 6 UP (37.5%) / 10 DOWN (62.5%).

A candidate prompt must:
1. Pass the Stage 1 sieve on training sessions (win rate $\ge 52.0\%$).
2. Beat the current champion's in-sample composite score.
3. Pass the **OOS Holdout Gate**: achieve $\ge 55.0\%$ Balanced Accuracy on the holdout sessions. Candidates failing OOS are rejected as overfit. See [[concepts/single-prompt-ratchet]].

---

## 4. Date-Snooping in Meta-Researcher

### The Vulnerability
When feeding prediction errors back to the meta-prompter to formulate new hypotheses, including calendar dates (e.g. "On 2026-08-12 we missed DOWN") directly invites the LLM to write date-specific heuristics into the system prompt.

### The Guard (Scenario Abstraction & Regex Linter)
1. **Anonymized Error Summaries**: Miss summaries are formatted as abstract market conditions:
   ```
   - Scenario 1: Predicted UP (Conf: 61%), but actual market move was DOWN (-0.57%).
     Prior reasoning was: "Tech momentum supportive, CPI expected in-line..."
   ```
2. **Automated Regex Linter (`lint_mutant_prompt`)**: Every mutant strategy proposed by the meta-researcher is audited before compilation:
   - Rejects 4-digit calendar years (`2024`, `2025`, `2026`).
   - Rejects month names (`January` through `December`, `Jan` through `Dec`).
   - Rejects calendar date constructs (`Aug 12`, `August 12th`).
   - Any prompt violating temporal hygiene is rejected and demoted immediately.

---

## Related Documentation

- [[entities/local-autoresearch]] — Local tournament runner and Strata ORCA integration.
- [[concepts/pure-directional-scoring]] — Pure directional score formulation without artificial intraday assumptions.
- [[concepts/daily-directional-predictability-limits]] — Information horizon and selectivity analysis.
