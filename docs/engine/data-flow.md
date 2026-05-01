# Data Flow & Pipeline Reference

Complete walkthrough of the daily pipeline, from newsletter ingestion to trade execution and feedback loops.

## Overview

The pipeline runs on a cron schedule during US market hours (see `.github/workflows/ingest.yml`). Six phases:

1. **Ingestion** — Fetch newsletters, economic calendar, government data
2. **Pre-Analysis** — Market hours check, dust cleanup, macro tracking
3. **Analysis** — Parallel LLM analysis with tool-calling loops
4. **Consensus** — Semantic grouping, event promotion, trend tracking
5. **Execution** — Validation, Reg T checks, trade settlement, attribution
6. **Feedback** — Post-mortem, contrarian analysis, cause & effect

---

## Phase 1: Ingestion

### Newsletter Scraping

**Files:** `apps/engine/ingest/newsletter.py`, `apps/engine/main.py`

1. **Gmail API**: Fetches unread emails from configured financial newsletter senders
2. **Content Extraction**: Parses HTML via BeautifulSoup, decodes base64, normalizes text
3. **Ad Removal**: Gemini Flash identifies and strips sponsored content, preserving financial analysis
4. **Attribution Keys**: Each chunk gets a deterministic `source_id` (MD5 of date+sender+subject) and a SHA-256 `chunk_hash` for deduplication
5. **Storage**: UPSERT into `newsletter_snapshots` table with idempotency via `chunk_hash`
6. **Semantic Monitoring**: Logs warnings if a previously active sender yields 0 valid chunks while others succeed

#### Worked Example: Gmail → hash → Supabase

Concretely, what happens for a single ingestion run with 4 newsletters:

```text
1. service.users().messages().list(q="from:(sender1@... OR sender2@...) newer_than:1d",
                                   maxResults=20)
     → 1 API call, returns 4 message IDs
2. For each ID: service.users().messages().get(id=..., format="full")
     → 4 API calls, returns full payloads (headers + base64url body)
3. extract_email_body() → decode_base64_url() → BeautifulSoup → clean_text()
4. clean_newsletter_content() (Gemini Flash) strips ads
5. generate_source_id(date, sender, subject)
     → "news_<sender_slug>_<md5[:8]>"   e.g. "news_newsletter1_a7f92c4e"
6. generate_chunk_hash(content)
     → SHA-256 of cleaned content (full 64 hex chars)
7. upsert_newsletter_snapshot() into newsletter_snapshots
     (id, source_id, chunk_hash, sender, subject, content, date, ingested_at)
```

The `source_id` is deterministic: re-ingesting the same email produces the same ID, so an UPSERT keyed on it is idempotent. The `chunk_hash` covers the cleaned content body — if a sender re-sends the same article under a new subject, the hash changes and it's treated as a new chunk.

### Economic Calendar

**Files:** `apps/engine/ingest/calendar.py`, `.github/workflows/calendar.yml`

Periodic cron fetches global macro catalysts from Trading Economics. High-importance events are stored as `CALENDAR_EVENT` memories with `is_future_catalyst=true` for Horizon Watch. Importance threshold and cadence: see `ingest/calendar.py` and the workflow YAML.

---

## Phase 2: Pre-Analysis Setup

### Market Hours Check

**Files:** `apps/engine/execution/market_data.py`

Enforces trading only during US market hours (weekdays, holiday-aware) via the FMP market-status API. Uses class-level caching so the API is called once per pipeline run rather than per-validation. TTL constant: `execution/market_data.py`.

### Dust Cleanup

**Files:** `apps/engine/main.py`

Before LLM analysis, the engine auto-sells any position too small to be meaningful relative to portfolio equity. This keeps LLMs from reasoning about negligible holdings. Threshold: see `main.py`.

### Global Macro Tracker

**Files:** `apps/engine/core/macro_tracker.py`

Fetches real-time quotes for a curated set of macro assets (broad equities, international, commodities, yields/indices). For each asset, calculates daily % change vs. its rolling standard deviation and flags `UNUSUAL` / `HIGHLY UNUSUAL` regime shifts when the move exceeds the σ threshold.

The formatted snapshot is injected into every LLM prompt, giving agents "Risk-On/Risk-Off" awareness. Asset list, lookback window, and σ thresholds: `core/macro_tracker.py`.

### Portfolio Initialization

**Files:** `apps/engine/analyze.py`

1. Initializes all agent portfolios and fetches current market prices for all unique holdings in parallel
2. Aggregates historical context (government incentives, lessons learned) via parallel pgvector searches
3. Enforces **calendar strategy context** (Turn of the Month, Payday Anomaly) based on current date

---

## Phase 3: Parallel LLM Analysis

### Batch Strategy

**Files:** `apps/engine/analyze.py`

News chunks are split into batches to avoid output-token truncation and the "Lost in the Middle" phenomenon. Each batch still receives the full portfolio summary, historical context, and market data. All batches execute in parallel via `asyncio.gather`. Batch size: `BATCH_SIZE` in `analyze.py`.

Trade-off: smaller batches give higher per-item precision but less cross-news context; larger batches risk JSON truncation when the structured output exceeds the model's output ceiling.

### Provider SDKs

| Provider | SDK |
|----------|-----|
| OpenAI | `openai` |
| Anthropic | `anthropic` |
| Gemini | `google-genai` |
| DeepSeek | `openai` (official, OpenAI-compatible endpoint) |
| Contrarian / Manager | `google-genai` |

Active model names live in [`packages/config/models.json`](../../packages/config/models.json).

### Modular Handlers

**Files:** `apps/engine/core/llm/handlers/`

Each provider uses a dedicated handler to manage tool-calling idiosyncrasies:

- **`openai.py`** — Standard tool loop
- **`anthropic.py`** — XML-like tool blocks, web search, whitespace filtering for empty text blocks
- **`gemini.py`** — `List[Model]` handling for multiple function calls, Google Search grounding
- **`deepseek.py`** — Thinking Mode with `reasoning_content` preservation across tool iterations, empty content fallbacks

### Active Tools

LLMs can invoke these tools during analysis:

| Tool | Purpose | Mandatory For |
|------|---------|---------------|
| `get_stock_quote` | Verify ticker existence, liquidity, current price | All trades |
| `get_price_history` | Check if news is "priced in" | — |
| `get_position_pnl` | Current unrealized P&L for existing positions | — |
| `calculate_buy_quantity(ticker, %)` | Exact shares based on % of buying power | All BUYs |
| `calculate_sell_quantity(ticker, %)` | Exact shares based on % of position | All SELLs |
| `web_search` | Real-time news verification (Anthropic/Gemini) | — |
| `run_stock_screener` | Find investable assets by sector, cap, beta | — |
| `find_uncorrelated_assets` | Discover diversification pairs | — |

**Tool Enforcement**: The engine performs a mandatory server-side scan of conversation history to confirm that `get_stock_quote` (all trades), `calculate_buy_quantity` (BUYs), and `calculate_sell_quantity` (SELLs) were actually executed via native function calling. Hallucinated or text-only tool usage results in trade rejection with 50% confidence reduction. See [TOOL_ENFORCEMENT.md](./TOOL_ENFORCEMENT.md) for the full 4-layer system.

### Discovery Agent

**Files:** `apps/engine/core/llm/discovery.py`

Before parallel analysis, a specialized `DiscoveryAgent` identifies relevant assets for each market theme:

1. **Mission Start**: Receives market theme + context
2. **Step 1**: Invokes `run_stock_screener` to find candidates, filtered by exchange and a market-cap floor
3. **Step 2** (optional): Uses web search to verify business models and thematic relevance
4. **Step 3**: Synthesizes findings into structured JSON with ticker, name, and reason per asset

Caps (max candidates, max final tickers, exchange filter, cap floor) live in `core/llm/discovery.py`.

**Strategic Framework:**
1. **Identify the Bottleneck** — Who owns the critical infrastructure everyone else needs?
2. **Chain of Events** — If X happens, who are the secondary/tertiary beneficiaries?
3. **Uncrowded Plays** — Mid-cap companies not yet priced in

### Web Search

**Files:** `apps/engine/core/llm/handlers/anthropic.py`, `gemini.py`

Claude and Gemini agents can invoke native web search with automatic citation tracking. Anthropic's web search is a **server tool** — it executes on Anthropic's servers with no client-side tool_result handling.

Toggles, tool versions, and per-request limits are configured via env vars (`ENABLE_*_WEB_SEARCH`, `ANTHROPIC_WEB_SEARCH_VERSION`, `ANTHROPIC_MAX_WEB_SEARCHES`) — see `apps/engine/.env.example` and [WEB_SEARCH.md](./WEB_SEARCH.md).

Web search is disabled in the verification pipeline (focused validation only).

### Structured Extraction

After the tool loop, Instructor + Pydantic enforces strict JSON schema. The engine includes:
- Retry logic (up to 3 attempts with corrective prompting)
- JSON repair (double-encoded strings, extra quotes, embedded JSON)
- Price backfill (queries MarketDataManager if LLM price is missing)

**Ownership Pre-Validation**: Before decisions reach the verification layer, SELL signals for unheld tickers are caught and converted to HOLD with `REJECTED_OWNERSHIP` reasoning.

---

## Phase 4: Consensus & Synthesis

**Files:** `apps/engine/consensus.py`

### Event Consensus Protocol

1. **Semantic Grouping**: Gemini embeddings cluster events by cosine similarity across LLMs.
2. **Weighted Consensus**: Events need a cumulative model weight above the promotion threshold. Impact (BULLISH/BEARISH) determined by weighted majority.
3. **Temporal Deduplication**: New events are checked against the `memories` table within a recency window; near-duplicates are dropped.
4. **Relationship Analysis**: Searches for ancestors and links via `parent_id` as REVERSAL, RESOLUTION, or UPDATE. REVERSALs and RESOLUTIONs auto-mark the ancestor as `RESOLVED` so stale narratives stop polluting future RAG retrievals.
5. **LLM Synthesis**: Unifies naming, extracts `is_future_catalyst`, `future_date`, and `historical_parallel`.
6. **Scenario Analysis**: Requires at least two distinct outcomes with a specific trading plan for each.
7. **Alpha Discovery**: Promoted events trigger `DiscoveryService` → `DiscoveryAgent` to populate the "Investable Assets" section of event metadata.

Source for all thresholds (clustering, dedup, ancestor candidacy, model weights, recency window): `apps/engine/analysis/consensus.py`. The momentum-tracker concept-merge threshold lives in `apps/engine/core/config.py` (`MOMENTUM_SIMILARITY_THRESHOLD`).

### Horizon Watch Filtering

Only events with high importance, `is_future_catalyst = true`, and a future `target_date` appear on the dashboard. Vague timeframes ("later in 2026", broad shifts) are excluded. ISO 8601 dates enforced. Importance cutoff: `apps/engine/analysis/consensus.py`.

### Trend & Momentum Analysis

**Files:** `apps/engine/analysis/momentum.py`

Tracks concept velocity using a hybrid formula: `Momentum = Intensity × Growth`
- **Intensity**: log-scaled mention count (rewards sustained relevance)
- **Growth**: short-window vs. long-window mention rate (rewards recent acceleration)

Semantically similar concepts are merged. Stale concepts decay via half-life. PCA reduces embedding vectors to 2D for the concept map. Window sizes, decay half-life, and merge threshold: `core/config.py`.

---

## Phase 5: Validation & Execution

### Pre-Market Validation

**Files:** `apps/engine/execution/validation.py`, `apps/engine/execution/market_data.py`

| Guardrail | Logic |
|-----------|-------|
| Existence | Ticker found via FMP |
| Price Banding | AI-suggested price within tolerance of current market price |
| Liquidity | Market capitalization above floor |
| Buying Power | Estimated trade cost fits within Reg T buying power |
| Minimum Value | Trade cost above floor (waived for SELL via tool) |
| SMA Floor | Projected SMA stays above safety threshold |

Tunable thresholds (`MAX_PRICE_DEVIATION_PCT`, `MIN_TRADE_VALUE`, liquidity floor, SMA floor): `apps/engine/.env.example` and `apps/engine/core/config.py`. Market data uses a short-TTL cache to absorb redundant calls — TTL constant in `core/config.py`.

### Reg T Margin Validation

**Files:** `apps/engine/execution/reg_t_validation.py`

Validates trades against Regulation T margin rules (Initial Margin, Maintenance Margin, Buying Power, SMA). The 10% minimum position rule is automatically enforced by `calculate_buy_quantity` / `calculate_sell_quantity`.

Full formulas, worked scenarios, and the SMA evolution rules: [account-buying-power-reg-t4-calculations.md](./account-buying-power-reg-t4-calculations.md).

### Trade Settlement

**Files:** `apps/engine/execution/portfolio.py`

Uses a **"Commit at the End"** atomic pattern:

1. **Pre-Trade**: Save decision with `status="VALIDATED"` to obtain `decision_id` (required FK for trades table)
2. **Position Update**: UPSERT into `portfolio_positions` (or DELETE if quantity = 0)
3. **Ledger**: INSERT into `trades` table
4. **Commit**: Only after steps 2-3 succeed, update `cash_balance` and `sma` in `portfolios`
5. **Reg T Recalculation**: Immediately recalculate and persist all margin metrics for dashboard accuracy

This prevents "Phantom Deductions" if the DB connection fails mid-operation.

**Cost Basis**: Uses weighted average method. New avg = (Old Total Cost + New Purchase Cost) / New Total Quantity. See [PNL-CALCULATIONS.md](./PNL-CALCULATIONS.md) for formulas.

**Alpaca Paper Mirror**: Every settled trade is fire-and-forget mirrored to Alpaca's paper API as a DAY limit order with agent-tagged `client_order_id`. Shorting guardrail prevents accidental short positions if the mirror has drifted from the internal ledger.

### Attribution Locking

**Files:** `apps/engine/attribution/service.py`, `apps/engine/main.py`

Two-phase commit establishing bidirectional Decision ↔ Trade links:

1. **Phase 1** (pre-trade): Save decision → get `decision_id`
2. **Trade Execution**: Insert trade with `decision_id` FK → get `trade_id`
3. **Phase 2** (post-trade): Update decision with `status="EXECUTED"` and `trade_id`

Result: machine-auditable path: **News → Reasoning → Decision ↔ Trade**

### Ledger & Performance

**Files:** `apps/engine/execution/portfolio.py`

Daily performance snapshots recorded in `portfolio_performance` table with unique constraint on `(portfolio_id, date)` for idempotency. After snapshot, Reg T metrics are persisted back to `portfolios` table.

### Rejection Preservation

Rejected decisions are never discarded — they're saved to the `decisions` table with a status code so the audit trail is complete. The canonical enum (see `apps/engine/core/audit/checks.py` and `apps/engine/execution/validation.py`):

| Status | Trigger |
|--------|---------|
| `REJECTED_MARGIN` | Reg T validation failed: cost > buying power, SMA floor breach, or min trade value not met |
| `REJECTED_OWNERSHIP` | SELL signal for a ticker not held in the portfolio |
| `REJECTED_REDUNDANCY` | Per-agent semantic overlap with a recent trade (overtrading prevention) |
| `REJECTED_TOOL_USAGE` | Required calculation tool (`calculate_buy/sell_quantity`) not actually invoked |
| `REJECTED_VERIFICATION` | Skeptical Verifier agent rejected the trade |
| `REJECTED_HALLUCINATION` | Tool-use claimed in text but no native function call in conversation history |
| `REJECTED_PRICE_DEVIATION` | AI's price deviates more than 5% from current market price |
| `REJECTED_LIQUIDITY` | Ticker market cap below the configured liquidity floor |
| `REJECTED_MARKET_CLOSED` | Triggered outside US market hours or on a holiday |
| `REJECTED_LIMIT_PRICE` | Limit order price judged unrealistic relative to market |
| `ERROR_PROVIDER` | Provider-side error during execution (network, rate limit, malformed response) |

Non-rejection terminal states: `CREATED`, `VALIDATED`, `EXECUTED`.

**Agent-Specific Redundancy**: Semantic overlap checks are per-agent. If Claude trades NKE on earnings, only Claude is blocked from repeating — other agents can independently act on the same opportunity.

---

## Phase 6: Feedback Loops

### Manager Agent (Post-Analysis)

**Files:** `apps/engine/analysis/post_analysis.py`, `.github/workflows/post-analysis.yml`

At configured intervals after trade execution (multi-tier — short, medium, long horizon):

1. Fetches the current market price for each traded ticker
2. Sends original reasoning + actual outcome to the Manager Agent
3. Generates `LESSON_LEARNED` memories stored in pgvector
4. Future RAG retrievals include these lessons, preventing repeated mistakes

Intervals: `analysis/post_analysis.py`. Workflow cadence: `post-analysis.yml`.

### Contrarian Agent

**Files:** `apps/engine/analysis/contrarian.py`

Runs after primary agents to identify crowded trades and missed risks. Executes contrarian trades in a dedicated portfolio. Uses dependency injection (optional parameters) for testability.

### Cause & Effect Analysis

**Files:** `apps/engine/analysis/cause_and_effect_analysis.py`, `.github/workflows/cause-and-effect.yml`

Periodic retrospective audit:

1. **Semantic Deduplication**: lookback against prior analyses to avoid re-auditing the same narrative
2. **Dynamic Ticker Discovery**: Gemini identifies the most-affected companies/suppliers per event
3. **Causal Attribution**: Compares original Scenario Analysis against actual price data
4. **Storage**: Results in `cause_and_effect` table, creating a searchable playbook

Cadence: workflow YAML. Lookback window and similarity threshold: `analysis/cause_and_effect_analysis.py`.

### Government Tracking

**Files:** `apps/engine/ingest/government.py`

Periodic audit of government incentives and policies. Stores findings as `GOVERNMENT_INCENTIVE` memories with expiry dates. See [government-incentive-quick-ref.md](../reference/government-incentive-quick-ref.md). Cadence: workflow YAML.

### Market Feeling

**Files:** `apps/engine/analysis/market_feeling.py`, `apps/engine/core/llm/minimax.py`

After each pipeline run, MiniMax generates a "How I'm feeling and why" sentiment based on the day's trades, lessons learned, and market events. Displayed on the Today dashboard with confidence bar and direction badge. The UI shows a stale warning when the latest reading is older than the configured freshness window — see `analysis/market_feeling.py`.

---

## Phase 7: Long-Term Memory

**Files:** `apps/engine/memory/store.py`, `apps/engine/memory/embeddings.py`

Decoupled vector storage separates macro context from strategy context:

| Source | Content | Table | RAG Label |
|--------|---------|-------|-----------|
| Market Events | Macro catalysts, geopolitics | `memories` | `[MARKET EVENT]` |
| Trade Reasoning | Specific stock justifications | `decisions` | `[PAST DECISION]` |

- **Embedding provider**: Google Gemini (model + dimensionality in `memory/embeddings.py`)
- **Deduplication**: recency-windowed similarity check before insert (window + threshold in `memory/store.py`)
- **Schema Robustness**: Automated JSON parsing, Pydantic `NaN→None` conversion, expanded catalyst type literals

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `apps/engine/main.py` | Pipeline entry point |
| `apps/engine/ingest/newsletter.py` | Gmail fetching, text processing |
| `apps/engine/ingest/calendar.py` | Economic calendar ingestion |
| `apps/engine/ingest/government.py` | Government policy tracking |
| `apps/engine/analyze.py` | RAG context + LLM orchestration |
| `apps/engine/core/llm/` | Multi-provider LLM clients + handlers |
| `apps/engine/core/macro_tracker.py` | Global macro regime detection |
| `apps/engine/consensus.py` | Semantic grouping, event synthesis |
| `apps/engine/analysis/momentum.py` | Trend velocity, decay logic |
| `apps/engine/analysis/post_analysis.py` | Manager Agent post-mortem |
| `apps/engine/analysis/contrarian.py` | Contrarian Agent execution |
| `apps/engine/analysis/cause_and_effect_analysis.py` | Cause & effect audit |
| `apps/engine/analysis/market_feeling.py` | LLM-driven market sentiment |
| `apps/engine/execution/market_data.py` | Cache-first financial data |
| `apps/engine/execution/validation.py` | Pre-market guardrails |
| `apps/engine/execution/portfolio.py` | Trade settlement, snapshots |
| `apps/engine/execution/reg_t_validation.py` | Reg T margin checks |
| `apps/engine/attribution/service.py` | Decision persistence, attribution |
| `apps/engine/memory/store.py` | pgvector interactions |
| `apps/engine/memory/embeddings.py` | Batch embedding client |
