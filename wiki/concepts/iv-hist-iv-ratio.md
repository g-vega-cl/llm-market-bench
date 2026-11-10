---
tags: [concept, options, volatility, implied-volatility, realized-volatility, catalysts]
category: concept
---

# IV / HistIV Ratio (Coiled Spring Radar)

A volatility dislocation screen that compares 30-day ATM Implied Volatility (IV) to 20-day Historical Realized Volatility (HistIV / RV). Extreme ratios signal imminent binary catalysts or severe options overpricing. Implemented in `apps/engine/analytics/volatility_ratio.py` and exposed to agents via the `get_high_iv_ratio_watchlist` pull tool.

## The Ratio

$$
\text{IV/HistIV} = \frac{\text{ATM IV (30d)}}{\text{Realized Vol (20d)}}
$$

## The Regimes

`classify_vol_ratio_regime(ratio)` maps the ratio into one of four regimes:

| Ratio | Regime | Meaning |
| :--- | :--- | :--- |
| `>= 1.8x` | `COILED_SPRING_EXTREME` | Imminent binary event risk or massive unannounced catalyst |
| `1.3–1.8x` | `VOL_RICH` | Elevated uncertainty or rich options premium |
| `0.8–1.3x` | `FAIR_VOL` | Options pricing aligned with historical baseline |
| `< 0.8x` | `VOL_CHEAP` | Complacent options, low implied vol |

## The Tool

`get_high_iv_ratio_watchlist(universe, custom_tickers, min_ratio, limit)` in `apps/engine/tools/technicals_options.py` wraps `get_high_iv_ratio_watchlist_report` in `apps/engine/analytics/volatility_ratio.py`.

Universe scopes:

- `mega_mid` (default): liquid mega-cap and high-beta bellwethers (`SPY`, `QQQ`, `NVDA`, `AAPL`, `MSFT`, `AMZN`, `GOOGL`, `META`, `TSLA`, `AMD`)
- `portfolio`: active holdings from `position_pnl`
- `custom`: comma-separated ticker list
- `all`: portfolio + mega_mid

Tickers are inspected concurrently under an `asyncio.Semaphore(5)` with an 8-second per-ticker timeout, sorted descending by ratio, and capped at `limit` (default 10). The report renders a Markdown table with spot price, ATM IV, HistIV, ratio, IV premium, and regime.

## The Prompt Block

`iv_hist_iv_ratio_coiled_springs` in `apps/engine/autoresearch/prompt_blocks.py` instructs the agent to:

1. Scan for extreme volatility compression/expansion via `get_high_iv_ratio_watchlist` across `mega_mid` or `portfolio`.
2. Treat tickers with `IV/HistIV >= 1.8x` (`COILED_SPRING_EXTREME`) as high-tension setups bracing for imminent binary catalysts (earnings, trials, activist filings) or severe market repricing.
3. Cross-reference `get_catalyst_radar` or `get_ticker_news` to distinguish unannounced catalyst accumulation from excessive panic overpricing.

## Related

- [[entities/tool-registry]] — canonical tool registry
- [[concepts/modular-prompt-blocks]] — modular prompt blocks catalog
- [[entities/engine]] — the engine hosting the analytics module
