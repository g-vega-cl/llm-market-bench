---
tags: [engine, diversification, correlation]
category: source
---

# Source: Correlation Matrix & Diversification

Synthesized from `raw/docs/engine/CORRELATION_MATRIX.md`.

## Takeaways

- **90-Day Window**: Computes Pearson and Spearman correlations over a rolling 90-day window for a diverse universe of 70 ETFs and crypto tickers.
- **SMA Smoothing**: Uses 5-day SMA at window endpoints to reduce noise from single-day volatility spikes.
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
