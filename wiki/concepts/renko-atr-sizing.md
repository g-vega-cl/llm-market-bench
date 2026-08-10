---
tags: [concept, technical-analysis, renko, atr, quant]
category: concept
---

# Renko ATR Sizing & Reversal Rules

**Renko ATR Sizing** is a quantitative chart filtering methodology that discards time and plots price movements based strictly on Average True Range (ATR) box thresholds.

## Key Principles

1. **Noise Reduction**: Standard time-based candles (1-min, 1-hour, daily) include low-volatility sideways noise. Renko charts construct new bricks only when price traverses an ATR box boundary.
2. **Periodic Locked ATR Snapshot**:
   - Pure dynamic ATR recalculated on every candle distorts past brick geometry retroactively.
   - **Quant Best Practice**: Calculate the 14-period ATR at periodic snapshot intervals, lock the dollar height as the fixed brick size for that period, and update at the next period boundary.
3. **2-Brick Reversal Threshold**:
   - A single brick move in the opposite direction is treated as noise.
   - A trend reversal is confirmed **only when price moves 2 full ATR brick heights** in the opposite direction from the highest/lowest brick close.

## LLM Token Synergy

Renko charts convert continuous price time series into discrete event streams (e.g. `UP brick #44 at $489.39 | Reversal Level: $480.87`). This drastically reduces prompt token overhead while providing high signal-to-noise ratio inputs for LLMs.

## Related

- [[entities/lin-renko-agent]]
- [[entities/engine]]
