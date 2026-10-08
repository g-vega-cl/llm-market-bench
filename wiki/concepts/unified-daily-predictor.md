---
tags: [web, daily-predictor, ui, spy, tlt]
category: concept
---

# Unified Daily Predictor Interface

The Daily Predictor page (`apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx`) serves both the S&P 500 (SPY) and 20+ Year Treasury (TLT) prediction arenas from a single view. An asset switcher at the top of the page toggles between the two tickers, and the model tabs, header copy, and prediction table all re-render for the selected asset.

## Asset Switcher

`AssetSwitcher` renders two segmented buttons — `📈 S&P 500 (SPY)` and `🏛️ 20+ Year Treasuries (TLT)` — each showing a live count of predictions for that ticker. Selecting a ticker:

1. Updates `selectedTicker` state.
2. Resets the selected model to the first model configured for that ticker.
3. Writes the choice to the URL via `history.replaceState` (`?ticker=TLT`), so the view is shareable and survives reloads.

The `PredictorHeader` swaps its title and subtitle based on the ticker — "Daily S&P Market Predictor" (DeepSeek Flash & MiniMax) versus "Daily 20+ Year Treasury Bond Predictor" (GPT-5.6 Luna, DeepSeek Flash & Jev).

## Per-Ticker Model Configuration

`getPredictorModelsForTicker(ticker)` in `daily-predictions-helpers.ts` returns the model set for a given asset:

- **SPY** (`SPY_PREDICTOR_MODELS`): `deepseek-v4-flash`, `MiniMax-M3`, `~typesafe/jev-latest`
- **TLT** (`BOND_PREDICTOR_MODELS`): `gpt-5.6-luna` (default), `deepseek-v4-flash`, `~typesafe/jev-latest`

The OpenAI model id is read from `@repo/config/models.json` (`OPENAI_MODEL`, falling back to `gpt-5.6-luna`). `PREDICTOR_MODELS` is retained as an alias for `SPY_PREDICTOR_MODELS` for backwards compatibility.

## Filtering and Routing

Predictions are filtered by ticker before model matching; a missing `ticker` field defaults to `SPY`. The route (`/daily-predictions`) validates a `ticker` search param, accepting only `TLT` (anything else falls back to `SPY`), and passes it through as the `initialTicker` prop so deep links open directly on the bond arena.

## Related

- [[entities/daily-market-predictor]] — the SPY prediction arena
- [[entities/bond-predictor]] — the TLT prediction arena
- [[entities/web-app]] — the dashboard that hosts this page
