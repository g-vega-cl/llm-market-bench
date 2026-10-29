---
tags: [trading, agent, live, spy, d3, alpaca, intraday]
category: entity
---

# Live Agent Trader

Autonomous intraday model trader console on the Home page (`apps/web/src/features/home/pages/HomePage.tsx`), replacing the static AI Market Feeling overview with real-time quantitative execution and transparent thought traces. The engine side lives in `apps/engine/trading/live_intraday_agent.py`; the presentation side is `LiveAgentConsole.tsx` + `SPYCandlestickChart.tsx`.

## Architecture

### 1. Market Data & Tape Execution
- **1-Minute SPY Candlestick Tape**: Handled by `apps/web/src/features/home/components/SPYCandlestickChart.tsx` using `d3: ^7.9.0`. Renders 120 minutes of 1-minute candlestick bars with trade execution markers (`.trade-marker` triangles, BUY below the bar / SELL above) and a volume sub-panel (22% of plot height). A `ResizeObserver` keeps the SVG width in sync with its container, and hovering a candle swaps the summary strip to that bar's OHLC/volume.
- **Active Candle Polling**: Real-time 10-second polling pulls the forming 1-minute bar from Alpaca (`fetch_active_candle` in `apps/engine/trading/live_intraday_agent.py`) using `Sort.DESC` with `limit=1`.
- **Rolling Tape Fetch**: `fetch_intraday_bars` pulls a 120-minute window of 1-minute bars (`StockBarsRequest`, `TimeFrame.Minute`) and normalizes them into `{time, open, high, low, close, volume}` dicts.
- **Fallback Tape**: `generateFallbackIntradayBars(count, basePrice)` in `apps/web/src/features/home/api/fetch-intraday-tape.ts` synthesizes a deterministic pseudo-random 120-bar tape (sine/cosine deltas) so the console always renders a chart when no live bars are available.
- **Trading Hours**: `isRegularMarketHours(date)` in `fetch-intraday-tape.ts` gates the console — weekdays only, 14:30–21:00 UTC (09:30 AM to 04:00 PM ET). Outside market hours the interface preserves the latest completed session tape with a `MARKET CLOSED` banner and `Next Session 09:30 ET` label.

### 2. Technical Snapshot
`calculate_technical_snapshot(bars)` computes, from the rolling 1-minute tape:
- **VWAP** — cumulative typical price (`(high + low + close) / 3`) weighted by volume.
- **RSI-14** — Wilder-style average gain/loss over the last 14 deltas (100.0 when average loss is zero and gains exist, 50.0 otherwise).
- **EMA-20** — exponential moving average seeded from the first close.
- **Trend** — `BULLISH` when last close is above both VWAP and EMA-20, `BEARISH` when below both, otherwise `NEUTRAL`.

Empty input returns a neutral snapshot (`vwap 0.0`, `rsi_14 50.0`, `trend NEUTRAL`).

### 3. Multi-Source News & Deduplication
- Implemented in `apps/engine/analysis/intraday_news_aggregator.py`.
- Aggregates headlines across the Alpaca Benzinga wire (`fetch_alpaca_news`), Polygon reference news (`fetch_polygon_news`, `/v2/reference/news`), and Financial Modeling Prep stable stock news (`fetch_fmp_news`, `/stable/news/stock`).
- `normalize_headline` lowercases, strips punctuation, drops stopwords and tokens of length ≤ 2; `deduplicate_news` then drops any article whose Jaccard word-overlap with an already-seen headline is `>= similarity_threshold` (default `0.5`).
- `aggregate_intraday_news` fans the three providers out with `asyncio.gather(..., return_exceptions=True)`, keeps only list results, and returns the deduplicated combined feed. Each provider fails soft (logs and returns `[]`) on missing keys, non-200 responses, or exceptions.

### 4. Cascading LLM Inference
`query_multi_tier_llm` implements a two-tier cascade:
- **Tier 1 (Local Strata)**: Primary inference server at `STRATA_BASE_URL` (default `http://localhost:8080/v1`), model `STRATA_MODEL` (default `orcarouter-qwen3.8-flash-next-uncensored-iq3_xxs`), 12s timeout.
- **Tier 2 (CLVG Free Proxy)**: Fallback proxy at `FREE_LLM_PROXY_URL` (default `https://llm.clvg.uk/v1`), model `FREE_PROXY_MODEL` (default `deepseek-chat`), 20s timeout — invoked on non-200, connection failure, or timeout.
- **Terminal Fallback**: If both tiers fail, a neutral `HOLD` decision JSON is returned so the loop never crashes.

### 5. Agent Turn & Order Routing
`execute_intraday_agent_step` runs one 5-minute turn:
1. Fetch the rolling 120-minute tape and compute the technical snapshot.
2. Aggregate deduplicated news for the ticker (5 per source).
3. Pull the 5 most recent `memories` rows for episodic context.
4. Build a lean system prompt enforcing a strict JSON contract — `action` (`BUY`/`SELL`/`HOLD`), `conviction` (0–100), `thought`, `allocation_pct` (0–25), `memories_consulted` — plus a user prompt with the tape snapshot, headlines, and memory bullets.
5. Parse the response with `_extract_json_decision`, which strips ```json fences, falls back to a greedy `{...}` regex match, and finally to a neutral `HOLD`.
6. **Agency-Driven Sizing**: On `BUY`/`SELL`, the agent reads Alpaca paper cash and sizes `allocation_pct` (clamped 1–25%) into whole shares at the last close, then submits a `MarketOrderRequest` with `TimeInForce.DAY`.
7. Persist the turn into `market_feeling` (`sentiment_label`, `confidence_score`, `why_explanation`, `market_direction`, `primary_concern` = RSI/trend, `secondary_concern` = VWAP, `trades_summary` payload with action/allocation/order id/technicals/memories/news count/bar count, `model_used = "Strata / Cheap-LLM-Cascade"`).

### 6. Console UI
`LiveAgentConsole.tsx` renders the header ribbon (`24/7 Autonomous SPY Trader`, live/closed pulse dot, 5-minute countdown timer), direction and action badges, a `ConfidenceBar` for agent conviction, the candlestick chart, the intraday thought trace, a technicals row (VWAP / RSI / Trend plus `Ref:` memory pills), and the audience queue card.

### 7. Audience Chat Queue
- Schema defined in `supabase/migrations/20261029140000_create_agent_chat_queue.sql` (`public.agent_chat_queue`).
- Columns: `id`, `user_id` (FK to `auth.users`, `ON DELETE SET NULL`), `display_name` (default `Visitor`), `message`, `status` (`pending` | `injected` | `archived` | `rejected`, default `pending`), `created_at`, `injected_turn_at`, `agent_response`.
- Indexes: `(status, created_at ASC)` for queue polling and `(created_at DESC)` for timeline display.
- RLS enabled with public `SELECT` and `INSERT` policies plus full `service_role` access; grants `SELECT, INSERT` to `anon`/`authenticated` and `ALL` to `service_role`.
- Allows human visitors to submit questions or market hypotheses to be injected into the agent's upcoming 5-minute thinking turn. The console card currently renders as a `Coming Soon` teaser.

## Home Page Integration
`apps/web/src/routes/index.tsx` builds the agent state server-side via `buildAgentState(marketFeeling, tradesPayload)`, deriving `action`, `conviction`, `thought`, `marketDirection`, `sentimentLabel`, `modelUsed`, `lastUpdated` (Eastern Time), `technicals`, and `memoriesConsulted` from the latest `market_feeling` row and its `trades_summary` payload. `buildFeelingSummary` retains the legacy feeling shape for other consumers. The Home page's first block now renders `LiveAgentConsole` inside the `home-block-feeling` test id, with `generateFallbackIntradayBars(120)` and `isRegularMarketHours()` supplying defaults.

## Related

- [[entities/intraday-news]]
- [[entities/investment-chat-gateway]]
- [[concepts/vertical-slice-islands]]
- [[entities/web-app]]
- [[entities/database]]
- [[entities/engine]]
