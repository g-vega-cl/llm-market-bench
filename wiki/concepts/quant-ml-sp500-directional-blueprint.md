---
tags: [quant, ml, autoresearch, market-efficiency, sp500, directional-prediction, blueprint]
category: concept
---

# Quantitative ML Blueprint for S&P 500 Daily Directional Prediction

A quantitative, econometric, and machine-learning blueprint detailing the statistical requirements, mathematical objective functions, structural priors, and architectural ensembling necessary to achieve genuine, non-trivial predictive edge in intraday S&P 500 (`SPY`) Open-to-Close forecasting without temporal leakage or statistical illusion.

## 1. The Statistical Power & Sample Size Dilemma

In liquid equities, daily Open-to-Close returns follow a near-martingale distribution:
$$E[R_{t+1} \mid \mathcal{F}_t] \approx 0$$
Under a two-sided Bernoulli trial with null hypothesis $H_0: p = 0.50$ (random walk):
- For small sample sizes (such as $N = 22$ sessions), standard error is large:
  $$\sigma = \sqrt{\frac{p(1-p)}{N}} = \sqrt{\frac{0.25}{22}} \approx 10.66\%$$
- To achieve statistical significance at $\alpha = 0.05$ ($p < 0.05$), a model must score $\ge 16/22$ hits ($72.7\%$ win rate, $p = 0.0262$).
- **The Empirical Reality**: Sustainable institutional equity market edge is typically $56\% \text{ to } 58\%$ balanced directional win rate (e.g. Renaissance Technologies' Medallion fund operates around ~50.75%–54% across high-capacity horizons).
- Expecting $\ge 70\%$ win rate over $N=22$ without overfitting is a statistical illusion. Conversely, a true $59\%$ edge will be falsely rejected as insignificant ($p \approx 0.14$).

### Remediation: Expanding Windows & Purged Walk-Forward CV
1. **Sample Scaling ($N \ge 60$ Balanced)**:
   - At $N=60$, a $58.3\%$ win rate (35/60) yields $z = 1.29$, while $61.7\%$ (37/60) crosses $p = 0.035$ ($z = 1.81$). True alpha becomes statistically distinguishable from random drift.
2. **Purged Walk-Forward Cross-Validation (WF-CV)**:
   - Rolling 3-month train $\to$ 1-month test folds with an embargo purge to eliminate cross-session autocorrelation and prevent epoch over-optimization.

---

## 2. Objective Function: Return-Weighted Sharpe & Sized Kelly Alpha

Binary accuracy ($y \in \{0, 1\}$) treats a $+1.8\%$ CPI trend breakout identically to a $+0.04\%$ flat gamma-pinned grind:
- A $60\%$ win-rate model that captures small $+0.1\%$ gains but misses $-2.0\%$ drawdown shocks produces catastrophic negative portfolio returns.
- A $50\%$ win-rate model that selectively sizes into fat-tail directional trend days achieves high compounded growth and positive Kelly fractions.

### Sized Daily Trading PnL Formula
The ratchet objective function evaluates Risk-Adjusted Position-Sized PnL:
$$\text{Score} = \text{Sharpe}\left(r_t \times \text{sign}(\hat{y}_t) \times \frac{\hat{C}_t - 50}{50}\right)$$
Where:
- $\hat{y}_t \in \{\text{UP}, \text{DOWN}\}$ is the predicted direction.
- $\hat{C}_t \in [50.0, 100.0]$ is model confidence.
- $r_t = \frac{\text{Close}_t - \text{Open}_t}{\text{Open}_t}$ is realized Open-to-Close return.
- If high confidence ($\hat{C}_t \ge 65\%$) coincides with large realized returns, portfolio utility is maximized. If high confidence fails on large counter-trend moves, drawdown penalties are punitive.

---

## 3. Curing the Pre-Training "Bear-Bias Attractor"

### The News Asymmetry Problem
Across multiple ratchet iterations, LLMs repeatedly collapse into perma-bear predictions ($\text{Recall}_{\text{DOWN}} \ge 90\%$, $\text{Recall}_{\text{UP}} \le 27\%$).
- **Pre-Training Corpora Skew**: Financial media publishes $10\times$ more alarmist content ("Recession Risk", "Debt Ceiling Crisis", "Yield Spike") than celebration during bull runs.
- **The "Wall of Worry" Principle**: Equities climb a wall of worry. Persistent passive structural flows (blind 401(k) indexing, $\$3\text{B/day}$ corporate buybacks, and dealer long-gamma positioning) provide an upward drift unless an unexpected, unpriced delta hits the market.

### The Bayesian Prior-to-Posterior Gate
1. **Baseline Prior**: Assume positive structural drift ($P(\text{UP}) = 0.53$) in the absence of fresh macroeconomic surprise.
2. **Expectation Gap**: Macro headlines that simply reiterate known ongoing issues (high interest rates, geopolitical tensions) are already priced in. A directional trade requires a measurable expectation gap (actual release vs consensus forecast).

---

## 4. Input Conditioning: Normalized Feature Vectors vs Text Bloat

Feeding $25\text{k}+$ characters of narrative text causes "lost-in-the-middle" attention degradation. Models fixate on sensational adjectives rather than numerical differentials.

### Standardized Quantitative Vector
Before narrative commentary, the prompt is injected with a structured tabular summary:
```yaml
quant_vector:
  overnight_gap_pct: +0.32          # SPY Open vs Prior Close
  yield_10y_delta_bps: -3.8         # TLT / 10Y Treasury movement
  oil_gold_risk_parity: "EASING"    # Commodities inflation proxy
  options_put_call_oi: 0.84         # Below 1.0 = Bullish open interest
  options_max_pain_distance_pct: +0.45 # Spot distance to Max Pain
  implied_vs_realized_vol_spread: -1.2 # Negative = compressed vol (pin regime)
  index_breadth_spread: +0.55       # QQQ/IWM leading SPY = broad risk-on
```
This anchors reasoning in quantitative differentials before narrative synthesis begins.

---

## 5. Architectural Horizon: The "Committee of Rivals" Ensemble

Single prompts suffer from high sample variance. A single prompt optimized across 22 sessions overfits to idiosyncratic market noise.

### The 3-Specialist Architecture
1. **Agent Alpha (Derivatives & Pinning Specialist)**: Focuses strictly on options 25-delta skew, Max Pain gravitation, and dealer gamma positioning.
2. **Agent Beta (Cross-Asset & Breadth Specialist)**: Focuses on Treasury yield curve shifts (10Y/2Y), US Dollar (DXY/UUP), and tech/small-cap breadth (`QQQ`/`IWM`).
3. **Agent Gamma (Macro Catalyst & Expectation Specialist)**: Focuses on 8:30 AM ET economic prints (CPI, PPI, NFP) vs consensus forecasts.

**Consensus Mechanism**: If 2 of 3 agents agree with high confidence, execute directional trade. If agents diverge, issue `NO_TRADE` (cash preservation).

---

## 6. Zero Lookahead & Point-in-Time Microstructure Integrity

All point-in-time constraints must remain hermetic:
- Strict 09:15 AM ET cutoff for pre-market news, economic releases, and proxy quotes.
- Zero inclusion of 09:30 AM opening price action inside prompt context.
- Target date calendar masking to eliminate model pre-training memorization.

---

## 7. Empirical Forensics: The "Bear Porn" Prior & Two-Sided Gating Case Study

During tournament runs on 1:1 balanced ground-truth sessions ($N=22$), candidate prompts frequently attempt to game institutional scoring functions by drifting into **perma-bear asymmetry**. 

### Iteration 3 Forensic Case Study
- **Raw Metric Outcome**: Candidate achieved an in-sample score of `48.98` (surpassing the baseline Champion's `47.41`) with an annualized Sharpe of `+3.32` and `1.81` Profit Factor.
- **The Short-Bias Trap**: Evaluated across 11 UP days and 11 DOWN days, the candidate achieved:
  - **Recall DOWN**: $81.8\%$ (9/11 red days captured)
  - **Recall UP**: $27.3\%$ (only 3/11 green days captured)
- **Gating Intervention**: The discrete two-sided promotion gate rejected the candidate:
  ```text
  Candidate rejected: Recall UP 27.3% < 55.0% (Bear-biased)
  ```
Without this discrete two-sided gate, the tournament would have promoted an overfit short-biased prompt that suffers catastrophic drawdowns in structural bull regimes.

---

## 8. Confidence-Sized Sharpe Sieve Pruning

Traditional multi-stage screening funnels (Stage 1 sieves) rely on raw win rate thresholds (e.g. $\ge 52\%$ over the first 15 sessions). However, raw win rate is risk-blind:
- A candidate that achieves 8 tiny scratch wins but suffers 7 massive, high-confidence drawdowns can sneak past a raw win-rate sieve while destroying portfolio capital.
- Conversely, a candidate with well-sized, high-conviction wins and disciplined, small-loss scratches might sit near $53\%$ win rate but possess an annualized Sharpe $> +2.0$.

### Sized Sieve Formulation
At the Stage 1 sieve boundary ($N_{\text{sieve}} = 15$):
1. **Raw Win Rate Gate**: $\text{WR} \ge 52.0\%$ ($\ge 8$ hits).
2. **Confidence-Sized Sharpe Gate**: $\text{Sharpe}_{\text{sized}} \ge -0.5$.
If a candidate experiences catastrophic drawdowns on high-confidence misses, it is pruned immediately, preserving GPU compute for viable candidates.

---

## 9. Pseudo-Random Temporal Stratification (Interleaved Dates)

Sorting evaluation sessions chronologically introduces **contiguous timeframe regime bias**:
- In a chronologically sorted sequence, the first 15 sessions (Stage 1 sieve) evaluate a single contiguous window (e.g., mid-August to late-September), which may be dominated by a single market regime (such as high-volatility chop).
- By introducing pseudo-random deterministic shuffling (`shuffle_order=True`), the Stage 1 sieve evaluates dates scattered non-contiguously across disparate months (e.g. August, September, October).
- This ensures that early pruning evaluates cross-regime generalization rather than contiguous regime memorization.

---

## 10. Modular Reasoning Blocks vs Prompt Puppet-Mastering

In alignment with [[concepts/tool-first-agency]], human engineers and coding agents must never hardcode trading heuristics or market-state rules into baseline prompts. Instead, capabilities are registered as optional modular blocks in `apps/engine/autoresearch/prompt_blocks.py`:
- `market_regime_classification`: 4-quadrant pre-forecast state identification (`LOW_VOL_PIN`, `TREND_EXPANSION`, `MEAN_REVERSION`, `CATALYST_EVENT`).
- `option_pin_gamma_levels`: Max Pain strike gravitation and 0DTE dealer gamma walls.
- `anti_pessimism_prior_conditioning`: Empirical ~54% equity drift baseline prior check with symmetric hurdle discipline.
- `dialectical_thesis_deliberation`: Dual-sided Bull vs Bear conviction scoring (1-10) with tie-breaking and low-conviction clamping.
- `regime_gated_confidence_calibration`: Structural confidence clamping (52-55% in range-bound/pinning regimes; >60% reserved for confirmed cross-asset divergences).

The Autoresearcher loop (`PromptResearchResult`) autonomously explores, tests, and adopts these blocks based on whether they improve two-sided out-of-sample Sharpe returns.

---

## 11. The "Asymmetry Pendulum" and Dialectical Balance Sheets

Forensic audits of tournament iterations (notably Iterations 3, 8, 12, and 13) revealed a recurring LLM failure mode dubbed the **Asymmetry Pendulum**:
- **Phase A (Perma-Bear Drift)**: After failing on rally days, mutation prompts over-index on risk headlines (debt, hawkish Fed, rate shocks), collapsing into perma-bear predictions (e.g. Iteration 12: Recall UP of only 14.3%).
- **Phase B (Perma-Bull Whiplash)**: In reaction, the optimizer adds rules suppressing false DOWN calls, causing the prompt to swing 180 degrees to perma-bull predictions (e.g. Iteration 13: 19 UP calls in 20 sessions, Recall DOWN of only 10.0%).

### Architectural Remedy: Dialectical Thesis Deliberation
To break this whiplash without violating Principle 8 (Tool-First Agency):
1. **Dialectical Conviction Balance Sheet**: The prompt constructs explicit `Bull Conviction Score [1-10]` and `Bear Conviction Score [1-10]` in reasoning traces.
2. **Symmetric Evidentiary Hurdles**: Calling UP and calling DOWN require identical evidential weight. If $|Bull - Bear| \le 1$, the regime defaults to `CONSOLIDATION / RANGE-BOUND` with clamped confidence (52%–54%).
3. **Anti-Whiplash Meta-Prompt Invariant**: The meta-researcher mutator is strictly instructed: *"Do not cure missed UP calls by penalizing DOWN calls. Directional symmetry is non-negotiable."*

---

## 12. Stage 1 Balanced Accuracy and Single-Class Recall Sieve Guards

While raw win rate ($\ge 52.0\%$) and confidence-sized Sharpe ($\ge -0.5$) prune random coin-flippers and reckless drawdowns, an asymmetric candidate (such as 14 UP calls and 1 DOWN call) could theoretically sneak through Stage 1 with 8/15 hits ($53.3\%$) despite a near-zero Recall DOWN.

To save GPU compute and eliminate doomed asymmetric candidates early:
1. **Balanced Accuracy Floor**: $\text{Balanced Acc} \ge 48.0\%$ at Session 15.
2. **Minimum Single-Class Recall**: $\min(\text{Recall}_{\text{UP}}, \text{Recall}_{\text{DOWN}}) \ge 25.0\%$ at Session 15.

If a candidate exhibits class collapse at Session 15, it is pruned immediately, saving 7 remaining full sessions (~25 minutes of GPU inference per iteration).

---

## Related

- [[entities/local-autoresearch]] — Local prompt tournament orchestrator pairing Strata Qwen distillation with two-pass Qwen decision reasoning
- [[concepts/daily-directional-predictability-limits]] — Post-mortem of the 300-iteration Jev locked vault tournament
- [[concepts/pure-directional-scoring]] — Pure directional scoring without artificial intraday hit artifacts
- [[concepts/ground-truth-autoresearch-leakage-guards]] — Anti-leakage and anti-memorization safeguards for autoresearch
- [[concepts/modular-prompt-blocks]] — Modular prompt blocks catalog
- [[concepts/tool-first-agency]] — Principle 8 Tool-First, Agency-Driven Architecture
