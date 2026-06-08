---
tags: [engine, diversification, correlation]
category: source
---

# Source: Correlation Matrix & Diversification

Synthesized from `raw/docs/engine/CORRELATION_MATRIX.md`.

## Takeaways

- **Multi-Window Support (7d, 30d, 60d, 90d)**: Computes Pearson and Spearman correlations and trailing returns over multiple rolling windows (7-day, 30-day, 60-day, and 90-day) for a diverse universe of 71 ETFs and crypto tickers.
- **SMA Smoothing**: Uses a 5-day SMA at window endpoints for windows >= 30 days to reduce noise from single-day volatility spikes. For short windows (7-day), falls back to raw endpoints.
- **7-Day Volatility Warning**: A warning disclaimer is displayed in the UI when the 7-day window is active, as short-term correlations computed over only ~5 trading days are highly sensitive to micro-movements and statistically noisy.
- **Agent Discovery**: Provides the `find_uncorrelated_assets` tool, allowing agents to proactively find diversification opportunities.

## Ticker Universe (71 assets)

| Category | Count | Tickers |
|---|---|---|
| US Sectors | 14 | XLK, SMH, XLE, XLF, XLV, XLY, XLI, XLB, XLU, XLRE, XLC, XOP, XME, XBI |
| US Sub-Sectors | 3 | KRE (regional banks), XRT (retail), XHB (homebuilders) |
| US Broad | 4 | QQQ, VIG, IWM, SPY |
| Intl Developed | 8 | EFA, EWJ, EWG, EWL, EWP, SCZ, BWX, EWA |
| Emerging Markets | 7 | EEM, MCHI, EWZ, EIDO, EPI, INDA, EWY |
| Commodities | 7 | GLD, SLV, PDBC, USO, CPER, UNG, DBA |
| Bonds | 6 | TLT, IEF, LQD, EMB, HYG, AGG |
| Intl Bonds | 3 | BNDX, IAGG, EMLC |
| Real Assets | 2 | VNQ, ICF |
| Dollar | 1 | UUP |
| Crypto | 2 | BTCUSD, ETHUSD |
| Volatility | 2 | VIXY, VIXM |

Added 2026-05-22: South Korea (EWY).

Added 2026-05-13: copper (CPER), natural gas (UNG), agriculture (DBA), high-yield bonds (HYG), aggregate bonds (AGG), EM local currency bonds (EMLC), biotech (XBI), metals/mining (XME), oil E&P (XOP), regional banks (KRE), retail (XRT), homebuilders (XHB), India (INDA), Australia (EWA).

## Related

- [[entities/engine]]
- [[entities/macro-tracker]]
- [[concepts/reasoning]]
