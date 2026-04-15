# Project Overview: AI Wall Street

## 1. Project Summary

### What It Does

An automated platform where four primary LLMs (**OpenAI, Claude, Gemini, DeepSeek**) compete in a virtual stock market, with two meta-agents (**Contrarian Agent, Manager Agent**) reviewing consensus and counter-positioning after primary analysis. Three times a day during market hours (09:30, 12:30, 15:30 ET), they parse financial newsletters, debate major global events, analyze government incentives, and rebalance their portfolios.

**New: Real-Time Web Search** - Agents now have access to live web search (Anthropic `web_search`, Gemini `google_search`) to verify breaking news, check corporate actions, and fact-check claims before trading. All searches include citations for audit trails.

**New: Stock Screener Tool & Discovery Agent** - All primary LLMs can invoke `run_stock_screener` to find investable assets by sector, market cap, beta, volume, and dividends. A specialized `DiscoveryAgent` uses this and web search in a tool-calling loop to populate the "Investable Assets" section of the AI's memory with high-conviction, liquidity-filtered candidates (NYSE/NASDAQ only, max 15 tickers).

### Why It Matters

* **Performance Benchmarking:** Real-world test of LLM reasoning vs. S&P 500.
* **The "Consensus" Effect:** Identifies where AI models agree or diverge on global risks.
* **Research Audit Trail:** Provides a full "Thinking Process" trace for every LLM call, including intermediate tool steps, for behavioral research.
* **Decision Attribution:** Provides a machine-auditable trail from raw news chunk to final trade execution.
* **Memory Integrity:** Tests if LLMs can maintain a consistent world view using Vector RAG (Retrieval-Augmented Generation).

## 2. Technical Architecture & Repo Structure

The project follows a **Monorepo** structure to keep the Python Data Engine and the TypeScript Frontend synchronized while separating concerns.

**Repository Organization:**

```text
llm-market-bench/
├── apps/
│   ├── web/                 # TanStack Start (Dashboard)
│   └── engine/              # Python Data Engine
│       ├── core/            # LLM clients, tools, and config
│       ├── ingest/          # Newsletter & Government data
│       ├── analysis/        # Momentum, Post-Mortems, Contrarian
│       ├── execution/       # Validation (Reg T) & Trade Settlement
│       ├── attribution/     # Decision mapping
│       ├── memory/          # pgvector store & embeddings
│       ├── main.py          # Pipeline entry point
│       └── update_prices.py # Utility
├── supabase/                # SQL Migrations & RLS
├── packages/
│   ├── config/              # Shared configuration (models.json)
│   └── database/            # Generated TypeScript types from Supabase schema
├── docs/                    # Technical Walkthroughs
└── tests/                   # Engine & Web tests
```

> **Type Safety**: Frontend types are generated from the Supabase database schema via `@llm-market-bench/database`. See [supabase/TYPE_GENERATION.md](../supabase/TYPE_GENERATION.md) for regeneration instructions.

## 3. The Daily Pipeline

For a detailed step-by-step walkthrough, see **[data-flow.md](./engine/data-flow.md)**.

### Phase 1: Ingestion & Normalization
1. **Triple Trigger (09:30, 12:30, 15:30 ET):** GitHub Actions fires the pipeline. The engine enforces a **Holiday-Aware Market Hours Check** (via FMP API) and skips execution if triggered outside 09:30-16:00 ET, on weekends, or on US stock market holidays. The market status check uses **class-level caching (5-minute TTL)** to ensure the FMP API is called only once per pipeline run, reducing redundant API calls while maintaining accurate holiday detection.
2. **Pre-Analysis Dust Cleanup:** Before any LLM analysis, the engine automatically sells any positions worth less than 10% of portfolio equity (dust positions). This ensures LLMs never see or manage tiny leftover positions when making allocation decisions. Dust cleanup runs on all active portfolios regardless of whether newsletter data exists.
3. **Newsletter Ingestion:** Scrapes unread emails; removes ads via Gemini Flash.
4. **Corporate Action Check:** *(Not yet implemented — see Roadmap.)*
5. **Economic Calendar Ingestion:** Fetches live events from Trading Economics (bi-weekly).
6. **Data Snapshotting:** Save raw text and current prices with idempotency keys.

### Phase 2: Consensus & Attribution
6.  **Global Macro Tracking**: The engine fetches real-time quotes and historical volatility for 16 key macro assets (Equities, Commodities, Yields/DXY). It identifies **Market Regime Shifts** ($> 2\sigma$ deviation) to provide high-level context before trade generation. See **[GLOBAL_MACRO_TRACKER.md](./engine/GLOBAL_MACRO_TRACKER.md)**.
7.  **Parallel LLM Analysis**: OpenAI, Claude, Gemini, and DeepSeek generate trade signals using active tools. The engine uses a centralized **[PromptFactory](./engine/llm-analysis-walkthrough.md#prompt-factory)** to ensure all agents receive semantically identical instructions while safely adapting to provider-specific requirements. It injects the live **Global Macro Snapshot** into each prompt, ensuring agents recognize "Risk-On/Risk-Off" environments before analysis. It initializes all agent portfolios and fetches current market prices for all unique holdings in parallel before analysis, ensuring consistent and fresh data injection. The engine uses **Modular Handlers** (dedicated logic for each provider) to manage diverse tool-calling behaviors. To ensure output reliability and prevent token truncation, the engine implements **[Asynchronous Chunk Batching](./engine/BatchingStrategy.md)** (processing news in batches of 20).
    -   **Reasoning Models (DeepSeek)**: DeepSeek runs in **Thinking Mode** (CoT reasoning) with a dedicated handler that preserves reasoning context (`reasoning_content`) across tool iterations and handles empty content fallbacks for final structured extraction.
    -   **Web Search Integration**: Claude and Gemini agents can invoke native web search tools to verify time-sensitive information (breaking news, corporate actions, government announcements) with automatic citation tracking. The `PromptFactory` dynamically manages these instructions, stripping them only when search is disabled and preserving them for Gemini when combined tool use is enabled.
8.  **RAG Context Retrieval**: Query `memories` and `decisions` for historical context (labeled to distinguish from current holdings).
9.  **Decision Attribution**: Map reasoning, strategy intent, and metadata to the `decisions` table.
10. **Event Consensus**: Synthesize global macro events with structured **Scenario Analysis** (requiring at least two distinct outcomes AND a specific **Trading Plan** for each); group semantically via pgvector.
    -   **Alpha Discovery Agent (`DiscoveryAgent`)**: During consensus synthesis, when an event reaches the promotion threshold, the `DiscoveryService` automatically delegates asset discovery to the `DiscoveryAgent`. This specialized agent uses a `run_stock_screener` tool-calling loop to convert market themes into a high-conviction candidate list for the "Investable Assets" section of the consensus event's metadata. Enforces NYSE/NASDAQ-only, actively trading, and a 15-ticker cap to ensure liquidity and prevent context bloating. See **[ASSET-DISCOVERY.md](./engine/ASSET-DISCOVERY.md)**.
11. **Trend Analysis**: Calculate concept momentum and update PCA coordinates for the map.

### Phase 3: Execution & Guardrails
12. **Second-Step Verification**: A skeptical "Verifier" agent audits BUY/SELL signals.
13. **Hard Tool Enforcement**: The engine performs a mandatory server-side scan of the conversation history to confirm that required tools (`get_stock_quote` for all trades, `calculate_buy_quantity` for BUYs, and `calculate_sell_quantity` for SELLs) were actually executed via native function calling. The scan is **robust to formatting variances**, automatically stripping whitespace and normalizing casing for tickers to prevent false rejections. Hallucinated or text-only tool usage results in trade rejection.
    - **Multi-Layer Verification**: See [TOOL_ENFORCEMENT.md](./engine/TOOL_ENFORCEMENT.md) for detailed documentation on the 4-layer enforcement system.
    - **Pre-Prompt Strengthening**: All models receive an enhanced unified system prompt (`CORE_ANALYSIS_SYSTEM_PROMPT`) equipped with strict high-fidelity few-shot tool usage examples.
    - **Portfolio Isolation**: The engine guarantees strict portfolio context scoping across batched tasks, preventing state leakage between distinct providers (e.g. Anthropic does not see DeepSeek's holdings).
    - **Confidence Penalties**: Decisions without verified tool calls receive 50% confidence reduction.
    - **Ownership Pre-Validation**: SELL signals for unheld tickers are caught before verification layer.
    - **Provider-Specific Fixes**:
      - **DeepSeek**: Thinking mode support with auto-retry for empty content
      - **Claude**: Max tokens increased from 8K → 32K
      - **Gemini**: `List[Model]` handling for multiple function calls
14. **Pre-Market Validation**: **FMP-Verified Market Hours** (holiday-aware, **cached with 5-minute TTL** to avoid redundant API calls), symbol existence, **5.0% price banding**, and liquidity checks.
15. **Reg T Margin Validation**: Ensure buying power and the $1,000 **absolute minimum trade value** (waived for SELL orders if a specific sell tool is used).
16. **Trade Settlement**: Atomic updates to cash, positions, and ledger. **Pre-saves decision with `status="VALIDATED"` to obtain `decision_id` for trade foreign key**.
17. **Attribution Locking:** **Two-phase commit** - links `TradeID` to decision after execution, completing the bidirectional `Decision ↔ Trade` link.
18. **Ledger Update:** Daily equity curve snapshot.

### Phase 4: Feedback & Specialized Agents
19. **Post-Analysis (Manager Agent):** Compare reasoning to multi-interval performance; generate lessons.
20. **Contrarian Agent:** Identifies crowded trades or missed risks.
21. **Skeptical Verifier Agent:** Performs just-in-time audits of every trade signal.
22. **Government Tracking:** Monthly audit of incentives and policies.
23. **Cause & Effect Analysis:** Bi-weekly audit of market events to track predicted vs actual impact (Tuesdays & Fridays). Now includes **Semantic Deduplication** (pgvector) to prevent redundant analysis and **Dynamic Ticker Discovery** (via FMP API) to identify sector proxies, ETFs, and derivative play tickers for any market theme, powering the 'How to Profit' feature.
24. **Economic Calendar Ingestion:** Twice-weekly fetch of global macro catalysts from Trading Economics (Sundays & Wednesdays).

### Phase 5: Market Execution (Sequential)

**12. Second-Step Verification** ✅

*   **Tech:** Python / Multi-Provider Tool Loop
*   **Logic:** *Every BUY/SELL signal is intercepted by a dedicated verifier.*
*   **Dynamic Provider**: *The verifier uses the **same intelligence profile** (e.g., Anthropic, Gemini) as the original generator.*
*   **Skepticism SOP**: *Checks if news is "priced in" via history, identifies at least two failure modes, and searches for "Silver to our Gold" alternative plays using **Vector-Based Sector Analysis**. Crucially, it now **audits the agent's strategic reasoning** (e.g., "sell X to fund Y") for logical consistency. It also validates adherence to **Calendar & Seasonal Strategies** (Turn of the Month, Payday Anomaly, etc.) by analyzing the injected current date context.*

*   **Robust Tooling**: *Universal tool implementation supports complex structured outputs (Anthropic) and safe content parsing (Gemini), enabling diverse models to act as verifiers. The verification layer uses **Modular Provider Handlers** (e.g., `openai.py`, `deepseek.py`, `anthropic.py`) and the **PromptFactory** to handle idiosyncratic behaviors while maintaining a single source of truth for the verifier's skeptical mindset. It is designed with **Sync/Async Resilience**, safely handling both native Google SDK response objects and asynchronous patterns.*
*   **Market Data Fallback & Robustness**: *Uses an enhanced `MarketDataManager` that automatically pulls historical prices from **FMP** (with YFinance fallback) if local data is missing for a new ticker. To optimize performance, the engine uses **Batch Upserts** when saving historical prices to Supabase, reducing network overhead significantly. For ETFs (like `BDRY`), the engine accurately evaluates liquidity by falling back to `totalAssets` or `netAssets` when `marketCap` is unavailable. The engine uses a **Singleton Connection Pattern** (with robust `finally` cleanup) for providers that require persistent connections, ensuring high-concurrency tool loops never result in port conflicts. It also implements a unified **`ensure_list`** wrapper to resiliently handle both single and multi-block LLM responses. The **Anthropic handler** (`handlers/anthropic.py`) filters whitespace-only text blocks before building the message history, preventing `400 Bad Request: text content blocks must be non-empty` errors. The **FMP provider** (`execution/providers/fmp.py`) correctly passes the ticker as a query parameter to the `historical-price-eod/full` endpoint and handles both flat-list and nested `"historical"` response shapes, resolving prior `404` errors for tickers like `SMCI` and `OIH`. Crucially, it integrates a **FMP-driven Market Status check** with **class-level caching (5-minute TTL)** to enforce trading only during active US market hours, including automatic holiday detection. This ensures the market status API is called only once per pipeline run, reducing redundant API calls by ~99%.*
*   **Outcome**: *Approves, rejects, or shrinks the trade allocation based on price risk and strategic intent.*

**13. Pre-Execution Margin Validation** ✅

*   **Tech:** Python / Supabase / Reg T Logic
*   **Logic:** *Before moving a decision to "Trade Settlement", the engine validates that the agent has sufficient Buying Power.*
*   **Rule:** *Check `portfolio.buying_power` against the estimated cost of the trade. If `Cost > Buying Power`, or if the limit order price submitted by the LLM deviates by more than **5.0%** from current market data, reject the trade to prevent execution based on stale or hallucinated prices.*
*   **Persistence:** *Portfolios are stored in `portfolios` and `portfolio_positions` tables to maintain state across daily runs.*
*   **Portfolio Context Injection**: LLMs receive their current Cash, Equity, and Buying Power in the prompt, along with real-time market prices for all holdings (fetched in parallel before analysis), allowing them to make **"Allocation %"** decisions for BUYS. For ALL trades (BUY or SELL), LLMs are now REQUIRED to use calculation tools (`calculate_buy_quantity` or `calculate_sell_quantity`) to determine the exact share quantity.
*
*   **Minimum Trade Rule**: Every trade must be at least **10% of Total Equity or available Buying Power** (whichever is larger), with an absolute floor of **$1,000 for BUY orders**. For **SELL orders**, the $1,000 floor is strictly enforced UNLESS the `calculate_sell_quantity` tool is used with a percentage, which allows for precision rebalancing and clearing "dust" positions.
*
*   **10% Minimum Position Rule (AUTOMATIC ENFORCEMENT)**: The system requires every position to be at least 10% of total portfolio equity. 
    - For BUYS: The `calculate_buy_quantity` tool automatically up-sizes the request to meet this floor.
    - For SELLS: The `calculate_sell_quantity` tool automatically mandates a 100% (FULL) sell if the remaining position would fall below the 10% threshold.
    This prevents portfolio pollution from small "dust" positions while providing agents with immediate feedback through the tool response.
*
*   documentation: ./engine/portfolio-management-walkthrough.md

**14. Trade Settlement & Ledgering** ✅

*   **Tech:** Python / Portfolio Class
*   **Logic:** *Execute `portfolio.execute_trade()` for valid decisions.*
*   **Guardrail:** *Enforces **Portfolio Ownership** for SELL signals; if an LLM tries to sell a ticker it doesn't own, the trade is rejected.*
*   **Action:** *Updates `cash_balance`, `sma`, and `portfolio_positions`. **Crucially, inserts a record into the `trades` table to generate a unique `TradeID` for the execution.***
*   **Atomic Settlement Pattern:** *Follows a **"Commit at the End"** logic where `cash_balance` and `sma` are only persisted to the `portfolios` table if both the `portfolio_positions` update and the `trades` ledger entry succeed. This prevents "Phantom Deductions" if the DB connection fails mid-operation.*
*   **Immediate Consistency:** *Recalculates and persists final Reg T metrics to the `portfolios` table immediately after every trade to ensure the dashboard remains accurate between scheduled snapshots.*
*   **Rejection Logic**: Decisions that fail Validation, Reg T, **Ownership**, **Semantic Redundancy** (overtrading prevention), or **Hard Tool Enforcement** (e.g., selling without actually calling a calculation tool in the history) are NOT discarded. They are saved to `decisions` with a status (e.g., `REJECTED_MARGIN`, `REJECTED_OWNERSHIP`, `REJECTED_REDUNDANCY`, `REJECTED_TOOL_USAGE`, `REJECTED_VERIFICATION`, `REJECTED_HALLUCINATION`, `REJECTED_PRICE_DEVIATION`, `REJECTED_LIQUIDITY`, `REJECTED_MARKET_CLOSED`, `REJECTED_LIMIT_PRICE`, `ERROR_PROVIDER`) to preserve the full "Audit Trail" of AI intent.
    - **Agent-Specific Redundancy**: The semantic redundancy check is **agent-specific**. For example, if CLAUDE recently traded NKE on earnings news, only CLAUDE will be blocked from making a similar NKE trade. Other agents (HAIKU, OpenAI, Gemini, etc.) can still trade NKE independently, as they maintain separate portfolios and decision contexts.
*
*   documentation: ./engine/trade-settlement-walkthrough.md

**14a. Real-time P&L Tracking (SQL View)** ✅

*   **Outcome:** Provides live Profit/Loss USD and % for all active positions.

**15. Attribution Locking** ✅
*   **Tech:** Supabase Postgres
*   *Uses a **two-phase commit pattern** to establish bidirectional links between decisions and trades:*
    1.  *Pre-Trade: Save decision with `status="VALIDATED"` to obtain a `decision_id` (required foreign key for the `trades` table).*
    2.  *Trade Execution: Insert trade record with the `decision_id`, generating a `trade_id`.*
    3.  *Post-Trade: Update decision with `status="EXECUTED"` and the `trade_id`.*
*   *We now have a machine-auditable path: **News -> Reasoning -> Decision ↔ Trade**.*
*   documentation: ./engine/attribution-locking-walkthrough.md

**16. Ledger & Equity Curve Update** ✅

*   **Tech:** Supabase Postgres
*   **Action:** *Calculate the new total Net Liquidation Value. Write an immutable row for today's performance.*
*   **Update:** *Crucially, it also updates the main `portfolios` summary table with the final calculated Reg T metrics (Equity, Moving SMA, Maintenance Margin) following all executions.*
*   **Idempotency:** *Enforce database constraints on `(portfolio_id, date)` to ensure performance is never double-counted.*
*   documentation: [step-14-ledger-equity-curve.md](./engine/step-14-ledger-equity-curve.md)

**16a. Price Update Utility (Non-LLM)** ✅

*   **Tech:** Python / `update_prices.py`
*   **Goal:** Refresh market prices and recalculate portfolio metrics without invoking the expensive LLM analysis loop.
*   **Usage:** Use this script to update the dashboard's "Live Equity" and "Buying Power" between daily newsletter ingestions. Automatically triggered every 30 minutes during market hours (approx. 13:30 - 20:00 UTC) via GitHub Actions.
*   **Resilience:** Implements retry logic with exponential backoff (3 retries: 1s, 2s, 4s) for transient Supabase errors (502, 503, 504, timeouts, connection errors).
*   File: `apps/engine/update_prices.py`

**17. Long-term Memory Embedding** ✅

*   **Tech:** **Supabase pgvector (Google Gemini gemini-embedding-001)**
*   **Decoupled RAG:** *The engine separates **Macro Context** (events in `memories`) from **Strategy Context** (trade reasonings in `decisions`).*
*   **Scenario Awareness:** Memories now incorporate structured **Scenario Analysis**, requiring models to recall not just what happened, but different well-defined ways an event was expected to resolve and the associated **Trading Plans**.
*
*   **Retrieval:** *The engine performs a parallel search across both tables to provide the LLM with a unified view of the market environment and its own past logic.*
*   **Schema Robustness:** *Includes automated JSON string parsing, Pydantic field validation to convert `NaN` values to `None`, and expanded `catalyst_type` literals to handle model "Semantic Fragility" during high-volume tool loops.*
*   **Deduplication:** *Enforces a 24-hour lookback window to prevent semantic duplicates of the same event from being stored (Similarity > 0.90).*
*   documentation: [step-15-long-term-memory-embedding.md](./engine/step-15-long-term-memory-embedding.md)

### Phase 4: Frontend & Feedback

**18. Interactive Dashboard** ✅

*   **Tech:** **TanStack Start (Vite + React)**
*   *Server-side rendering for SEO, client-side hydration for interactivity.*
*   **State:** **TanStack Query** handles all data fetching with caching, deduplication, and background refetching.
*   **Architecture:** Hybrid pattern combining server loaders (fast initial load) with client-side `useQuery` (caching & real-time updates).
*   **Data Fetching Strategy:** All backend/database calls flow through TanStack Query for a single source of truth. See **[TanStack Best Practices Guide](./web/TANSTACK_BEST_PRACTICES.md)** for complete documentation.
*   **Key Features:**
    - **Query Options Factories:** Centralized, type-safe query & infinite query management via `src/lib/queries.ts`
    - **Cursor-Based Pagination:** Efficient pagination for large datasets (reasoning logs, memories)
    - **Infinite Queries:** "Load More" pattern with automatic caching
    - **Smart Caching:** Configurable stale times per route (2-10 minutes based on data volatility)
    - **Auto-Refresh:** Today page auto-refreshes every 5 minutes
    - **Zero Dependencies:** Custom error boundary using React's built-in APIs
*   **TODAY Dashboard**: The primary entry point (`/`) providing a comprehensive, real-time view of AI trading activity with a modern editorial design.
    *   **Market Status Hero**: Full-width gradient banner showing:
        - Live market status (Open/Closed with EST timezone awareness)
        - AI Sentiment Gauge (Bullish/Bearish/Neutral based on trade flow)
        - Quick stats: Newsletters, Trades, Active Memories
        - Animated gradient background with dot pattern
    *   **AI Cognitive Synthesis**: Consensus insights with enhanced visualization:
        - **Consensus Meter**: Progress bar showing agreement percentage
        - **Agent Avatars**: Color-coded participation (🟢 OpenAI, 🟠 Claude, 🔵 Gemini, 🟣 DeepSeek)
        - **Importance Scores**: Badge display for each insight
        - **Ticker Tags**: Related assets as clickable pills
    *   **Daily Intelligence Briefing**: Newsletter summaries in 2-column grid
    *   **Market Execution & Guardrails**: Interactive trade feed with:
        - Activity stats (Total, Buys, Sells, Rejected)
        - Agent attribution with confidence scores
        - Click-to-expand for full LLM reasoning
        - Detail cards showing quantity, price, total value
    *   **Horizon Watch**: Timeline of future catalysts with:
        - **Live Countdown**: Days/Hours/Minutes until each event
        - **Importance Coding**: Color-coded (Critical/High/Medium/Low)
        - **Scenario Analysis**: Expandable trading plans
        - **Smart Filtering**: Auto-hides past events
        - **Accurate Counter**: Shows only visible (non-passed) events
    *   **Horizon Watch** (Backend):
        - **Multi-Source Date Extraction**: The engine uses a multi-layered approach for date integrity. It first attempts to use LLM-extracted dates. If missing, the **`cleanup_catalysts.py`** script and the **frontend display layer** both use robust regex extraction to pull `YYYY-MM-DD` dates directly from the event title or content.
        - **ISO 8601 Standardization**: The engine enforces `YYYY-MM-DD` format for all future dates. Vague timeframes (e.g., "by next summer") are mapped to the end of that period. If ONLY a year is given, the date is set to `null` and the year is moved to the note.
        - **Tentative Notes & Time**: A `future_date_note` or `event_time` (e.g., "10:00 AM", "tentative") is extracted and stored, providing better context for Horizon Watch.
        - **Strict Separation & Calibration**: Horizon Watch strictly filters for events with `importance_score >= 8` AND `is_future_catalyst = true`. The cleanup script and ingestion pipeline automatically recalibrate these flags, ensuring that past events (Date < Today) or "Ongoing Trends" (e.g., Rotations, Investments) are moved to the general memory timeline and hidden from the future watcher. 
        - **Strict Catalyst Filter**: To qualify as a **Future Catalyst**, an event must be strictly PENDING and SCHEDULED. Vague timeframes like "later in 2026" or broad thematic shifts are excluded from this view.
        - **Multi-Outcome Scenarios**: Every Horizon Watch event is required to have a structured **Scenario Analysis** containing at least two possible outcomes and a dedicated **Trading Plan** for each.
*   **Audit Trail:** Users can explore the AI's logic on any execution or rejection directly from the **TODAY** dashboard. 
    - Click-to-expand cards reveal full LLM thought process and reasoning
    - Agent attribution with confidence scores displayed as badges
    - Detail cards show quantity, price, total value, and confidence
    - Color-coded: Green (BUY), Red (SELL), Amber (REJECTED)
    - For closed positions, the audit trail displays **Realized P&L** (USD and %) in the trades table
*   **Agent Portfolios:** Dedicated [Portfolios UI](./web/portfolios-ui.md) for tracking AI agent performance and holdings.
    *   **Active vs Retired Classification:** Portfolios are automatically classified based on their `owner_id` matching current models in `packages/config/models.json`.
    *   **Retired Portfolios:** Outdated model portfolios (e.g., `gemini-3-flash-preview`, `mimo-v2-pro`) are moved to a "Retired Agents" section with visual distinction (grayed styling, reduced opacity).
    *   **Owner ID Normalization:** Handles formatting variations (spaces, dashes, underscores, case) for robust matching across different model name formats.
    *   **Interactive Equity Curve**: Performance chart with hover tooltip overlay showing exact date and equity value, plus vertical crosshair for precise tracking.
    *   **Sortable Positions Table**: Click-to-sort columns for Invested, % of Portfolio, P/L (USD), and P/L (%) with visual direction indicators.
*   **Documentation:** [Web Application Architecture & Structure](./web/README.md)
*   **Hosting & Deployment:** [Netlify Deployment (benchify)](./web/tanstack-start-deploy-official.md)
*   **Live Dashboard:** [benchify.netlify.app](https://benchify.netlify.app)
*   **Public Insights:** A public [Memories Page](/memories) allows users to explore the AI's long-term market perspective.
    *   **How to Profit:** Each memory card features an interactive "How to Profit" section that displays actionable investment ideas and specific FMP-verified assets based on the AI's scenario analysis.
    *   **Event Linking:** Browse related "Update" events and trace their parent origins.
    *   **Flow View:** An interactive, infinite-canvas visualization of narrative threads and event chains.
*   **Reasoning**: A research-grade audit trail with a human-friendly tabbed UI, showing every LLM interaction, tool call, and internal "thought" trace categorized by task type.
*   **How it Works**: A detailed conceptual overview of the agentic pipeline with technical depth.
    *   **Phase Breakdown:** 
        - **Phase 1: Ingestion** (Tripled trigger: 09:30, 12:30, 15:30 ET via GitHub Actions, Holiday-Aware Market Hours Check via FMP with 5-min TTL caching, Gmail newsletter scraping, Economic Calendar from Trading Economics)
        - **Phase 2: Analysis** (Parallel LLM analysis via PromptFactory, Global Macro Tracker with 16 assets and regime detection at 2σ, Asynchronous Chunk Batching (20 chunks), Web Search with citations, Stock Screener tool, DiscoveryAgent for Alpha Discovery)
        - **Phase 3: Verification** (4-Layer Enforcement System, Hard Tool Enforcement requiring native function calls, Ownership Pre-Validation, 50% Confidence Penalty, Strategic Reasoning Audit)
        - **Phase 4: Execution** (FMP-Verified Market Hours, 5.0% Price Banding, Reg T Margin Validation with $1,000 minimum, Atomic Settlement "Commit at End" pattern, Two-Phase Attribution Locking)
        - **Phase 5: Feedback** (Manager Agent with 5/14/30-day post-analysis, Contrarian Agent, Government Tracking monthly audit, Cause & Effect bi-weekly with semantic deduplication, pgvector RAG with Scenario Analysis)
    *   **Models:** OpenAI (gpt-5.4-nano), Claude (claude-haiku-4-5), Gemini (gemini-3.1-flash-lite-preview), DeepSeek (deepseek-reasoner)

**18a. TanStack Query Architecture** ✅
*   **Tech:** **TanStack Query v5 + TanStack Start**
*   **Goal:** Single source of truth for all data fetching with automatic caching, deduplication, and background refetching.
*   **Implementation:** Hybrid pattern - server loaders for fast initial page load (SEO, FCP) + `useQuery` for client-side caching and real-time updates.
*   **Routes Using Hybrid Pattern:**
    - `/` (Today) - Auto-refresh every 5 minutes, stale time 2 minutes
    - `/memories` - Infinite scroll with cursor pagination, stale time 5 minutes
    - `/reasoning` - Infinite scroll with cursor pagination, stale time 5 minutes
    - `/concepts` - Static data, stale time 10 minutes
    - `/cause-and-effect` - Historical data, stale time 5 minutes
    - `/portfolios` - Performance data, stale time 5 minutes
    - `/portfolios/$id` - Detail view with positions, trades, history
*   **Query Key Structure:** Type-safe cache management using centralized `queryOptions` via the `queries` factory.
*   **Named Parameters Pattern:** All query methods use named parameters for explicit, type-safe API usage (e.g., `queries.reasoning.list({ cursor, fetchFn })`).

*   **Documentation:** [TanStack Best Practices Guide](./web/TANSTACK_BEST_PRACTICES.md), [Reasoning Page Optimization](./web/reasoning-page-optimization.md)

**18b. Testing Infrastructure** ✅
*   **Tech:** **Vitest + React Testing Library**
*   **Goal:** Ensure UI reliability and logic correctness for complex frontend components.
*   **Documentation:** [Frontend Testing](./web/testing.md)

**18c. Concept Cluster Map** ✅
*   **Tech:** **D3.js + React**
*   **Visualizing Trends:** A 2D scatter plot visualizing semantic relationships between market concepts.
*   **Coordinates:** Calculated via PCA (Principal Component Analysis) on the python backend to reduce 768-dim embeddings to 2D.
*   **Route:** `/concepts`
*   **Features:** 
    *   **Hybrid Visualization:** Nodes are colored by **Velocity** (Red=Trending, Blue=Stable) to show momentum at a glance.
    *   **Spatial Heatmap:** Background "islands" are colored by **Semantic Position** (Rainbow) to group related concepts.
    *   **Interactive Topography:** Hovering over a background region highlights the entire cluster and identifies the Region Name, creating an explorable "Terrain Map" of the market.
    *   **Temporal Tracking:** Tooltips display both **"First seen"** and **"Last seen"** dates for each concept, allowing users to track the lifespan of market narratives.

**19. Google Authentication** ✅
*   **Tech:** **Supabase Auth (OAuth 2.0)**
*   **Goal:** Enable secure, one-click login for users using their Google accounts, integrated with the project's RLS policies.
*   **Action:** Uses `signInWithOAuth` on the client side to handle the redirect flow and session management.
*   **Implementation Best Practice:** Uses a dual-client approach (Server Client for SSR/Server Functions and Browser Client for OAuth redirects) to maintain session consistency.
*   documentation: [auth-walkthrough.md](./engine/auth-walkthrough.md)

**20. Community Interaction**
*   **Tech:** **Supabase Auth**
*   *Users log in to comment on trades.*
*   **Security:** *Postgres Row Level Security (RLS) ensures only authenticated users can post, and only Admins can write to the Ledger.*

**21. Observability & Health**
* **Tech:** Sentry
* *Log parsing failures or API timeouts.*

**22. Analytics & Growth**

* **Tech:** PostHog
* *Track which AI's reasoning page is most read.*

**23. Regret-Driven Reinforcement (Post-Analysis & Manager Agent)** ✅

* **Tech:** Python / Gemini Flash 3 / pgvector
* **Logic:** *At multiple intervals (5, 14, 30 days) after a trade, the **Manager Agent** performs a "Post-Analysis." It compares the AI's reasoning to the actual price performance.*
* **Outcome:** *Generates "Lessons Learned" (stored as `LESSON_LEARNED` memories) and injects them back into the Long-term Memory (pgvector). This allows the AI to recognize its own past hallucinations or **strategic planning errors** in future RAG retrievals.*
* File: `apps/engine/analysis/post_analysis.py`

**24. Contrarian Agent Execution** ✅

* **Tech:** Python / Gemini Flash 3
* **Logic:** *Runs after the primary agents, analyzing their consensus to identify crowded trades or missed risks.*
* **Multi-Block Robustness:** *Uses a `ContrarianAgentResponse` wrapper model (`responses: List[DecisionsResponse]`) to safely aggregate responses from multiple Gemini tool-call blocks, avoiding `Instructor does not support multiple function calls` errors.*
* **Dependency Injection:** *Supports DI via optional parameters (`portfolio`, `market_data`, `llm_client`, `retrieve_context_fn`) for testability. See [Testing](./engine/testing.md#dependency-injection-for-analysis-functions).*
* **Outcome:** *Executes contrarian trades in a dedicated portfolio.*
* File: `apps/engine/analysis/contrarian.py`

**25. Government Budget & Policy Tracking** ✅

* **Tech:** Python / Gemini Flash 3
* **Logic:** *Monthly pipeline that identifies government incentives, budgets, and objectives. The engine enforces strict compliance in the analysis loop, triggering warnings if models fail to flag clear government policy content.*
* **Outcome:** *Stores findings as `GOVERNMENT_INCENTIVE` memories with expiry dates to inform future analysis. Prompt instructions are explicitly strengthened to ensure models link policy keywords to the `is_government_incentive` flag.*
* File: `apps/engine/ingest/government.py`

**26. Uncrowded Trades Identification** ✅

* **Tech:** Python / Multi-LLM
* **Logic:** *Agents are instructed to actively look for secondary / derivative effects of news (e.g., fertilizer supply shocks from an oil conflict) that the broader market hasn't priced in. These opportunities are flagged as `UNCROWDED_TRADE`.*
* **Outcome:** *The Verification step uses a specialized rule set for `UNCROWDED_TRADE`s, bypassing strict volatility/momentum guardrails to prioritize the fundamental entry thesis.*
* File: `apps/engine/core/models.py`, `apps/engine/core/llm/prompts.py`, `apps/engine/core/llm/verification.py`

**27. System Audits** ✅

* **Tech:** Python / DeepSeek / GitHub Actions / Supabase
* **Logic:** *Weekly audit system that checks for database anomalies and analyzes system logs.*
* **Components:**
  - **SQL Anomaly Checks:** 10 checks for orphaned references, invalid status values, stale data, and data quality issues.
  - **Log Analysis:** DeepSeek-powered analysis of ingestion logs to identify errors and failures.
  - **Public Dashboard:** `/audits` page displays all findings for transparency.
* **Schedule:** Weekly on Fridays at 16:00 EST via GitHub Actions.
* **Retention:** `system_audits` resolved/ignored entries deleted after 30 days; `ingestion_logs` deleted after 48 hours.
* **Files:**
  - Engine: `apps/engine/core/audit/`
  - Workflow: `.github/workflows/audit.yml`
  - Frontend: `apps/web/src/routes/audits/`

**28. Market Feeling (LLM-Driven Sentiment)** ✅

* **Tech:** Python / MiniMax MiniMax-M2.7 / Supabase
* **Logic:** *After the main pipeline execution (09:30, 12:30, 15:30 ET), the system calls MiniMax MiniMax-M2.7 with today's trading data (trades, LESSON_LEARNED memories, MARKET_EVENT memories, and decision reasoning) to generate a nuanced "How I'm feeling and why" market sentiment.*
* **Output Fields:**
  - `sentiment_label`: LLM-generated label (e.g., "Cautiously Optimistic", "Risk-Off", "Wait-and-See")
  - `sentiment_emoji`: Single emoji
  - `confidence_score`: 0-100 based on data availability
  - `why_explanation`: 2-3 sentence reasoning
  - `market_direction`: BULLISH / BEARISH / NEUTRAL
  - `primary_concern`: Main risk or opportunity
  - `secondary_concern`: Secondary consideration
* **Display:** Shown prominently on the Today page ("How I'm Feeling" card) with confidence bar, direction badge, and "last analyzed" timestamp.
* **Fallback:** If no fresh analysis exists (stale >4 hours), shows warning indicator and last update time.
* **Retention:** 30-day history stored in `market_feeling` table.
* **Files:**
  - Engine: `apps/engine/analysis/market_feeling.py`
  - MiniMax Client: `apps/engine/core/llm/minimax.py`
  - Migration: `supabase/migrations/20260416000001_create_market_feeling.sql`
  - Frontend: `apps/web/src/components/today/MarketStatusHero.tsx`
  - Database Schema: [database-schema.md](./database-schema.md#8-market-feeling-llm-driven-sentiment)


## 9. Reasoning Rigor & Validation

To ensure high-fidelity decision-making and prevent "shallow" market analysis, the system enforces a strict reasoning framework across all agents.

### The "5 Whys" Technique
All reasoning agents (Analysis, Manager, Cause & Effect) are required to apply recursive causal analysis:
1. **Why** is this news market-moving?
2. **Why** will this specific asset benefit?
3. **Why** is this not already priced in?
4. **Why** is the proposed action the most efficient way to profit?
5. **Why** could this trade fail (Root Cause of Risk)?

This prevents agents from simply repeating news headlines and forces them to identify the actual "Profit Mechanism" and "Supply Chain Bottlenecks."

### Catalyst Logic Synchronization
The system synchronizes strict filtering logic between the **Analysis** and **Synthesis** layers to prevent "Horizon Watch" dashboard pollution:
- **Negative Constraints:** Vague themes (e.g., "AI growth"), broad years (e.g., "in 2026"), or non-specific timeframes (e.g., "later this year") are explicitly rejected as future catalysts.
- **Actionable Events:** Only events with a specific expected date or a very tight window (e.g., "this week") are promoted to the Horizon Watch dashboard.

### Hard Tool Enforcement
The **Execution Engine** performs server-side verification of the `tool_use` blocks in the LLM response history. 
- **Requirement:** `get_stock_quote`, `calculate_buy_quantity`, and `calculate_sell_quantity` must be physically executed.
- **Hallucination Guard:** If an LLM claims in text to have called a tool but the actual functional block is missing, the trade is automatically rejected as a hallucination.

---

## 4. Maintenance & Utilities

The engine provides several utility scripts for managing the system state and performing maintenance tasks without re-running the entire pipeline.

### Resetting State

If you need to reset the portfolios to their default state (e.g., $10,000 cash) and clear all active trades/positions while keeping the history:

*   **Script:** `apps/engine/reset_state.py`
*   **Usage:** `python reset_state.py`

### Clearing the Database (Start from Scratch)

To completely wipe the experimental data while preserving market price history and cache:

*   **Script:** `apps/engine/clear_db.py`
*   **Usage:** `python clear_db.py`
*   **Preserved Tables:** `price_history`, `market_data_cache`.

> The `clear_db.py` script is destructive and cannot be undone. Use it only when you want to restart all LLM experiments from zero.

### Economic Calendar Ingestion

To manually trigger the fetching and analysis of global macro events:
*   **Command:** `python main.py calendar`
*   **Pipeline:** Fetches HTML -> BeautifulSoup Parsing -> DeepSeek Relevance Filtering -> Memory Insertion.

### Database Schema & Cleanup Utilities

To ensure the `docs/database-schema.md` is always up to date with the actual Postgres schema:
*   **Script:** `apps/engine/generate_schema_docs.py`
*   **Usage:** `python generate_schema_docs.py`

To normalize Horizon Watch catalysts (ISO dates, notes, and importance) and ensure strict separation from ongoing memories:
*   **Script:** `apps/engine/cleanup_catalysts.py`
*   **Usage:** `python cleanup_catalysts.py`
*   **Goal:** Enforces data integrity for "Horizon Watch" entries by standardizing non-ISO dates and ensuring materiality. It uses **Regex-based Date Extraction** to recover missing dates from event text and recalibrates the `is_future_catalyst` flag to strictly filter for upcoming events (Date >= Today), moving past events and ongoing thematic rotations to general memory.

## 5. Environment & Security
### Key Management Strategy

We use a **Scoped `.env**` approach. Each service only has access to the variables it needs. For local development, use a `.env.example` as a template.

**Critical Rule:** Never commit `.env` files. Add them to the root `.gitignore`.

### Required Variables

| Service | Variable Name | Description | Required For |
| --- | --- | --- | --- |
| **Global** | `DATABASE_URL` | Supabase Postgres Connection String | Engine, Database Migrations |
|  | `SUPABASE_URL` | Supabase API URL | Web (Frontend), Engine |
| **Engine** | `OPENAI_API_KEY` | OpenAI API Key (Model: `gpt-5.4-nano`) | Trading Analysis, Embeddings |
|  | `ANTHROPIC_API_KEY` | Claude API Key (Model: `claude-haiku-4-5`) | Trading Analysis |
|  | `GEMINI_API_KEY` | Google Gemini API Key | Trading Analysis, Embeddings |
|  | `DEEPSEEK_API_KEY` | DeepSeek API Key | Trading Analysis |
|  | `FMP_API_KEY` | Financial Modeling Prep API Key (Required) | Price Data & Validation |
|  | `FINANCIAL_PROVIDER` | Primary market data provider (Default: `fmp`) | Selection of the single market data source |
|  | `MARKET_DATA_CACHE_TTL_SECONDS` | Cache duration in seconds (Default: 2) | Price Fetching Optimization |
|  | `MARKET_DATA_RETRIES` | Number of attempts per provider (Default: 2) | Configurable retry logic |
|  | `IBKR_HOST` | Host for IBKR Gateway/TWS (Default: `127.0.0.1`) | [LEGACY — not in active use] |
|  | `IBKR_PORT` | Port for IBKR Gateway/TWS (Default: `7496`) | [LEGACY — not in active use] |
|  | `IBKR_CLIENT_ID` | Client ID for IBKR connection (Default: `1`) | [LEGACY — not in active use] |
|  | `IBKR_PROXY_URL` | URL of the IBKR Proxy server | [LEGACY — not in active use] |
|  | `IBKR_PROXY_TOKEN` | Auth token for the IBKR Proxy | [LEGACY — not in active use] |

For detailed setup instructions, see [IBKR Integration Guide](IBKR-Integration.md).
|  | `FINANCIAL_API_THROTTLE_SECONDS` | **INTERNAL CONSTANT** (0.2s). Formerly an environment variable, now hardcoded for high-performance parallel fetching. | Rate Limit Prevention |
|  | `MIN_TRADE_VALUE` | Minimum purchase/sell value for LLM-driven trades (Default: 1000.0) | Trade Validation |
|  | `MAX_PRICE_DEVIATION_PCT` | Maximum % difference between AI and market price (Default: 5.0) | Trade Validation |
|  | `ENABLE_ANTHROPIC_WEB_SEARCH` | Enable Anthropic web search (Default: true) | Real-time news verification |
|  | `ENABLE_GEMINI_WEB_SEARCH` | Enable Gemini Google Search (Default: true) | Real-time news verification |
|  | `ANTHROPIC_WEB_SEARCH_VERSION` | Tool version: `web_search_20250305` or `web_search_20260209` | ZDR compliance vs dynamic filtering |
|  | `ANTHROPIC_MAX_WEB_SEARCHES` | Max searches per request (Default: 3) | Cost control |
| **Agents** | (Automatic) | The system automatically processes post-mortems and contrarian signals. | Feedback Loop |
| **Web** | `VITE_SUPABASE_URL` | Supabase API URL (Exposed to Browser) | Frontend Auth & Data Fetching |
|  | `VITE_SUPABASE_ANON_KEY` | Supabase Anon Key (Exposed to Browser) | Frontend Auth & Data Fetching |

> [!TIP]
> **Vite Prefixing:** Any environment variable used in the browser (client-side code) MUST be prefixed with `VITE_`. Vite automatically strips non-prefixed variables from the client bundle for security.

> [!NOTE]
> **Security of Anon Key:** It is standard practice and safe to expose the `Supabase URL` and `Anon Key` to the frontend. Security in Supabase is enforced via **Row Level Security (RLS)** at the database layer. NEVER expose the `SERVICE_ROLE_KEY` to the client.

> [!CAUTION]
> **Vite Prefixing:** Only variables prefixed with `VITE_` are exposed to the frontend. All Python/Engine keys **must not** have this prefix to prevent accidental exposure via client-side bundles.

### Latest Model Configuration

Model names are defined in the shared JSON configuration file at [`packages/config/models.json`](../packages/config/models.json) — **not** set via environment variables. To change a model, edit this JSON file directly. Both the Python engine and the TypeScript frontend read from it, ensuring a single source of truth.

> [!TIP]
> **Monorepo Workspace Integration:** The `packages/config` directory is officially configured as a `pnpm` workspace package named `@repo/config`. This allows the Web Frontend to seamlessly import the shared JSON structure during the Vite build process (`import modelsConfig from '@repo/config/models.json'`) without causing bundler resolution errors or relying on brittle relative paths.

```json
{
  "OPENAI_MODEL": "gpt-5.4-nano",
  "ANTHROPIC_MODEL": "claude-haiku-4-5",
  "GEMINI_MODEL": "gemini-3.1-flash-lite-preview",
  "DEEPSEEK_MODEL": "deepseek-reasoner",
  "CONTRARIAN_AGENT_ID": "contrarian_agent"
}
```

### Deprecated Portfolios

When a provider's model is upgraded (e.g., `gpt-4o-mini` → `gpt-5.4-nano`), the old portfolio row in the `portfolios` table is **not automatically removed**. It becomes an inactive historical record. The portfolios below are **no longer traded** and will not receive new decisions, but their historical performance data (trades, ledger snapshots) is preserved for auditability.

| `owner_id` (DB key) | Provider | Replaced By | Reason Deprecated |
|---|---|---|---|
| `gpt-4o-mini` | OpenAI | `gpt-5.4-nano` | Upgraded to GPT-5 generation model |
| `gpt-4o` | OpenAI | `gpt-5.4-nano` | Upgraded to GPT-5 generation model |
| `gpt-5-mini` | OpenAI | `gpt-5.4-nano` | Model renamed/versioned to `gpt-5.4-nano` |
| `claude-3-5-haiku-20241022` | Anthropic | `claude-haiku-4-5` | Upgraded to Claude 4 generation |
| `gemini-2.0-flash` | Google | `gemini-3.1-flash-lite-preview` | Upgraded to Gemini 3 generation |
| `gemini-2.5-flash-preview-04-17` | Google | `gemini-3.1-flash-lite-preview` | Upgraded to Gemini 3 generation |

> [!NOTE]
> To hide deprecated portfolios from the dashboard, you can soft-delete them by adding an `is_active = false` flag to the `portfolios` table via a Supabase migration, or simply filter them out in the frontend query by checking if the `owner_id` matches one of the current active models in `packages/config/models.json`.

### Local Setup Flow

1. **Root Directory:** No `.env` file (avoids confusion).
2. **`apps/engine/.env`**: Contains all LLM and Broker keys.
3. **`apps/web/.env`**: Contains only Supabase connection keys.
4. **GitHub Secrets**: Add all the above to **Settings > Secrets and Variables > Actions**.
   - **Secrets**: Use for sensitive keys (API Keys, Tokens, URLs).
   - **Variables**: Use for optional configuration overrides (e.g., `FINANCIAL_PROVIDER`).
   - **Note**: Model names are **not** GitHub Variables — they're defined in `packages/config/models.json`.

### GitHub Actions Configuration

The daily pipeline in `.github/workflows/ingest.yml` explicitly maps Secrets and Variables to the engine. Ensure the following are set in GitHub to avoid failures:

#### Required Secrets
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`
- `FMP_API_KEY`: Financial Modeling Prep API key.
- `SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY`.
- `DEEPSEEK_API_KEY`: Used for both trading analysis and audit log analysis.

#### Optional Variables
You can override default providers without code changes by adding these as **Repository Variables**:
- `FINANCIAL_PROVIDER`: Defaults to `fmp`.

> [!NOTE]
> Model names (`OPENAI_MODEL`, `GEMINI_MODEL`, etc.) are **no longer environment variables**. They are defined in the shared JSON file at `packages/config/models.json`. Update that file directly when switching models.


## Information Flow

```mermaid
graph TD
    subgraph "Development & CI/CD"
        DEV[Developer Code Change] --> CI[GitHub Actions: ci.yml]
        CI -->|Pass| MAIN[Merge to main]
    end

    subgraph "Daily Pipeline (Phase 1)"
        CRON[Cron Schedule 09:30, 12:30, 15:30 ET] --> INGEST[ingest.yml]
        INGEST --> A[Gmail Newsletters]
        INGEST --> GOV_INGEST[Government Tracking]
        INGEST --> CAL_INGEST[Economic Calendar]
        A & GOV_INGEST & CAL_INGEST --> B[Data Snapshot + Chunk IDs]
    end

    subgraph "Reasoning & Consensus (Phase 2)"
        B --> GMT[Global Macro Tracker]
        GMT --> C{Context Retrieval}
        C <-->|Query History| V[Supabase pgvector]
        
        GMT --> D1[OpenAI Batch Analysis]
        GMT --> D2[Claude Batch Analysis]
        GMT --> D3[Gemini Batch Analysis]
        GMT --> D4[DeepSeek Batch Analysis]
        
        D1 & D2 & D3 & D4 --> AT[Decision Attribution Layer]
        AT -->|Map Reasoning to ChunkID| DB[(Decisions Table)]
        
        AT --> CP{Event Consensus Protocol}
        
        CP --> VER[Skeptical Verifier Agent]
          MDM[MarketDataManager]
        MDM -->|Primary| FMP[Financial Modeling Prep]
        MDM -->|Fallback| YF[YFinance]
        VER -->|Abort/Adjust| EG{Execution Guardrails}
        
        EG -->|Cleanup| CL[Provider disconnect_all]
        
        CP -->|Semantic Grouping + Dedupe| SYN[LLM Synthesis]
        
        SYN --> TM[Trend & Momentum Analysis]
        TM -->|Update Velocity| CM[(Concept Metrics)]
        TM -->|Promote 2+ Agreement| GT[Global Timeline]
        
        SYN --> FW[5 Whys Reasoning Check]
        FW --> HG{Hallucination Guardrails}
    end

    subgraph "Execution & Memory (Phase 3 & 4)"
        HG -->|Fail| F[Reject]
        EG -->|Pass| GT
        EG -->|Pass| H[Execution Engine]
        
        H --> I[Supabase Ledger]
        I -->|Link TradeID| DB
        
        I --> LS[Performance Snapshot]
        LS --> J[TanStack Start Dashboard]
        
        I --> ME[Memory Embedding]
        ME -->|Vectorize reasoning| V
        
        GT --> J
        K[User Comments] -->|Supabase Auth| J
    end

    subgraph "Analysis & Feedback (Phase 5)"
        I --> PM[Manager Agent: Post-Analysis]
        PM -->|Lessons Learned| V
        
        CP --> CA[Contrarian Agent]
        CA -->|Counter-Signals| H
        
        GOV[Gov Tracking] -->|Incentives| V

        V --> CE[Cause & Effect Analysis]
        CE -->|Historical Impact| V
    end
```

## 6. Cause & Effect Analysis (Historical Audit)

The system performs a bi-weekly retrospective audit of market events to track predicted vs actual impact. This is the "Institutional Memory" loop that turns news into a searchable playbook.

### Key Logic:
- **Dynamic Ticker Discovery:** Instead of just checking broad indices, the engine uses Gemini to identify the specific 3-5 companies, suppliers, or competitors most affected by a theme (e.g., "Private Credit" -> JPM, OWL).
- **Semantic Deduplication:** Enforces a 7-day lookback window with a ~0.85 similarity threshold to ensure identical narratives aren't analyzed twice.
- **Causal Attribution:** The LLM compares the original "Scenario Analysis" against actual historical price data (fetched via `MarketDataManager`) to quantify the outcome.

### Example Entry:
| Event | Tickers Checked | Actual Market Outcome | Causal Analysis |
|-------|-----------------|-----------------------|-----------------|
| **Fed Rate Hike Pause** | SPY, QQQ, JPM, GS | Financials outpaced tech as yield uncertainty stabilized. | The pause provided relief to regional banks, while mega-cap tech remained flat due to high valuations. |
| **Iran-Israel Tension** | USO, XOM, LMT, RTX | Energy and Defense sectors spiked 3-5% intraday. | Geopolitical risk premium was immediately priced into Brent crude futures and defense contractors. |

## 7. FMP API Documentation

For detailed Financial Modeling Prep (FMP) API reference, see:

*   **Documentation:** [docs/library-docs/FMP/FMP-API-Documentation.md](./library-docs/FMP/FMP-API-Documentation.md)
*   **Coverage:** Complete reference for all 28 API categories including:
    *   Stock Prices & Market Data
    *   Financial Statements (Income, Balance, Cash Flow)
    *   Company Profiles & Insider Trading
    *   Economic Data & Calendars
    *   Technical Indicators & Screener
    *   ETFs, Mutual Funds, and Crypto APIs
*   **Usage:** All endpoints use base URL `https://financialmodelingprep.com/stable/` with API key authentication via header or query parameter.

## 8. Deployment & Hosting

The application is deployed as a Serverless TanStack Start app on Netlify.

*   **Project Name:** `benchify`
*   **Live URL:** [https://benchify.netlify.app](https://benchify.netlify.app)
*   **Site ID:** `5d3df086-5934-4ea4-9758-36fe189e9af3`
*   **Deployment Docs:** [docs/web/tanstack-start-deploy-official.md](./web/tanstack-start-deploy-official.md)

### Deployment Flow
```bash
cd apps/web
pnpm run build
npx netlify deploy --prod --site 5d3df086-5934-4ea4-9758-36fe189e9af3
```
