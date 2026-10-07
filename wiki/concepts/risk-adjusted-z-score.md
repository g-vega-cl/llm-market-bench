---
tags: [scoring, autoresearch, volatility, risk-adjustment, benchmarks]
category: concept
---

# Unified Risk-Adjusted Z-Score

The scoring formula used by the auto-research arena to evaluate weekly portfolio prompt variants. It converts a benchmark-relative excess return into a volatility-normalized Z-score, expressed in standard-deviation (σ) units, so calm and turbulent market regimes are compared on equal statistical footing. See [[entities/autoresearch]].

## Formula

$$\text{Composite Excess Return} = 0.4 \times (\text{portfolio} - \text{SPY}) + 0.4 \times (\text{portfolio} - \text{Do-Nothing}) + 0.2 \times (\text{portfolio} - \text{Bond})$$

$$\text{Net Excess Return} = \text{Composite Excess Return} - (\text{max\_drawdown} \times 0.3)$$

$$\text{Weekly Effective Volatility} = \frac{\max(\sigma_{\text{portfolio}}, \sigma_{\text{market}}, 10.0\%)}{\sqrt{52}}$$

$$\text{Score} = \frac{\text{Net Excess Return}}{\text{Weekly Effective Volatility}} \quad (\text{units of } \sigma)$$

Implemented in `compute_score()` in `apps/engine/autoresearch/metrics.py`. The drawdown penalty weight is `DRAWDOWN_PENALTY_WEIGHT = 0.3`; the annualized volatility floor is `VOLATILITY_ANNUAL_FLOOR = 10.0`.

## Composite Benchmark Triad

The composite excess return is measured against three reference portfolios:

- **40% SPY** — passive index exposure (beta benchmark)
- **40% Do-Nothing** — the portfolio's own pre-week snapshot held unchanged (measures whether trading added value)
- **20% 10Y Treasury Bond** — risk-free hurdle

Separately tracked values in `compute_score()` output: `opportunity_cost_penalty` (portfolio − bond, the risk-free excess) and the Do-Nothing return.

## Volatility Normalization

The denominator is the *effective weekly volatility*: the larger of the portfolio's realized volatility, the market (SPY) realized volatility, and a 10.0% annualized floor, scaled to a weekly figure by dividing by √52. This yields two distinct behaviors:

- **Market-anchored regime normalization** — During wild macro weeks (high SPY σ), raw percentage moves expand naturally. Dividing by market volatility deflates wide beta swings, so high-volatility weeks cannot create unrepeatable, runaway baseline scores. In calm low-volatility weeks, by contrast, precise alpha is scaled up so quiet weeks have an equal shot at beating the ratchet.
- **Idiosyncratic risk deflator** — If an agent takes extreme, reckless meme bets that exceed market volatility (σ_portfolio > σ_market), the denominator expands to the portfolio's own volatility, mathematically deflating lucky tail-risk flukes.

The 10.0% floor prevents division by near-zero volatility in exceptionally quiet weeks, keeping scores bounded.

SPY volatility is computed from daily SPY returns over the evaluated week (sample standard deviation × √252 × 100) inside `evaluate_week()` in `apps/engine/autoresearch/evaluator.py` and passed to `compute_score()` as `spy_volatility_pct`.

## Output Fields

The score dict returned by `compute_score()` carries the full derivation: `score`, `excess_return`, `net_excess_return`, `max_drawdown`, `volatility`, `spy_volatility`, `effective_volatility`, `weekly_effective_volatility`, `drawdown_penalty`, `opportunity_cost_penalty`, and the reference benchmark returns.

## Historical Backfill

`apps/engine/scripts/backfill_normalized_scores.py` recomputes stored `prompt_experiments.metrics` under the Z-score formula. It runs dry-run by default (`--commit` to apply), can filter by `--track-id`, recomputes SPY volatility from price history when a stored week range exists, and falls back to a 16.0% annualized default when SPY volatility cannot be recovered.

## Presentation

The web dashboard exposes the math in [[entities/web-app]] via `ScoreBreakdown` (per-experiment derivation) and `ScoreCalculation` (static formula explanation), both rendering the score with the σ suffix. The weekly markdown report emitted by `evaluate_week()` prints the full formula substitution and the resulting Z-score.

## Related

- [[entities/autoresearch]]
- [[concepts/multi-track-autoresearch]]
- [[concepts/auto-research-prompt-improver]]
- [[concepts/weekly-audit]]
- [[concepts/performance-auditing-strategy]]
