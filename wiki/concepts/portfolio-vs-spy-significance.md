---
tags: [portfolio, statistics, benchmark, spy, alpha, significance]
category: synthesis
---

# Portfolio vs SPY: Statistical Significance Audit

Snapshot audit (2026-10-20) of whether any portfolio beats SPY by more than luck. Related: [[concepts/system-portfolios]], [[concepts/significance-funnel]], [[concepts/equal-weighted-returns]].

## Verdict

**No active portfolio is statistically better than SPY.** Of 24 active portfolios, the best raw one-sided p-value is 0.18. After Holm and Benjamini-Hochberg correction, none is below 0.96. Portfolios that are ahead of SPY cannot be told apart from luck.

## Scope: Deprecated Portfolios

A portfolio is labeled **DEPRECATED** when it has made no trade in the 30 days before the audit date, or has never traded. Every portfolio gets a daily equity snapshot even when idle, so snapshot dates cannot identify them. Deprecated portfolios are excluded from the tests and from the multiple-testing correction.

| Deprecated portfolio | Trades | Last trade |
|---|---|---|
| mimo-v2-pro | 1 | 2026-03-25 |
| gpt-5-mini | 77 | 2026-03-25 |
| gemini-3-flash-preview | 151 | 2026-03-25 |
| deepseek-reasoner | 49 | 2026-04-28 |
| gemini-3.1-flash-lite-preview | 25 | 2026-05-08 |
| gemini-3.1-flash-lite | 51 | 2026-08-04 |
| gpt-5.4-nano | 27 | 2026-08-06 |
| contrarian_agent | 321 | 2026-08-14 |
| sys-smid-quality-compounder | 16 | 2026-09-03 |
| sys-frontier-tech | 6 | 2026-09-10 |
| deepseek-v4-pro | 72 | 2026-09-14 |
| MiniMax-M2.7, test_model, claude-haiku-5-5, sys-max-pain | 0 | never |

The three largest "outperformers" in an all-portfolio run (gpt-5.4-nano, gpt-5-mini, deepseek-reasoner) are all deprecated. They were not significant either (best p = 0.09).

## Method

- **Data (read-only)**: daily `total_equity` from `portfolio_performance`, trades from `trades`, SPY closes from `price_history`. Access used the anon key, with no writes and no external API calls.
- **Returns**: daily portfolio return minus SPY return, on snapshot dates that overlap with SPY data. Assumes no deposits or withdrawals.
- **Tests per portfolio**: one-sided paired t-test on daily excess return, block bootstrap, CAPM alpha/beta with Newey-West standard errors, annualized information ratio.
- **Multiple testing**: Holm and Benjamini-Hochberg across the 24 active portfolios.
- **Power**: days needed to detect the observed excess return at alpha=0.05 and 80% power.
- **Validation**: the stats helpers were self-tested on synthetic data. Noise gave a false-positive rate near 5%, and a planted edge was detected.

## Results (active portfolios, top by raw p)

| Portfolio | Days | Trades | Return | SPY | One-sided p | Holm p | Days needed |
|---|---|---|---|---|---|---|---|
| sys-sector-uncorr-7d | 26 | 26 | +6.1% | +1.2% | 0.183 | 1.0 | ~240 |
| gemini-3.5-flash-lite | 53 | 14 | +6.1% | 0.0% | 0.254 | 1.0 | ~940 |
| sys-sector-ls-90d | 18 | 5 | +0.9% | +0.3% | 0.449 | 1.0 | ~8,400 |

Only these three active portfolios are ahead of SPY. The other 21 trail it. Bootstrap and HAC alpha p-values agree.

## Interpretation

- **Chance alone predicts about 1.2 false positives** at p<0.05 across 24 tests. We see none, and the best active p-value is 0.18.
- **Histories are too short.** The `sys-sector-*` portfolios have 18–38 days, the daily TLT portfolios have 7, and the 30d and 90d sector portfolios cover 1–2 holding periods.
- **Selection bias.** Choosing the best of many after the fact overstates its evidence. Autoresearch variants are selected on performance, so their results are not independent.
- **Underperformance is also unproven after correction.** `sys-pead-drift`, `sys-sector-mean-reversion` and `sys-daily-tlt-close-~typesafe/jev-latest` look significantly worse before correction, but none survive it. The last two have 26 and 7 days respectively.

## Re-running

Re-run when histories are longer, ideally 250+ trading days per portfolio. For the sector and bond portfolios, count independent holding periods rather than days. Rank by corrected p-values, not raw returns.
