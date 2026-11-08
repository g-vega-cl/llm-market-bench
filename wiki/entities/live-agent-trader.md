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
- `fetch_alpaca_news` accepts an optional client; when none is supplied it lazily constructs a `NewsClient` from `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` (or explicit `api_key`/`secret_key` args).
- Every normalized article carries `url`, `tickers`, and a deterministic `source_id_hash` (SHA-256 of `headline|source|event_timestamp[:19]`).
- `normalize_headline` lowercases, strips punctuation, drops stopwords and tokens of length 2 or less; `deduplicate_news` then drops any article whose Jaccard word overlap with an already seen headline is greater than or equal to `similarity_threshold` (default 0.5).
- `aggregate_intraday_news` fans the three providers out with `asyncio.gather(..., return_exceptions=True)`, keeps only list results, and returns the deduplicated combined feed (backfilling `source_id_hash` on any item missing one). Each provider fails soft on missing keys, non-200 responses, or exceptions.
- **Persistence**: `persist_intraday_news(news_items, sb_client=None, evaluate=...)` (in `apps/engine/trading/intraday_news_store.py`) skips stored hashes and near-duplicate headlines from the last 24h, vets each remaining item with Jev, and upserts both `MARKET_MOVING` and `NOISE` items with their real confidence on `on_conflict="source_id_hash"` so rejected `NOISE` headlines are never re-evaluated on subsequent cycles. `execute_intraday_agent_step` calls it after aggregation (see [[entities/intraday-news]]).

### 4. Cascading LLM Inference and Network Topology
`query_multi_tier_llm` implements a two-tier cascade:
- **Tier 1 (Local Strata)**: Primary inference server at `STRATA_BASE_URL` (default `http://primary-workstation:8080/v1`), model `STRATA_MODEL` (default `orcarouter-qwen3.8-flash-next-uncensored-iq3_xxs`), 45s timeout. When running on the edge MiniPC server, Tailscale routes `primary-workstation:8080` to the developer machine.
- **Tier 2 (Centralized CLVG Free Proxy)**: Fallback proxy at `FREE_LLM_PROXY_URL` (default `https://llm.clvg.uk/v1`), model `FREE_PROXY_MODEL` (default `auto-strata`), 75s timeout, invoked on non-200, connection failure, or timeout. Requests are authenticated with an `Authorization: Bearer <master key>` header.
- **Default Client Timeout**: When `query_multi_tier_llm` is called without an injected `http_client`, it constructs its own `httpx.AsyncClient(timeout=120.0)` so the full cascade (45s Strata + 75s free proxy plus overhead) has enough headroom to complete without aborting mid-request.
- **Master Key Resolution**: `query_multi_tier_llm` accepts an optional `fallback_api_key` parameter that takes precedence over the ambient key. When it is not supplied, `_get_free_proxy_master_key()` resolves the key: it first reads the `FREE_PROXY_MASTER_KEY` environment variable, and if unset, falls back to parsing `FREE_PROXY_MASTER_KEY=` out of `apps/free_llm_proxy/.env` (checked at both `apps/free_llm_proxy/.env` and `../../apps/free_llm_proxy/.env` relative paths). If no key is found by either path, the fallback request is sent with **no** `Authorization` header at all rather than an empty bearer token, so the cascade still completes on clean CI runners and unprovisioned hosts.
- **Configurable Token Budget & Reasoning Headroom**: `query_multi_tier_llm` accepts `max_tokens` (default `16384`) and `reasoning_budget_tokens` (default `12288`) parameters applied to both tiers. Callers configure this per task — the conversational explainer passes `16384` and `12288` to guarantee reasoning models (Strata ORCA, Gemini Flash) have ample chain-of-thought room without cutting off markdown commentary, while the news synthesizer passes `800`.
- **Terminal Fallback**: If both tiers fail, a neutral `HOLD` decision JSON is returned so the loop never crashes.

### 5. Agent Turn and Order Routing
`execute_intraday_agent_step` runs one 5-minute turn. It is strictly isolated from audience input — the trader never sees untrusted user text (the audience Q&A is handled by the decoupled worker in [[entities/conversational-explainer]]):
1. Fetch the rolling 120-minute tape and compute the technical snapshot.
2. Aggregate deduplicated news for the ticker (5 per source) and persist it via `persist_intraday_news`.
3. **Retrieve read-only grounding**: `retrieve_read_only_market_data(sb_client, query="", ticker, limit_per_domain=3)` in `apps/engine/trading/read_only_retriever.py` gathers cross-domain context using the production PostgreSQL table and column schemas:
   - `memories` — selects `id, content, importance_score, relevance_score, status, memory_type, target_date, created_at, metadata`, filters with `.eq("status", "ACTIVE")` and with `ilike("content", "%<ticker>%")` (the `memories` table has no `ticker` column), ordered by `importance_score` descending with a `limit_per_domain * 2` fetch window. Post-query filtering drops `ACADEMIC_PAPER` textbooks and expired `CALENDAR_EVENT` rows (`target_date < today`), then truncates to `limit_per_domain` (falling back to the raw rows if filtering empties the list). When the chained `.eq` status builder is unsupported (e.g. an older mock), it falls back to the un-status-filtered `id, content, importance_score, metadata` select ordered by `importance_score`.
   - `cause_and_effect` — selects `id, analysis, market_outcome, confidence, tags`, ordered by `created_at` descending.
   - `trades` — selects `id, ticker, signal, price, reasoning`, ticker-filtered, ordered by `executed_at` descending.
   - `decisions` — selects `id, ticker, signal, confidence, reasoning`, ticker-filtered, ordered by `created_at` descending.
   - `market_barometer_history` — selects `date, pe_ratio, forward_pe, pb_ratio, ps_ratio, earnings_surprise_momentum, pfcf_ratio`, ordered by `date` descending, limit 1.
   - `catalyst_radar` — selects `id, concept_name, catalyst_title, impact, memory_content, target_date`, ordered by `created_at` descending, limit 3.
   `format_read_only_grounding` renders these into lean prompt sections (`### HISTORICAL MEMORIES & LESSONS`, `### CAUSAL CHAINS`, `### RECENT TRADES & AUDIT DECISIONS`, `### MACRO & CATALYST CONTEXT`). The formatter tolerates both production and legacy column names (`analysis`/`cause`, `market_outcome`/`effect`, `signal`/`action`, `price`/`execution_price`, `confidence`/`confidence_score`, `concept_name`/`narrative`, `catalyst_title`/`catalyst`, `impact`/`urgency`), and renders barometer valuation ratios (P/E, forward P/E, earnings-surprise momentum) when present, falling back to score/status/regime. It also tolerates explicit NULL values in any column (e.g. `trades.reasoning`, `memories.content`, `importance_score`, `price`, `confidence`), coercing them to empty strings or zero defaults so live rows never crash formatting.
4. Build a lean system prompt enforcing a strict JSON contract (`action`, `conviction`, `thought`, `allocation_pct`, `memories_consulted`) plus a user prompt with the tape snapshot, headlines, and grounding sections. No audience inquiry block is ever injected into the trader prompt.
5. Parse the response with `_extract_json_decision`, which strips code fences, falls back to a greedy regex match, and finally to a neutral `HOLD`. On a failed JSON parse it now salvages the `thought` string via a targeted regex (un-escaping quotes/newlines) rather than dumping raw JSON, defaulting to `"Technical tape evaluated; maintaining disciplined position."` when no thought is recoverable.
6. **20% Portfolio Target Exposure & Dual-Layer Execution**: Implemented in `apps/engine/trading/intraday_portfolio.py` for owner `live-spy-trader`:
   - **Target Equity Sizing**: `compute_intraday_trade_sizing` enforces a strict 20% portfolio equity cap in SPY (`cash_balance + shares * current_price`). On `BUY`, it calculates the dollar deficit to reach 20% equity and purchases that quantity of shares. If current holdings are already at or above 20%, it returns a `HOLD` no-op.
   - **Full Liquidation on SELL**: On `SELL`, the trader liquidates 100% of currently held SPY shares back to cash.
   - **Session Gating**: Real executions in Supabase and Alpaca occur strictly during regular market hours (`09:30 AM - 04:00 PM ET`). Off-hours turns continue tape analysis and Q&A without altering positions.
   - **Dual-Layer Ledger Persistence**: `execute_intraday_portfolio_turn` immediately updates Supabase tables (`trades`, `portfolio_positions`, `portfolios`, and `portfolio_performance` mark-to-market snapshots) and mirrors to an Alpaca paper `MarketOrderRequest` when `alpaca_trading_client` is supplied.
   - **UI Presentation**: `LiveAgentConsole.tsx` renders a recessed `.voxel-trough` portfolio telemetry summary (`ConsolePortfolioStrip.tsx`) displaying Total Equity, Cash Balance, SPY Holdings, and Unrealized PnL. Executed trades are fetched via `fetchTodayLiveTraderTrades` and plotted directly onto `SPYCandlestickChart.tsx` as green/red marker triangles. The `live-spy-trader` model is registered in `packages/config/models.json` and featured in the homepage Active Portfolios leaderboard.
7. Persist the turn into `market_feeling` (`sentiment_label`, `confidence_score`, `why_explanation`, `market_direction`, `primary_concern` for RSI and trend, `secondary_concern` for VWAP, `trades_summary` payload with action, allocation, order id, technicals, memories, news count, bar count, model attribution, plus `queue_item_id` and `audience_question` — both now always `None` since the trader no longer dequeues audience questions). When a `news_summary` argument is supplied or a cached synthesis exists (`get_latest_news_synthesis()`), the row also carries `news_summary`. The `trades_summary` payload also carries the full `bars` array of real 1-minute candles, which is what the Home page chart renders from. The returned step result exposes `queue_item_id` (always `None`).

### 6. Edge Daemon Runner and Deployment
`apps/engine/trading/runner.py` drives the background loop:
- `is_market_session_active`: Checks if current Eastern Time is Monday through Friday between 09:30 AM and 04:00 PM.
- `calculate_seconds_to_market_open`: Calculates remaining seconds until the next 09:30 AM ET market open.
- `run_loop(..., continuous_24_7=True)`: In 24/7 mode (the default) the loop never sleeps for the market close. When the session is closed it still runs an evaluation turn every 300 seconds, but passes `alpaca_trading_client=None` so paper order submission is skipped — the agent keeps analyzing news, reviewing memories, and answering audience questions. When the session is open the real trading client is passed and orders execute normally. Passing `--no-24-7` restores the legacy behavior of sleeping until the next market open.
- **Concurrent Tasks**: `run_loop` gathers four concurrent tasks — `tape_task` (20s Alpaca tape poller + SSE broadcaster), `agent_task` (5-minute autonomous trader turn), `qa_task` (5-minute conversational explainer worker), and `news_synth_task` (30-minute AI news synthesis worker).
- **HTTP Client Timeouts**: Long-running worker loops configure appropriate HTTP client timeouts — `_run_agent_loop` and `run_news_synthesis_worker_loop` use 90.0s, while `run_qa_worker_loop` uses 120.0s to give Tier 1 Strata (45s) and Tier 2 proxy fallback (75s) full non-overlapping headroom.
- Dockerized in `docker/archive/Dockerfile.trader` and configured as `live-spy-trader` in `docker/archive/docker-compose.secondary.yml`.
- `docker/archive/deploy_secondary.sh` syncs the runner, dependencies, and configuration to the edge MiniPC server (`cv-minipc@minipc`).

### 7. Real-Time Tape Streaming & MiniPC Edge Gateway
To provide instant live candlestick updates without draining client battery or running unneeded LLM evaluations, the live tape architecture is decoupled into a 20-second edge streaming service and a 5-minute autonomous LLM turn:

- **Edge Tape Streaming Server (`apps/engine/trading/tape_stream.py`)**:
  - `TapeBroadcaster`: Thread-safe, in-memory pub/sub broker managing client queues for active candlestick bars and technical snapshots.
  - `TapeHttpServer`: Lightweight `asyncio.start_server` running on port 8090 on the MiniPC edge gateway (`live-spy-trader` container), exposing `/api/tape/health` and `/api/tape/stream` (Server-Sent Events) with CORS support.
  - Client connections receive an immediate `snapshot` event with the rolling 60-minute bars, followed by real-time `bar` events as 1-minute candles form, and periodic keepalive pings every 15 seconds. Client TCP disconnects are detected concurrently via `reader.read(1)`.
  - Reverse proxied via Nginx (`proxy_buffering off;`) across edge hosts and the Cloudflare tunnel.
- **Background Tape Poller**: In `apps/engine/trading/runner.py`, `run_tape_poller_loop` polls Alpaca 1-minute bars every 10 seconds during regular market hours (and pre-seeds existing tape from `market_feeling` on daemon start), broadcasts to connected SSE subscribers, and updates `market_feeling` in PostgreSQL (`update_latest_tape_in_db`) without modifying agent LLM analysis fields. The 5-minute autonomous reasoning loop also broadcasts `agent_turn` events via `publish_agent_turn` so frontends receive real-time action, thought trace, and conviction updates.
- **Client Reactive Streaming Hook (`apps/web/src/features/home/hooks/useLiveTapeStream.ts`)**:
  - Manages real-time connection to `/api/tape/stream` with zero client-side HTTP polling intervals.
  - `mergeIncomingBar`: Pure algorithmic merge that updates the active forming bar in-place if timestamps match the current minute, or appends a new bar and rolls off the oldest bar to maintain a strict 60-minute window.
  - **Tab Visibility Sleep Guard**: Listens to browser `visibilitychange` events; if the tab is backgrounded or minimized, the SSE connection is immediately closed to eliminate battery drain, automatically reconnecting when the tab becomes visible again.
- **CSR Island in SSR Page**: The home page remains server-side rendered (`routes/index.tsx`) for fast TTFB and SEO, but `LiveAgentConsole` acts as a client-side rendered (CSR) reactive island. `SPYCandlestickChart.tsx` guarantees zero layout shift (CLS) by always rendering fixed SVG viewport dimensions and reference grid coordinates even while initial bars are loading.
- **Manual Tape Refresh**: An explicit `Refresh Tape` button triggers an on-demand tape snapshot fetch from the server.

### 8. Decoupled Conversational Desk & Audience Chat Queue
- Schema defined in `supabase/migrations/20261029140000_create_agent_chat_queue.sql` (`public.agent_chat_queue`), extended by `supabase/migrations/20261029220000_add_pop_next_queue_item_rpc.sql`, and decoupled from local auth stubs by `supabase/migrations/20261030190000_decouple_agent_chat_queue_auth_fk.sql`.
- Columns: `id`, `user_id` (Supabase Cloud user UUID; foreign key to local `auth.users` dropped to allow cloud authentication), `display_name` (default `Visitor`), `message`, `status` (`pending`, `injected`, `answered`, `archived`, `rejected`, default `pending`), `created_at`, `injected_turn_at`, `agent_response`.
- Indexes: `(status, created_at ASC)` for queue polling and `(created_at DESC)` for timeline display.
- RLS enabled with public `SELECT` for visitor queue visibility and `service_role` full access; `INSERT` is restricted to `service_role` execution via server functions validating Supabase Cloud session cookies.
- **Architectural Decoupling**: Rather than injecting untrusted user text into the live trading runner's decision prompt, the audience queue is strictly decoupled into a dedicated **Conversational Desk Explainer** (`apps/engine/trading/conversational_explainer.py`, see [[entities/conversational-explainer]]). The autonomous trader evaluates tape, news, and benchmark grounding with zero audience input, while a concurrent 5-minute QA worker queries relevant memories, recent trades, and macroeconomic precedents to answer community inquiries in articulate Markdown prose.

### 9. 30-Minute AI News Synthesis Worker
`run_news_synthesis_worker_loop(sb_client, strata_url, cheap_proxy_url, interval_seconds=1800)` runs a background loop that keeps a rolling institutional market brief fresh:

- **`synthesize_recent_news(...)`** reads the latest `limit` (default 15) rows from `intraday_market_news` filtered strictly to `jev_choice = "MARKET_MOVING"` (Jev-vetted catalysts only — rejected `NOISE` headlines never feed the synthesis prompt), ordered by `event_timestamp` descending, formats them as `- [source] headline` bullets, and prompts the two-tier cascade (`query_multi_tier_llm`, `max_tokens=800`) to produce a concise 2-3 sentence institutional intelligence summary highlighting dominant themes, sector rotation, or immediate risk catalysts.
- The worker loop owns a shared `httpx.AsyncClient` with a `90.0`-second timeout, giving the two-tier cascade (12s Strata + 75s free proxy plus overhead) enough headroom to complete without aborting mid-request.
- The cleaned summary is cached in-process via `set_latest_news_synthesis()` (readable through `get_latest_news_synthesis()`) and written to the newest `market_feeling` row's `news_summary` column.
- Empty results, missing news rows, or an `"All LLM endpoints currently unavailable"` fallback resolve to `None` (no write).
- The loop is scheduled by `run_loop` as `news_synth_task` and its cadence is configurable via the `--news-interval` CLI flag (default `1800` seconds).

### 10. 30-Minute Audit Harness
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
`apps/web/src/routes/index.tsx` builds the agent state server-side via `buildAgentState(marketFeeling, tradesPayload)`, deriving `action`, `conviction`, `thought`, `marketDirection`, `sentimentLabel`, `modelUsed`, `lastUpdated` in Eastern Time, `timestamp` (the raw ISO `created_at`), `technicals`, and `memoriesConsulted` from the latest `market_feeling` row and its `trades_summary` payload. The route component merges `Route.useRouteContext().user` into the payload as `currentUser`, which `HomePage` forwards to `LiveAgentConsole`. The Home page's first block renders `LiveAgentConsole` inside the `home-block-feeling` test id, receiving real Alpaca bars directly from `tradesPayload.bars` with `isRegularMarketHours()` supplying session state.

The console header ribbon (`ConsoleHeaderRibbon`) renders market bias and action telemetry inside a recessed `voxel-trough` (`data-testid="console-telemetry-trough"`) as compact `text-xs font-mono` text — a square pixel dot plus `BIAS:`/`ACT:` labels — rather than `Badge` elements. Direction and action colors are resolved from `DIRECTION_COLOR_MAP` (`BULLISH` → `text-success`/`bg-success`, `BEARISH` → `text-danger`/`bg-danger`, `NEUTRAL` → `text-boxel-ink`/`bg-boxel-muted`) and `ACTION_COLOR_MAP` (`BUY` → `text-success`, `SELL` → `text-danger`, `HOLD` → `text-boxel-muted`), so the header never inherits the Cheddar Gold action fill.

The console no longer renders a standalone technicals row: VWAP, RSI-14, and trend stay in the `LiveAgentState` payload for stream consumers and `/lab`, but the home console does not surface them (trend is already carried by the header ribbon's `BIAS:` telemetry, and the `HomePage` fallback agent state no longer fabricates VWAP/RSI numbers). The **Intraday Thought Trace** is a three-row stack inside its `voxel-trough`: a standalone Tier 2 title row, a wrapping meta row (`data-testid="thought-trace-meta"`, `flex flex-wrap items-baseline gap-x-2 gap-y-1`) holding the turn timestamp followed by `<ACTION> DECISION`, and the quoted thought itself. The timestamp is single-sourced here — the sentiment/model row above the conviction bar renders only `Model: …` — preferring the pre-formatted Eastern-Time `lastUpdated` and falling back to `formatEasternTime(timestamp)` when only the raw ISO value is present; `Unknown` formatting resolves to no timestamp. Rather than cluttering the header with raw reference badges, memory grounding citations (`memories_consulted`) are quietly indicated in a subtle console footer with direct links out to the Memory Vault (`/memories`) and Research Lab (`/lab`). Immediately below the thought trace is `ConsoleQueueCard`, allowing signed-in audience members to submit hypotheses that are answered by the decoupled desk explainer.

Bars flow through `filterLastBars(bars, 60)` in `apps/web/src/features/home/api/fetch-intraday-tape.ts`, which returns the trailing 60 candles (or an empty array for `null`/`undefined`/non-array input). `SPYCandlestickChart` independently slices its input to the last 60 bars, so the chart never renders more than an hour of tape. There is no synthetic fallback tape — when no live bars exist the chart renders the `Awaiting live SPY market tape...` empty state.

### Intraday Tape API Module
`apps/web/src/features/home/api/fetch-intraday-tape.ts` is the single home for the intraday tape data layer. It exports:

- `MarketFeelingRecord` and `IntradayPayload` interfaces (the `market_feeling` row shape and its `trades_summary` payload).
- `filterLastBars(bars, maxBars = 60)` — trailing-bar slicer.
- `isRegularMarketHours(date)` — weekday 14:30–21:00 UTC session gate.
- `buildAgentState(feeling, payload)` — maps a `market_feeling` row plus its payload into a `LiveAgentState` (action, conviction, thought, direction, sentiment label, model, Eastern-Time `lastUpdated`, raw ISO `timestamp`, technicals, memories consulted).
- `fetchLatestIntradayBars(marketFeeling)` — server-side bar resolution with the most-recent-populated fallback described below.
- `fetchLiveIntradayTape` — a `createServerFn({ method: 'GET' })` returning `{ bars, agentState, isMarketOpen }` for the client poller. It queries the newest `market_feeling` row with a non-null `trades_summary->bars`, builds the agent state, and fails soft to an empty snapshot on any error.

### Latest-Bars Fallback Resolution
Because the newest `market_feeling` row can be written by a turn that persisted no tape (or by a non-trader writer), the homepage loader resolves bars through `fetchLatestIntradayBars(marketFeeling)` rather than reading only the newest row's payload:

1. **Direct payload first** — `filterLastBars(marketFeeling.trades_summary.bars, 60)` is returned immediately when it yields at least one bar.
2. **Most-recent-populated fallback** — otherwise the server database client (`getDbServerClient()`) queries `market_feeling` for `trades_summary`, filtered with `.not('trades_summary->bars', 'is', null)` and ordered `created_at` descending with `limit(1)`, then runs the same `filterLastBars(..., 60)` over that payload.
3. **Fail-soft** — any query error is caught and resolves to an empty bar array, so the console degrades to the `Awaiting live SPY market tape...` empty state instead of failing the homepage render.

This keeps the last real session tape visible across row churn without ever fabricating candles.

## Audience Interactive Queue & 24/7 Operation
- **Database Queue (`public.agent_chat_queue`)**: Schema defined in `supabase/migrations/20261029140000_create_agent_chat_queue.sql`, extended with the atomic `pop_next_queue_item()` RPC in `supabase/migrations/20261029220000_add_pop_next_queue_item_rpc.sql`, and decoupled from local `auth.users` via `supabase/migrations/20261030190000_decouple_agent_chat_queue_auth_fk.sql` (see [[entities/database]]). Statuses are `pending`, `injected`, `answered`, `archived`, `rejected`.
- **Authenticated Submissions**: Gated strictly to logged-in users via `submitAgentQueueQuestion` in `apps/web/src/features/home/api/fetch-agent-queue.ts`, capturing `user_id` as metadata for analytics. `validateQueueMessage` rejects empty/whitespace-only input and enforces a 500-character max (`MAX_QUEUE_MESSAGE_LENGTH`). Unauthenticated submissions throw `UNAUTHORIZED`.
- **Queue Status Polling**: `fetchAgentQueueStatus` returns `{ pendingCount, latestAnswered }` — an exact `pending` count plus the most recent row with a non-null `agent_response` ordered by `injected_turn_at` descending. It fails soft to `{ pendingCount: 0, latestAnswered: null }`.
- **Decoupled Explainer & Memory Grounding**: `apps/engine/trading/conversational_explainer.py` searches memories by keyword (e.g. midterm election calendar events, tariff backlash, and SCOTUS precedents) alongside recent desk positioning in `market_feeling` to deliver well-researched, conversational answers (see [[entities/conversational-explainer]]).
- **Strict Execution Isolation**: Audience questions are completely isolated from the live intraday trader's decision loop. The trader runs 100% data-driven without ever seeing audience inputs, eliminating prompt injection risks into paper portfolio execution.
- **24/7 Continuous Mode**: `apps/engine/trading/runner.py` runs continuous evaluation turns across off-hours and weekends (`continuous_24_7=True`, disable with `--no-24-7`). Off-hours turns pass `alpaca_trading_client=None`, so paper order submission is skipped while the agent continues analyzing news, reviewing memories, and serving the 5-minute QA explainer worker.
- **Frontend Console Card**: `apps/web/src/features/home/components/ConsoleQueueCard.tsx` renders a sign-in CTA for anonymous visitors, a 500-character textarea with live `n/500` counting for authenticated users, the pending queue count (`N in queue` / `Queue open`), and the latest answered turn with the model's commentary rendered through the shared zero-dependency `apps/web/src/components/ui/MarkdownContent.tsx` renderer (bold, headings, `---` rules, tables, nested lists, fenced code; block parsing in `apps/web/src/components/ui/markdown-parse.ts`). The answered-turn view (`AnsweredTurnView`) consolidates the question header into a single clean meta row: the `Question` label sits on the left, while the author handle (`@{display_name}`) and short Eastern Date & Time (`formatEasternDateTime` on `created_at`, e.g. `Nov 3 • 10:42 AM ET`) sit on the right, eliminating redundant turn timestamps and clearly indicating the month, day, and time when the question was submitted. A local `formatTimestamp` helper passes through values already suffixed `ET`/`EST`/`EDT`, otherwise formats via `formatEasternDateTime`, falling back to the raw string when formatting yields `Unknown`. The audience question itself renders in a labeled `Question` block (`data-testid="answered-question"`) with `whitespace-pre-wrap` line-break preservation, `break-words` long-token wrapping, a muted accent left rule, and inline Markdown via `InlineMarkdown`, so multi-line or emphasized questions are formatted instead of dumped as raw text.
- **LLM Outage Fallback Rendering**: The card exports `isOutageFallbackResponse(response)`, which flags a stored `agent_response` as an outage payload when it is empty, contains `"All LLM endpoints currently unavailable"`, or is a JSON object (starts with `{`) carrying both `"action"` and `"HOLD"`. When flagged, the card renders a styled **DESK NOTICE: HIGH SYSTEM VOLUME** panel (warning icon + neutral-stance explanation) instead of the raw text, so emergency trader JSON is never surfaced to the audience. A `React.useEffect` guarded by `trackedErrorIdRef` (deduplicating per `latestAnswered.id`) reports the outage to PostHog via `posthog.captureException(err, properties)` with `err.name = 'AgentLLMOutageError'` and a paired `posthog.capture('agent_chat_endpoint_error', properties)` analytics event (see [[concepts/posthog-stealth-proxy]]).

## Related

- [[entities/intraday-news]]
- [[entities/conversational-explainer]]
- [[entities/investment-chat-gateway]]
- [[concepts/vertical-slice-islands]]
- [[entities/web-app]]
- [[entities/database]]
- [[entities/engine]]
- [[concepts/posthog-stealth-proxy]]
