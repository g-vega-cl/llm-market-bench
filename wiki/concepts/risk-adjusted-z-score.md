---
tags: [scoring, autoresearch, volatility, risk-adjustment, benchmarks]
category: concept
---

# Unified Risk-Adjusted Z-Score

The scoring formula used by the auto-research arena to evaluate weekly portfolio prompt variants. It converts benchmark-relative excess return into a volatility-normalized Z-score, expressed in standard-deviation ($\sigma$) units, so calm and turbulent market regimes are evaluated on equal statistical footing. See [[entities/autoresearch]].

## Formula

$$\text{Composite Excess Return} = 0.4 \times (\text{portfolio} - \text{SPY}) + 0.4 \times (\text{portfolio} - \text{Do-Nothing}) + 0.2 \times (\text{portfolio} - \text{Bond})$$

$$\text{Net Excess Return} = \text{Composite Excess Return} - (\text{max\_drawdown} \times 0.3)$$

$$\text{Weekly Effective Volatility} = \frac{\max(\sigma_{\text{portfolio}}, \sigma_{\text{market}}, 10.0\%)}{\sqrt{52}}$$

$$\text{Score} = \frac{\text{Net Excess Return}}{\text{Weekly Effective Volatility}} \quad (\text{units of } \sigma)$$

Implemented in `compute_score()` in `apps/engine/autoresearch/metrics.py`. The drawdown penalty weight is `DRAWDOWN_PENALTY_WEIGHT = 0.3`; the annualized volatility floor is `VOLATILITY_ANNUAL_FLOOR = 10.0`.

## Composite Benchmark Triad

The composite excess return is measured against three reference portfolios:

- **40% SPY** — passive index exposure (beta benchmark)
- **40% Do-Nothing** — the portfolio's own pre-week snapshot held unchanged (measures whether active trading added value over doing nothing)
- **20% 10Y Treasury Bond** — risk-free hurdle

Separately tracked values in `compute_score()` output: `opportunity_cost_penalty` (portfolio − bond, the risk-free excess) and the Do-Nothing return.

## Why We Added It (Rationale & The Karpathy Ratchet Lockout)

Prior to introducing the Unified Risk-Adjusted Z-Score, prompt variants were evaluated on unnormalized net excess return:

$$\text{Score}_{\text{legacy}} = \text{Composite Excess Return} - (\text{max\_drawdown} \times 0.3)$$

This raw return calculation introduced several systemic failure modes into the Karpathy-style auto-research loop:

### 1. The Karpathy Ratchet Lockout Problem (July 19 Outlier)
Under raw excess return, outlier weeks with elevated macro volatility produced massive percentage returns that permanently locked the baseline ratchet. On the week of July 19, 2026, prompt variant `v20260719-183000` captured a wide market swing and registered an uncalibrated score of `24.16`. Because the Karpathy ratchet only promotes variants that beat the all-time high-water mark, this single turbulent-week score set an impossible hurdle. For subsequent months, dozens of high-quality prompt improvements were discarded because normal market conditions could not generate 24+ percentage points of raw excess return.

### 2. Market Regime Inequality (Calm vs. Turbulent Weeks)
Raw percentage moves expand naturally during turbulent macro regimes and compress during quiet markets. In a low-volatility week where SPY moves $\pm 0.5\%$, an agent demonstrating exceptional stock-picking skill to generate $+1.5\%$ alpha produces a net excess return of only $\sim 0.8\%$. Without volatility normalization, quiet weeks had zero mathematical probability of establishing a baseline, biasing prompt evolution exclusively toward high-beta volatility chasing.

### 3. Idiosyncratic Meme Bet Deflator
If an agent took reckless, concentrated bets on high-beta speculative assets, a lucky tail-risk swing could produce a huge raw return. By setting the denominator to $\max(\sigma_{\text{portfolio}}, \sigma_{\text{market}}, 10.0\%) / \sqrt{52}$, the formula expands the volatility divisor to the portfolio's own volatility whenever $\sigma_{\text{portfolio}} > \sigma_{\text{market}}$. This mathematically deflates unrepeatable meme flukes.

### 4. Annualized Volatility Floor
The $10.0\%$ annualized floor prevents division by near-zero volatility during exceptionally flat trading windows, keeping scores statistically bounded.

## Volatility Normalization Mechanics

The denominator is the *effective weekly volatility*: the larger of the portfolio's realized volatility, the market (SPY) realized volatility, and a 10.0% annualized floor, scaled to a weekly figure by dividing by $\sqrt{52}$.

- **Market-anchored regime normalization**: Dividing by SPY volatility deflates wide beta swings during volatile macro weeks so high-volatility weeks cannot create unrepeatable, runaway baseline scores. In calm low-volatility weeks, precise alpha is scaled up so quiet weeks have an equal shot at beating the ratchet.
- **Idiosyncratic risk deflator**: If an agent takes extreme, reckless bets that exceed market volatility ($\sigma_{\text{portfolio}} > \sigma_{\text{market}}$), the denominator expands to the portfolio's own volatility, deflating lucky tail-risk spikes.

SPY volatility is computed from daily SPY returns over the evaluated week (sample standard deviation $\times \sqrt{252} \times 100$) inside `evaluate_week()` in `apps/engine/autoresearch/evaluator.py` and passed to `compute_score()` as `spy_volatility_pct`.

## Historical Backfill

To resolve the July 19 ratchet lockout and restore active prompt evolution, `apps/engine/scripts/backfill_normalized_scores.py` recalibrated all 35 historical variants stored in Supabase `prompt_experiments.metrics`. The script:
1. Recomputes SPY sample volatility from stored daily price history for each variant's evaluated week.
2. Applies the Z-score formula to recalculate `metrics.score`, `effective_volatility`, and `weekly_effective_volatility`.
3. Recalibrated the July 19 outlier variant from an unmanageable `24.16` into its true statistical baseline of `2.52σ`, unfreezing the Karpathy ratchet across all portfolio tracks.

## Disambiguation Across Auto-Research Loops

The platform runs three independent auto-research loops, each using a domain-specific evaluation metric:

| Research Loop | Target Prompt | Evaluation Metric | Unit |
| :--- | :--- | :--- | :--- |
| **Portfolio Trading** (`apps/engine/autoresearch/`) | `CORE_ANALYSIS_SYSTEM_PROMPT` | Unified Risk-Adjusted Z-Score | $\sigma$ (standard deviation) |
| **Daily SPY Predictor** (`apps/engine/tasks/daily_autoresearch.py`) | `DAILY_PREDICTOR_PROMPT` | 4-Pillar Composite (Close Acc, Intraday Hit, Mag Capture, Brier Penalty) | Points (0–100 scale) |
| **Sector Predictor** (`apps/engine/tasks/predictor_autoresearch.py`) | `SECTOR_PREDICTOR_PROMPT` | Multi-Pillar (Sector Percentile + S&P Alpha Bonus − Brier Penalty) | Points |

## Presentation

The web dashboard exposes the math in [[entities/web-app]] via `ScoreBreakdown` (per-experiment derivation) and `ScoreCalculation` (static formula explanation), both rendering the score with the $\sigma$ suffix. The weekly markdown report emitted by `evaluate_week()` prints the full formula substitution and the resulting Z-score.

## Related

- [[entities/autoresearch]]
- [[entities/autoresearch-arena]]
- [[concepts/multi-track-autoresearch]]
- [[concepts/auto-research-prompt-improver]]
- [[concepts/prompt-experiment-lifecycle]]
- [[concepts/auditability]]
- [[concepts/transparency-standard]]
