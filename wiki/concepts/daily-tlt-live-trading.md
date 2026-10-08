---
tags: [concept, trading, bond, tlt, systematic]
category: concept
---

# Daily TLT Live Trading

Daily TLT live trading is the systematic, close-exit day-trading loop for the iShares 20+ Year Treasury Bond ETF. It is the fixed-income counterpart to [[concepts/daily-spy-live-trading]]: both open a position at the 09:30 ET bell and flatten before the close, but TLT trades a ~17-year duration bond instrument whose price is driven by Treasury yields, Fed expectations, and macro prints.

## Loop

1. **Predict** — pre-market, the [[entities/bond-predictor]] runs a tool-first arena (`gpt-5.6-luna`, `deepseek-v4-flash`, Jev) and writes `UP`/`DOWN` forecasts to `daily_predictions` (ticker `TLT`).
2. **Enter** — `daily-trade --ticker TLT --action entry` submits MOO entries into per-model `sys-daily-tlt-close-{model}` portfolios (long on `UP`, short on `DOWN`).
3. **Exit** — at session close the position is liquidated via the bond close-exit path in [[entities/daily-bond-trading]], realizing open-to-close PnL.
4. **Evaluate & audit** — bottom-up evaluation and the [[entities/portfolio-auditor]] reconcile each model's TLT trades for the session, with idempotent cleanup guarding against double-counting.

## Key Properties

- **Directional bet on the curve** — predictions hinge on yield movement; the strategy is explicitly a duration trade, not an equity-index trade.
- **Tight slippage** — 2 bps modeled friction on the highly liquid TLT ETF.
- **Full-cash sizing** — each model portfolio commits 100% of available cash per session.

## Related

- [[entities/bond-predictor]]
- [[entities/daily-bond-trading]]
- [[concepts/system-portfolios]]
- [[concepts/daily-spy-live-trading]]
