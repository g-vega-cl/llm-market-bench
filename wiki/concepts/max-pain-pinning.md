---
tags: [concept, max-pain, options, pinning, gamma, anomaly, 0dte]
category: concept
---

# Options Expiration Pinning (Max Pain)

Options expiration pinning is the empirically observed tendency for heavily traded underlyings to gravitate toward the strike price where the maximum total dollar value of option contracts expire worthless. First documented rigorously by Ni, Pearson & Poteshman (2005) in the Journal of Financial Economics, the anomaly is driven by the dynamic hedging operations of options market makers.

The platform exploits this through the [[entities/max-pain-pinning]] systematic portfolio (`sys-max-pain`), which focuses on daily 0DTE index expirations for SPY and QQQ.

## Market Mechanism

1. **Option Writer Exposure**: Market makers and institutional options underwriters sell calls and puts across diverse strikes. At expiration, option payouts represent a direct cash liability to option writers.
2. **Dynamic Gamma Hedging**: As expiration approaches (especially on 0DTE contracts), option gamma expands rapidly for near-the-money strikes. To maintain delta neutrality:
   - When the underlying price falls below a high open interest strike, market makers must buy stock to cover short deltas.
   - When the underlying price rises above a high open interest strike, market makers must sell stock to cover long deltas.
3. **Magnetic Pinning Effect**: This structural buying below the strike and selling above it acts as a mechanical dampener, pulling the asset price toward the strike with the largest open interest cluster (the Max Pain strike).

## Signals Tracked

- **Max Pain Strike**: Calculated via `calculate_max_pain` from open interest and volume distributions across calls and puts.
- **Convergence Discount**: The percentage gap `(max_pain - spot) / spot`. Admission requires a healthy discount (0.25% to 2.50%) where upward delta hedging pressure is strongest.
- **Put/Call OI Ratio**: Confirms balanced dealer positioning rather than a one-sided blowout.
- **ATM Implied Volatility**: Validates that volatility is sufficiently low to allow gamma pinning rather than an unpinned volatility spike.

## Admission Gate

The quantitative filter is coupled with TypeSafe Jev on the OpenRouter Decisions API (`max_pain_admission`). Jev assesses breaking macro catalysts, FOMC announcements, or unexpected headline shocks, requiring `P(QUALIFIED) >= 70%` to filter out sessions where directional momentum will overwhelm dealer hedging capacity. See [[concepts/jev-decisions-model]].

## Holding Discipline

Positions are strictly intraday with zero overnight exposure:
- **Take-Profit Target**: Exit immediately when the spot price or the session high (`dayHigh` from the FMP `/stable/quote` snapshot) reaches within 0.05% of the verified Alpaca Max Pain strike. On a pin touch the sale fills at the target strike (less 1 bps slippage) even if price has since pulled back, so a wick through the strike is not forfeited.
- **MOC Liquidation**: Mandatory exit window at `min(15:50 ET, session_close − 10 min)` before the expiration bell, evaluated on the MiniPC daemon's 5-minute hooks tick; early closes (e.g. 13:00 ET half-days) liquidate at 12:50 ET. Before the deadline the hook evaluates entries; at/after it forces the exit pass.
- **Same-Session Idempotency**: Once a ticker has entered today (`has_entered_today`), it is not re-entered later in the same session, including after a pin-touch exit.
- **Adverse Stop Loss**: 1.0% drop below entry price to protect against gamma breakdowns.
- **Unliquidated Next-Pass Exit**: Any 0DTE position still open after an exit pass logs `UNLIQUIDATED_MAX_PAIN_AFTER_EXIT_PASS` and is retried on the next 5-minute hook tick. If the book is still open at audit time, [[entities/portfolio-auditor]] flags `UNLIQUIDATED_MAX_PAIN_POSITION`, first tries one live exit pass, then falls back to a modeled exit via the canonical `execute_portfolio_trade` RPC at pass time (never a backdated `BACKFILLED` row).

## Related

- [[entities/max-pain-pinning]]
- [[entities/massive-options]]
- [[entities/macro-options]]
- [[concepts/jev-decisions-model]]
- [[entities/academic-paper-seeding]]
- [[concepts/max-pain-data-sources]]
- [[entities/portfolio-auditor]]
