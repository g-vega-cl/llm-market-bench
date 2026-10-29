---
tags: [trading, agent, live, spy, d3, alpaca, intraday, edge, runner]
category: entity
---

# Live Agent Trader

Autonomous intraday model trader console on the Home page (`apps/web/src/features/home/pages/HomePage.tsx`), replacing the static AI Market Feeling overview with real-time quantitative execution and transparent thought traces. The engine side lives in `apps/engine/trading/live_intraday_agent.py` and `apps/engine/trading/runner.py`; the presentation side is `LiveAgentConsole.tsx` and `SPYCandlestickChart.tsx`.

## Architecture

### 1. Market Data and Tape Execution
- **1-Minute SPY Candlestick Tape**: Handled by `apps/web/src/features/home/components/SPYCandlestickChart.tsx` using `d3: ^7.9.0`. Renders strictly the last 60 minutes of real 1-minute candlestick bars at a 320px plot height with trade execution markers (`.trade-marker` triangles, BUY below the bar, SELL above) and a volume sub-panel. An interactive HUD above the chart displays live Open, High, Low, Close, Volume, and Eastern Time.
- **Active Candle Polling**: Real-time polling pulls the forming 1-minute bar from Alpaca (`fetch_active_candle` in `apps/engine/trading/live_intraday_agent.py`) using `Sort.DESC` with `DataFeed.IEX`.
- **Rolling Tape Fetch**: `fetch_intraday_bars` pulls rolling 60-minute 1-minute bars using `Sort.DESC` and `DataFeed.IEX` for zero-delay real-time execution, reversing the output so bars are strictly chronological up to the latest formed minute, and persists the full array of real bars into `market_feeling.trades_summary.bars`. Zero synthetic or fake data is ever generated.
- **Trading Hours**: `isRegularMarketHours(date)` in `fetch-intraday-tape.ts` gates the console: weekdays only, 14:30 to 21:00 UTC (09:30 AM to 04:00 PM ET). Outside market hours the interface preserves the latest completed session tape with a `MARKET CLOSED` banner and `Next Session 09:30 ET` label.

### 2. Technical Snapshot
`calculate_technical_snapshot(bars)` computes, from the rolling 1-minute tape:
- **VWAP**: cumulative typical price weighted by volume.
- **RSI-14**: Wilder style average gain and loss over the last 14 deltas (100.0 when average loss is zero and gains exist, 50.0 otherwise).
- **EMA-20**: exponential moving average seeded from the first close.
- **Trend**: `BULLISH` when last close is above both VWAP and EMA-20, `BEARISH` when below both, otherwise `NEUTRAL`.

Empty input returns a neutral snapshot (`vwap 0.0`, `rsi_14 50.0`, `trend NEUTRAL`).

### 3. Multi-Source News and Deduplication
- Implemented in `apps/engine/analysis/intraday_news_aggregator.py`.
- Aggregates headlines across the Alpaca Benzinga wire (`fetch_alpaca_news`), Polygon reference news (`fetch_polygon_news`, `/v2/reference/news`), and Financial Modeling Prep stable stock news (`fetch_fmp_news`, `/stable/news/stock`).
- `normalize_headline` lowercases, strips punctuation, drops stopwords and tokens of length 2 or less; `deduplicate_news` then drops any article whose Jaccard word overlap with an already seen headline is greater than or equal to `similarity_threshold` (default 0.5).
- `aggregate_intraday_news` fans the three providers out with `asyncio.gather(..., return_exceptions=True)`, keeps only list results, and returns the deduplicated combined feed. Each provider fails soft on missing keys, non-200 responses, or exceptions.

### 4. Cascading LLM Inference and Network Topology
`query_multi_tier_llm` implements a two-tier cascade:
- **Tier 1 (Local Strata)**: Primary inference server at `STRATA_BASE_URL` (default `http://primary-workstation:8080/v1`), model `STRATA_MODEL` (default `orcarouter-qwen3.8-flash-next-uncensored-iq3_xxs`), 12s timeout. When running on the edge MiniPC server, Tailscale routes `primary-workstation:8080` to the developer machine.
- **Tier 2 (Centralized CLVG Free Proxy)**: Fallback proxy at `FREE_LLM_PROXY_URL` (default `https://llm.clvg.uk/v1`), model `FREE_PROXY_MODEL` (default `free-auto`), 20s timeout, invoked on non-200, connection failure, or timeout. Requests are authenticated with an `Authorization: Bearer <master key>` header. The master key is resolved by `_get_free_proxy_master_key()`: it first reads the `FREE_PROXY_MASTER_KEY` environment variable, and if unset, falls back to parsing `FREE_PROXY_MASTER_KEY=` out of `apps/free_llm_proxy/.env` (checked at both `apps/free_llm_proxy/.env` and `../../apps/free_llm_proxy/.env` relative paths). If no key is found, the request is sent without an `Authorization` header.
- **Terminal Fallback**: If both tiers fail, a neutral `HOLD` decision JSON is returned so the loop never crashes.

### 5. Agent Turn and Order Routing
`execute_intraday_agent_step` runs one 5-minute turn:
1. Fetch the rolling 120-minute tape and compute the technical snapshot.
2. Aggregate deduplicated news for the ticker (5 per source).
3. Pull the 5 most recent `memories` rows for episodic context.
4. Build a lean system prompt enforcing a strict JSON contract (`action`, `conviction`, `thought`, `allocation_pct`, `memories_consulted`) plus a user prompt with the tape snapshot, headlines, and memory bullets.
5. Parse the response with `_extract_json_decision`, which strips code fences, falls back to a greedy regex match, and finally to a neutral `HOLD`.
6. **Agency-Driven Sizing**: On `BUY` or `SELL`, the agent reads Alpaca paper cash and sizes `allocation_pct` into whole shares at the last close, then submits a `MarketOrderRequest` with `TimeInForce.DAY`.
7. Persist the turn into `market_feeling` (`sentiment_label`, `confidence_score`, `why_explanation`, `market_direction`, `primary_concern` for RSI and trend, `secondary_concern` for VWAP, `trades_summary` payload with action, allocation, order id, technicals, memories, news count, bar count, and model attribution). The `trades_summary` payload also carries the full `bars` array of real 1-minute candles, which is what the Home page chart renders from.

### 6. Edge Daemon Runner and Deployment
`apps/engine/trading/runner.py` drives the background loop:
- `is_market_session_active`: Checks if current Eastern Time is Monday through Friday between 09:30 AM and 04:00 PM.
- `calculate_seconds_to_market_open`: Calculates remaining seconds until the next 09:30 AM ET market open.
- In `--loop` mode: Sleeps until market open if closed. When active, executes `run_daemon_turn` every 300 seconds.
- Dockerized in `docker/archive/Dockerfile.trader` and configured as `live-spy-trader` in `docker/archive/docker-compose.secondary.yml`.
- `docker/archive/deploy_secondary.sh` syncs the runner, dependencies, and configuration to the edge MiniPC server (`cv-minipc@minipc`).

### 7. Console UI and Client-Side Polling
`LiveAgentConsole.tsx` renders the header ribbon (`24/7 Autonomous SPY Trader`, live or closed pulse dot, 5-minute countdown timer, `Polling 20s` status indicator, and manual `Refresh Tape` action), direction and action badges, a `ConfidenceBar` for agent conviction, the candlestick chart, the intraday thought trace, a technicals row (VWAP, RSI, Trend plus memory pills), and the audience queue card.

While the surrounding Home page remains completely server-side rendered (`routes/index.tsx`), `LiveAgentConsole` acts as an active presentation island on the client. It polls `fetchLiveIntradayTape` every 20 seconds, updating the local chart tape and agent thought state without re-rendering or refetching portfolio leaderboards or benchmarks.

- **Local State Seeding**: `currentBars` and `currentAgentState` are initialized from the SSR-provided `bars` / `agentState` props and re-synced whenever those props change, so the server-rendered tape is shown instantly before the first poll lands.
- **`updateLiveTape` Helper**: Wraps the poll in a `try/finally` that toggles `isPolling`, optionally invokes the `onRefreshTape` callback, calls the `fetchLiveIntradayTape` server function, and only overwrites local bars/state when the snapshot returns non-empty data. Failures are swallowed as non-blocking background poll errors.
- **Manual Refresh**: The header `Refresh` button (`voxel-btn`, disabled while `isPolling`) triggers the same `updateLiveTape` path on demand.

### 8. Audience Chat Queue
- Schema defined in `supabase/migrations/20261029140000_create_agent_chat_queue.sql` (`public.agent_chat_queue`).
- Columns: `id`, `user_id` (FK to `auth.users`, `ON DELETE SET NULL`), `display_name` (default `Visitor`), `message`, `status` (`pending`, `injected`, `archived`, `rejected`, default `pending`), `created_at`, `injected_turn_at`, `agent_response`.
- Indexes: `(status, created_at ASC)` for queue polling and `(created_at DESC)` for timeline display.
- RLS enabled with public `SELECT` and `INSERT` policies plus full `service_role` access; grants `SELECT, INSERT` to `anon` and `authenticated` and `ALL` to `service_role`.
- Allows human visitors to submit questions or market hypotheses to be injected into the agent's upcoming 5-minute thinking turn. The console card currently renders as a teaser.

### 9. 30-Minute Audit Harness
`apps/engine/scripts/audit_30min_trader.py` is a standalone instrumented harness that exercises the live trader end-to-end against real feeds (Alpaca, Benzinga, Polygon, FMP stable, Supabase, and the multi-tier LLM cascade) and records per-turn metrics.

- **Turn loop**: `run_30min_audit` computes `total_turns = total_minutes * 60 // turn_interval` (defaults: 30 minutes, 300s interval, ticker `SPY`) and calls `run_single_audit_turn` for each turn, sleeping `turn_interval` seconds between turns.
- **Per-turn instrumentation**: fetches the active candle via `fetch_active_candle` (timed), runs the full `execute_intraday_agent_step`, then verifies persistence by reading back the newest `market_feeling` row (`id`, `created_at`, `market_direction`, `sentiment_label`, `model_used`).
- **Recorded fields**: `turn`, `timestamp_et`, `timestamp_utc`, `ticker`, `active_candle`, `step_duration_seconds`, `action`, `conviction`, `thought`, `order_id`, `technicals`, `db_verified`.
- **Resilience**: an exception in any turn is logged via `logger.exception` and recorded as an error entry rather than aborting the run; intermediate results are written to the output JSON after every turn.
- **Output**: prints a per-turn summary table (Turn, Time ET, Price, Trend, Action, Conviction, Latency, DB) and persists the full JSON to `--output` (default `audit_30min_results.json`).

```sh
PYTHONPATH=apps/engine ./apps/engine/.venv/bin/python3 apps/engine/scripts/audit_30min_trader.py \
  --total-minutes 30 --turn-interval 300 --ticker SPY \
  --output audit_30min_results.json \
  --strata-url http://primary-workstation:8080/v1 \
  --cheap-proxy-url https://llm.clvg.uk/v1
```

## Home Page Integration
`apps/web/src/routes/index.tsx` builds the agent state server-side via `buildAgentState(marketFeeling, tradesPayload)`, deriving `action`, `conviction`, `thought`, `marketDirection`, `sentimentLabel`, `modelUsed`, `lastUpdated` in Eastern Time, `technicals`, and `memoriesConsulted` from the latest `market_feeling` row and its `trades_summary` payload. The Home page's first block renders `LiveAgentConsole` inside the `home-block-feeling` test id, receiving real Alpaca bars directly from `tradesPayload.bars` with `isRegularMarketHours()` supplying session state.

Bars flow through `filterLastBars(bars, 60)` in `apps/web/src/features/home/api/fetch-intraday-tape.ts`, which returns the trailing 60 candles (or an empty array for `null`/`undefined`/non-array input). `SPYCandlestickChart` independently slices its input to the last 60 bars, so the chart never renders more than an hour of tape. There is no synthetic fallback tape — when no live bars exist the chart renders the `Awaiting live SPY market tape...` empty state.

### Intraday Tape API Module
`apps/web/src/features/home/api/fetch-intraday-tape.ts` is the single home for the intraday tape data layer. It exports:

- `MarketFeelingRecord` and `IntradayPayload` interfaces (the `market_feeling` row shape and its `trades_summary` payload).
- `filterLastBars(bars, maxBars = 60)` — trailing-bar slicer.
- `isRegularMarketHours(date)` — weekday 14:30–21:00 UTC session gate.
- `buildAgentState(feeling, payload)` — maps a `market_feeling` row plus its payload into a `LiveAgentState` (action, conviction, thought, direction, sentiment label, model, Eastern-Time `lastUpdated`, technicals, memories consulted).
- `fetchLatestIntradayBars(marketFeeling)` — server-side bar resolution with the most-recent-populated fallback described below.
- `fetchLiveIntradayTape` — a `createServerFn({ method: 'GET' })` returning `{ bars, agentState, isMarketOpen }` for the client poller. It queries the newest `market_feeling` row with a non-null `trades_summary->bars`, builds the agent state, and fails soft to an empty snapshot on any error.

### Latest-Bars Fallback Resolution
Because the newest `market_feeling` row can be written by a turn that persisted no tape (or by a non-trader writer), the homepage loader resolves bars through `fetchLatestIntradayBars(marketFeeling)` rather than reading only the newest row's payload:

1. **Direct payload first** — `filterLastBars(marketFeeling.trades_summary.bars, 60)` is returned immediately when it yields at least one bar.
2. **Most-recent-populated fallback** — otherwise the server client (`getSupabaseServerClient()`) queries `market_feeling` for `trades_summary`, filtered with `.not('trades_summary->bars', 'is', null)` and ordered `created_at` descending with `limit(1)`, then runs the same `filterLastBars(..., 60)` over that payload.
3. **Fail-soft** — any query error is caught and resolves to an empty bar array, so the console degrades to the `Awaiting live SPY market tape...` empty state instead of failing the homepage render.

This keeps the last real session tape visible across row churn without ever fabricating candles.

## Related

- [[entities/intraday-news]]
- [[entities/investment-chat-gateway]]
- [[concepts/vertical-slice-islands]]
- [[entities/web-app]]
- [[entities/database]]
- [[entities/engine]]
