---
tags: [concepts, trading, probability, barriers, regimes, quant, triple-barrier]
category: concept
---

# Triple Barrier Touch Probabilities

The Triple Barrier Method, introduced by Marcos López de Prado (2018), replaces fixed-time horizon labeling with dynamic horizontal and vertical barriers. Conditioning these barriers on market regime indicators allows models to calculate empirical hit frequencies before entering positions.

## Background and Motivation

Traditional financial machine learning models label price series by fixed-time returns, such as asking whether price was higher five days later. This ignores the intra-period path:
1. **Intra-candle stop invalidation**: A position that hits a severe adverse move is stopped out in real trading, even if the price later recovers.
2. **Volatile profit targets**: A profitable run that touches a reasonable profit target but subsequently collapses before the end of the window is recorded as a loss or flat return.
3. **Volatility non-stationarity**: A fixed percentage move represents normal noise in high volatility regimes, but an extreme statistical outlier in quiet regimes.

## Architecture and Barriers

The method defines three distinct boundaries around entry price $P_0$:
1. **Upper barrier (Take Profit)**: $P_{upper} = P_0 \times (1 + \text{target\_pct} / 100)$.
2. **Lower barrier (Stop Loss)**: $P_{lower} = P_0 \times (1 - \text{stop\_pct} / 100)$.
3. **Vertical barrier (Time Stop)**: Expiration after $H$ bars if neither price barrier is reached.

When explicit target or stop percentages are omitted, the barriers scale dynamically to local volatility:
- $\text{Target} = 1.5 \times \text{ATR}_{14}\%$
- $\text{Stop} = 1.0 \times \text{ATR}_{14}\%$

## Regime Conditioning

Empirical touch distributions change radically depending on the prevailing state of the market, as shown by Hamilton (1989) and Kritzman et al. (2012). The framework classifies the asset into:
- **Trend regime**: Bullish Trend (price above 20-day SMA with positive SMA slope), Bearish Trend (price below 20-day SMA with negative SMA slope), or Sideways Consolidation.
- **Volatility regime**: High Volatility (ATR percentile > 67%), Low Volatility (ATR percentile < 33%), or Normal Volatility.

Historical occurrences sharing the same regime state are evaluated over a rolling lookback window (typically 252 trading days).

## Tool: `get_barrier_touch_probabilities`

Implemented in `apps/engine/analytics/barrier_probabilities.py` and registered in `packages/config/tools.json` and `CANONICAL_TOOLS_REGISTRY`:

### Parameters
- `ticker`: Stock or ETF ticker symbol (e.g. `SPY`, `QQQ`, `NVDA`).
- `target_pct`: Optional upper profit-take barrier percentage. Defaults to 1.5x local ATR.
- `stop_pct`: Optional lower stop-loss barrier percentage. Defaults to 1.0x local ATR.
- `horizon_bars`: Holding period in daily bars before vertical time stop (default `5`).
- `lookback_days`: Historical days of lookback for regime matching (default `252`).

### Output Metrics
- Empirical win rate percentage (percentage touching upper barrier first).
- Empirical loss rate percentage (percentage touching lower barrier first).
- Vertical expiration percentage and average return when neither barrier is touched.
- Average bars required to touch upper or lower boundaries.
- Expected value after deducting 10 bps round-trip slippage.
- Strategy verdict: `FAVORABLE_LONG`, `FAVORABLE_SHORT`, `RANGE_BOUND_NO_TOUCH`, or `UNFAVORABLE_ASYMMETRY`.

## Related

- [[entities/engine]]
- [[entities/academic-paper-seeding]]
- [[concepts/agent-workflow]]
