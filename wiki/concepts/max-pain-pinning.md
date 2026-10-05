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
- **Take-Profit Target**: Exit immediately when the spot price reaches within 0.05% of the Max Pain strike.
- **MOC Liquidation**: Mandatory market-on-close liquidation at 3:50 PM ET before the expiration bell.
- **Adverse Stop Loss**: 1.0% drop below entry price to protect against gamma breakdowns.

## Related

- [[entities/max-pain-pinning]]
- [[entities/massive-options]]
- [[entities/macro-options]]
- [[concepts/jev-decisions-model]]
- [[entities/academic-paper-seeding]]
