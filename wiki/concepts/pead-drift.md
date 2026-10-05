---
tags: [concept, pead, earnings, strategy, anomaly]
category: concept
---

# Post-Earnings Announcement Drift (PEAD)

PEAD is the empirically observed tendency for a stock's price to continue drifting in the direction of an earnings surprise for several weeks after the announcement. First documented by Ball & Brown (1968) and refined by Bernard & Thomas (1989), the effect is attributed to the gradual institutional accumulation window (TWAP/VWAP block execution) that follows a strong print — the market under-reacts initially and drifts toward fair value over roughly 15–45 days.

The platform exploits this through the [[entities/pead-drift]] systematic portfolio, which uses a purely mechanical pre-filter plus an LLM admission gate rather than a free-form trading prompt.

## Signals Tracked

- **SUE (Standardized Unexpected Earnings)** — the surprise magnitude scaled by historical surprise dispersion. Admission requires `SUE >= 2.0` (top decile).
- **Revenue surprise** — the top-line must confirm the bottom-line beat.
- **Sloan accrual quality** — operating cash flow must confirm reported earnings; accrual ratio above ~0.10 flags low-quality, one-off-driven beats.
- **Pre-earnings run-up** — a parabolic run-up (>25% in 20 days) disqualifies the candidate as a potential sell-the-news trap.
- **Forward guidance & margins** — captured qualitatively by the Jev gate.

## Admission Gate

The quantitative filter is necessary but not sufficient. TypeSafe Jev evaluates the surprise metrics, margin deltas, and qualitative guidance, requiring `P(QUALIFIED) >= 70%` to filter out guidance traps that pure screening cannot detect. See [[concepts/jev-decisions-model]].

## Holding Discipline

Positions target 10–15 equal-weighted holdings held for 30 trading days (the core drift sweet spot), managed with a 5% trailing ATR stop and a mandatory exit before the subsequent quarterly earnings print. See [[entities/pead-drift]] for the concrete exit-rule implementation.

## Related

- [[entities/pead-drift]] — the systematic portfolio implementation
- [[concepts/earnings-prediction-strategies]]
- [[entities/earnings-alpha]]
- [[concepts/jev-decisions-model]]
