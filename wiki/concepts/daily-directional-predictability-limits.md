---
tags: [postmortem, autoresearch, market-efficiency, directional-prediction, evaluation, jev]
category: concept
---

# Daily Directional Predictability Limits & Post-Mortem

This concept documents the post-mortem analysis of the 300-iteration [[entities/local-autoresearch]] tournament and subsequent Locked Vault stress test. It details the structural, quantitative, and objective-function reasons why binary open-to-close directional accuracy plateaued at 52%–56%, and why naive prompt evolution collapses on out-of-sample data without structural market-regime awareness.

## Empirical Tournament Summary

Across 10 distinct archetype seeds (30 iterations each, 300 total iterations) over a 2-year dataset (507 days, 106 weeks):

| Setup | Active Pool Test Score | 21-Week Locked Vault Score | Vault Win Rate | Days Traded / Total |
| :--- | :---: | :---: | :---: | :---: |
| **Batch 9: `contrarian-sentiment` (`qwen-jev-d723b5`)** | **59.72** | **40.11** | **43.1%** | 102 / 103 (99%) |
| **Batch 7: `trend-exhaustion` (`qwen-jev-ad283a`)** | **56.18** | **52.20** | **55.6%** | 72 / 103 (70%) |
| **Unconditional Market Drift (Always UP)** | — | — | **55.3%** | 103 / 103 |
| **Random Coin Flip (50/50)** | 50.00 | 50.00 | 50.0% | 103 / 103 |

The active pool "champion" (`qwen-jev-d723b5`, scoring 59.72 in-sample) collapsed to **43.1% win rate** on the sequestered Locked Vault, underperforming both a naive buy-and-hold rule (55.3%) and a random coin flip (50.0%).

---

## Root Cause Analysis

### 1. The Selectivity Subsidy Incentive Trap

The [[concepts/pure-directional-scoring]] formula was designed to prevent cowardice (models refusing to trade):

$$\text{Score} = (0.65 \times \text{Traded Win Rate}) + (0.25 \times \text{Close Accuracy}) + (0.10 \times \text{Selectivity}) - (\text{Mean Brier} \times 20.0)$$

However, the $+0.10 \times \text{Selectivity}$ term created a perverse mathematical incentive:
- Trading 100% of days yielded $+10.0$ free points.
- A disciplined model trading only 25% of days (cherry-picking high-conviction setups with a 65% win rate) was penalized $-7.5$ points for selectivity.
- Consequently, the meta-researcher (Qwen) learned to set loose criteria and low confidence gates ($56\%–58\%$) to trade virtually every single session (102/103 days).
- In liquid equities, trading 99% of days forces the model to bet on directionless, chop-heavy sessions where directional price action is statistical noise.

### 2. The "Contrarian Gap Fade" Trap (Fighting the Trend)

In Batch 9, Qwen evolved a gap-fade rule:
- If SPY gaps up $+0.15\%$ to $+0.65\%$, predict **DOWN**.
- If SPY gaps down $-0.15\%$ to $-0.65\%$, predict **UP**.

While this rule exploited short-term mean reversion during choppy consolidation weeks in the active pool, it was disastrous on the sequestered vault during trending regimes:
- On the vault, when `qwen-jev-d723b5` called **DOWN**, its accuracy was only **13 / 39 (33.3%)**.
- The model repeatedly attempted to short morning gap-ups in an underlying bull market, falling prey to gap-and-go trend continuation.

### 3. The Mask of Legacy Intraday Hits (+35 pt Illusion)

In earlier iterations, the benchmark reported deceptively high scores (75–82) because the ratchet formula included an unearned intraday metric:
$$\text{intraday\_hit} = (\text{high} > \text{open}) \quad \text{for UP}$$
Because the S&P 500 daily high exceeds the open price on $>97\%$ of trading days, models were awarded $+35.0$ free points regardless of predictive skill. Removing this artifact exposed the raw underlying reality: **the models had virtually no true directional edge over a random walk**.

### 4. Severe Information Horizon Asymmetry (09:15 AM Cutoff vs 4:00 PM Close)

Local autoresearch strictly enforces zero lookahead at 09:15 AM ET:
- At 09:15 AM ET, NYSE opening order imbalances, the 09:30 AM opening bell volume, and European morning close rotations have not yet occurred.
- Between 09:15 AM and 4:00 PM ET (6.75 hours), major new information enters the market: 10:00 AM macro releases (ISM, Consumer Confidence), Fed speaker commentary, 1:00 PM Treasury auctions, and late-day institutional market-on-close (MOC) imbalances.
- Forecasting 4:00 PM close direction from a pre-market static snapshot without continuous intraday recalculation is an inherently low-signal problem bounded by efficient market dynamics.

### 5. Semantic LLM Categorization vs Quantitative Order Flow

Jev (`~typesafe/jev-latest`) is a natural language decision model. When Qwen pruned all 15 newsletters to eliminate narrative noise, the payload was reduced to:
- A single 10-year Treasury yield print.
- Prior session VWAP and CLV.
- Pre-market proxy quotes (`QQQ`).

Asking a large language model to perform semantic reasoning on five numerical lines produces fuzzy text pattern matching, not quantitative signal generation. Without options dealer positioning (gamma flip levels), market depth (Level 2), or volatility surfaces, the model lacks the state space required to forecast directional drift.

---

## What Actually Generalizes: Selective Momentum Alignment

The only variant that preserved edge on the Locked Vault was **`qwen-jev-ad283a`** (Batch 7: `trend-exhaustion`):
- **Traded Win Rate**: **55.6%** (41 / 73 days).
- **Gated Out**: 30 days (29.1% of days rejected as `NO_TRADE`).
- **Accuracy Calling UP**: **62.5%** (15 / 24).
- **Accuracy Calling DOWN**: **53.1%** (26 / 49).

Key characteristics of the surviving model:
1. **Trend & Tape Confirmation**: Aligned pre-market gaps ($\le -0.10\%$ on both SPY and QQQ) with prior session institutional accumulation (prior close below VWAP and negative CLV).
2. **Event Risk Hurdle**: Required macroeconomic data to agree with the direction, rather than treating economic data as a directional trigger.
3. **Disciplined Gating**: Refused to trade flat opens, avoiding the 43% chop trap that destroyed the 99%-trade models.

---

## Architectural & Strategic Remediation

To escape the 50%–52% random walk ceiling:

1. **Fix the Objective Function (Selectivity)**:
   - Replace the $+0.10 \times \text{Selectivity}$ term with a minimum hurdle ($>20\%$ trade rate required), but score purely on **Traded Expectancy** or **Traded Information Ratio**:
     $$\text{Score} = (0.75 \times \text{Traded Win Rate}) + (0.25 \times \text{Close Accuracy}) - (\text{Mean Brier} \times 20.0)$$
   - Stop rewarding models for trading flat sessions.
2. **Shorten the Prediction Horizon**:
   - Instead of 09:30 AM $\to$ 16:00 PM (6.75 hours of unobserved noise), predict the **Opening Drive Direction** (09:30 AM $\to$ 10:30 AM) or **First-Hour High/Low Breakout**. Pre-market information decays rapidly after the first 60 minutes of trading.
3. **Incorporate Structural Microstructure Features**:
   - Ingest dealer gamma exposure (GEX), NYSE Tick cumulative volume delta, and morning MOC indications into the feature cache rather than relying solely on EOD bar history.

---

## Related

- [[entities/local-autoresearch]] — the optimization loop where these experiments were executed
- [[concepts/pure-directional-scoring]] — the scoring formula evaluated
- [[concepts/regime-vault]] — the out-of-distribution vault protocol
- [[concepts/locked-vault-kfold]] — atomic weekly grouping and overfit penalty calculation
- [[concepts/confidence-gating]] — mechanism for filtering ambiguous sessions
