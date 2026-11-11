---
tags: [web, daily-predictor, ui, spy, tlt, stock-picker]
category: concept
---

# Unified Daily Predictor Interface

The Daily Predictor page (`apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.tsx`) serves the S&P 500 (SPY), 20+ Year Treasury (TLT), and Daily Stock Picker arenas from a single view. An asset switcher at the top of the page toggles between the three tickers, and the model tabs, header copy, and prediction table (or stock-pick showcase) all re-render for the selected arena.

## Asset Switcher

`AssetSwitcher` renders three segmented buttons — `📈 S&P 500 (SPY)`, `🏛️ 20+ Year Treasuries (TLT)`, and `🎯 3 UP / 3 DOWN (PICKS)` — each showing a live count of predictions (or stock baskets) for that arena. Selecting a ticker:

1. Updates `selectedTicker` state.
2. Resets the selected model to the first model configured for that ticker (skipped for the `PICKS` tab, which shares one basket filter row).
3. Writes the choice to the URL via `history.replaceState` (`?ticker=TLT`, `?ticker=PICKS`), so the view is shareable and survives reloads.

The `PredictorHeader` swaps its title and subtitle based on the ticker — "Daily S&P Market Predictor" (DeepSeek Flash & MiniMax) versus "Daily 20+ Year Treasury Bond Predictor" (GPT-5.6 Luna, DeepSeek Flash & Jev). The `PICKS` tab bypasses `PredictorHeader` and renders the `DailyStockPicksTab` component directly (see [[entities/daily-stock-picker]]).

## Per-Ticker Model Configuration

`getPredictorModelsForTicker(ticker)` in `daily-predictions-helpers.ts` returns the model set for a given asset:

- **SPY** (`SPY_PREDICTOR_MODELS`):
  - `deepseek-v4-flash`
  - `MiniMax-M3`
  - `~typesafe/jev-latest`
  - `jev-four-regime-champion` ("Jev (Four-Regime Champion)")
- **TLT** (`BOND_PREDICTOR_MODELS`): `gpt-5.6-luna` (default), `deepseek-v4-flash`, `~typesafe/jev-latest`

The OpenAI model id is read from `@repo/config/models.json` (`OPENAI_MODEL`, falling back to `gpt-5.6-luna`). `PREDICTOR_MODELS` is retained as an alias for `SPY_PREDICTOR_MODELS` for backwards compatibility. `SupportedDailyTicker` is the union `'SPY' | 'TLT' | 'PICKS'`.

### Model Matching

Each `ModelConfig` carries a `matches(modelName)` predicate. The curated Jev entry matches only on `four-regime`, so the deprecated `jev-local-autoresearched` tag no longer groups under the champion tab (its historical predictions remain in the database but are not surfaced under the active champion). The baseline Jev entry matches `jev` while explicitly excluding names containing `autoresearch`.

## Curated Manifest & Zero Abstention

For the `jev-four-regime-champion` model, the UI renders specialized visual components:
- **Curated Manifest Card** (`CuratedManifestCard.tsx`): Displays the model's active "Box of Data" configuration, breaking down included/pruned proxies, selected newsletter senders, options positioning, and technical intraday profiles.
- **Zero Abstention Binary Classification**: The model commits strictly to `UP` or `DOWN` on every session (see [[concepts/confidence-gating]]). Amber `NO_TRADE` gating is deprecated and preserved only as a backwards-compatible parser fallback for legacy historical data.

## Daily Stock Picker Tab (`PICKS`)

Selecting the `PICKS` arena renders `DailyStockPicksTab` (`apps/web/src/features/daily-predictions/components/DailyStockPicksTab.tsx`) with the `DailyStockBasket[]` array loaded from `daily_stock_baskets` / `daily_stock_picks` (via `fetchDailyStockBaskets` in `fetch-stock-picks.ts`). The tab provides:

- **Model filter buttons** — `⭐ Consensus`, `DeepSeek Flash`, `MiniMax-M3`, `GPT-5.6 Luna`; the persona filter matches `model_name` by substring (case-insensitive), and `consensus` matches exactly.
- **Performance tiles** — Directional Hit Rate, Net L/S Spread Alpha, SPY Benchmark move, and Excess vs SPY Alpha (all pre-materialized by the engine).
- **Two-column pick showcase** — three UP cards with rank badges and emerald borders, three DOWN cards with rose borders; each card shows the ticker, `confidence% Conviction` badge, ranking, two-line reasoning, and (when evaluated) open→close prices, stock return, and position PnL with a `HIT`/`MISS` badge.
- **Historical basket table** — audited ledger with right-aligned tabular numbers and status badges (see [[entities/daily-stock-picker]]).

## Filtering and Routing

Predictions are filtered by ticker before model matching; a missing `ticker` field defaults to `SPY`. The route (`/daily-predictions`) validates a `ticker` search param, accepting only `TLT` or `PICKS` (anything else falls back to `SPY`), and passes it through as the `initialTicker` prop so deep links open directly on the bond or stock-picker arena.

## Related

- [[entities/daily-market-predictor]] — the SPY prediction arena
- [[entities/local-autoresearch]] — local offline prompt and manifest evolution loop
- [[entities/bond-predictor]] — the TLT prediction arena
- [[entities/daily-stock-picker]] — the 3-UP / 3-DOWN stock selection arena
- [[entities/web-app]] — the dashboard that hosts this page
- [[concepts/jev-decisions-model]] — the Jev classifier and its curated champion track
