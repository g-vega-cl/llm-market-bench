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
3. Writes the choice to the URL via `history.replaceState` — `?ticker=SPY`, `?ticker=TLT`, `?ticker=PICKS` — so the view survives reloads and is shareable. `/daily-predictions` and `/daily-predictions?ticker=SPY` are both valid addresses for the SPY tab; neither redirects.

### Canonical Search (no self-redirect)

`validateSearch` in `apps/web/src/routes/daily-predictions/index.tsx` must round-trip every value the page itself writes. TanStack Router rebuilds the request URL from the validator's result on the server (`loadServerRoute` in `@tanstack/router-core` builds the location with `_includeValidateSearch` and 307-redirects whenever the rebuilt href differs from the requested `publicHref`), so a validator that returned `{ ticker: undefined }` for SPY — the value the switcher wrote — rewrote the URL on every SSR request: the canonical href became `/daily-predictions`, a target with no query at all. Production answered that hop with a `Location` equal to the request, so browsers reported `ERR_TOO_MANY_REDIRECTS` on `?ticker=SPY` only (with any second param the canonical target kept a query and the hop converged in one step). The router side is reproducible from the repo; the edge hop that re-expanded the query-less `Location` is not, so treat that step as the likely explanation rather than a measured fact. A trailing-slash request (`/daily-predictions/`) still canonicalises once to the non-slash form — pre-existing, one hop, no loop.

Current contract: an absent `ticker` key returns `{}` so a cold load stays param-less; `TLT`/`PICKS` pass through; every other present value (including lowercase, empty, and unknown tickers) normalizes to `SPY`, which keeps a normalising redirect target queryful. Regression guard: `apps/web/src/routes/-daily-predictions-search.test.ts` drives a real router (memory history + `buildLocation({ _includeValidateSearch: true })`) so the assertion covers search serialisation, not a hand-rolled copy of it.


The `PredictorHeader` swaps its title and subtitle based on the ticker — "Daily S&P Market Predictor" (DeepSeek Flash & MiniMax) versus "Daily 20+ Year Treasury Bond Predictor" (GPT-6 Luna, DeepSeek Flash & Jev). The `PICKS` tab bypasses `PredictorHeader` and renders the `DailyStockPicksTab` component directly (see [[entities/daily-stock-picker]]).

## Per-Ticker Model Configuration

`getPredictorModelsForTicker(ticker)` in `daily-predictions-helpers.ts` returns the model set for a given asset:

- **SPY** (`SPY_PREDICTOR_MODELS`):
  - `deepseek-flash`
  - `MiniMax-M3.1-Flash`
  - `~typesafe/jev-latest`
- **TLT** (`BOND_PREDICTOR_MODELS`): `gpt-6-luna` (default), `deepseek-flash`, `~typesafe/jev-latest`

The OpenAI model id is read from `@repo/config/models.json` (`OPENAI_MODEL`, falling back to `gpt-6-luna`). `PREDICTOR_MODELS` is retained as an alias for `SPY_PREDICTOR_MODELS` for backwards compatibility. `SupportedDailyTicker` is the union `'SPY' | 'TLT' | 'PICKS'`.

### Model Matching

The baseline Jev entry matches `jev` while explicitly excluding names containing `local` or `autoresearch`. The retired `jev-four-regime-champion` track is no longer a model tab — its historical predictions remain in the database but are not surfaced as a model track. See [[concepts/jev-decisions-model]].

## Filtering and Routing

Predictions are filtered by ticker before model matching; a missing `ticker` field defaults to `SPY`. The route (`/daily-predictions`) validates a `ticker` search param, accepting only `TLT` or `PICKS` (anything else falls back to `SPY`), and passes it through as the `initialTicker` prop so deep links open directly on the bond or stock-picker arena.

## Related

- [[entities/daily-market-predictor]] — the SPY prediction arena
- [[entities/local-autoresearch]] — local offline prompt and manifest evolution loop
- [[entities/bond-predictor]] — the TLT prediction arena
- [[entities/daily-stock-picker]] — the 3-UP / 3-DOWN stock selection arena
- [[entities/web-app]] — the dashboard that hosts this page
- [[concepts/jev-decisions-model]] — the Jev classifier and its retired curated champion track
