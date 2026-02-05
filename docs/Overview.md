# Project Overview: AI Wall Street

## 1. Project Summary

### What It Does

An automated platform where six LLMs (**OpenAI, Claude, Gemini, DeepSeek, Contrarian Agent, Manager Agent**) compete in a virtual stock market. Every morning, they parse financial newsletters, debate major global events, analyze government incentives, and rebalance their portfolios.

### Why It Matters

* **Performance Benchmarking:** Real-world test of LLM reasoning vs. S&P 500.
* **The "Consensus" Effect:** Identifies where AI models agree or diverge on global risks.
* **Decision Attribution:** Provides a machine-auditable trail from raw news chunk to final trade execution.
* **Memory Integrity:** Tests if LLMs can maintain a consistent world view using Vector RAG (Retrieval-Augmented Generation).

## 2. Technical Architecture & Repo Structure

The project follows a **Monorepo** structure to keep the Python Data Engine and the TypeScript Frontend synchronized while separating concerns.

**Repository Organization:**

```text
llm-market-bench/
├── apps/
│   ├── web/                 # TanStack Start (Frontend - React + TS)
│   │   ├── src/             # Application source
│   │   │   ├── routes/      # Route Ownership: Colocated UI & Logic
│   │   │   ├── shared/      # Shared Domain: Auth, Portfolios (cross-route business logic)
│   │   │   ├── components/  # Design System: Pure UI primitives (ui/, layout/)
│   │   │   ├── lib/         # Infrastructure: Supabase, SEO, Query Client
│   │   │   └── hooks/       # Generic hooks
│   │   └── package.json     # Web dependencies
│   └── engine/              # Python (The Backend Pipeline)
│       ├── core/
│       │   └── llm/         # LLM clients and handlers
│       │       ├── handlers/  # Provider-specific tool execution (openai, anthropic, gemini)
│       │       ├── analysis.py
│       │       ├── clients.py
│       │       ├── prompts.py
│       │       └── tools.py
│       ├── ingest/          # Newsletters & De-advertisement
│       │   ├── newsletter.py
│       │   └── cleaner.py
│       ├── attribution/     # Decision mapping
│       ├── analysis/        # Trend & momentum
│       ├── execution/       # Trade Settlement
│       ├── main.py          # Entry point
│       └── update_prices.py # Utility

├── packages/
│   └── database/            # Shared Supabase types/schemas (PENDING)
├── supabase/                # SQL Migrations, RLS policies
├── package.json             # Root monorepo config
├── pnpm-workspace.yaml      # PNPM Workspaces config
└── README.md                # Project entry point
```

## 3. The 20-Step Daily Pipeline

For a detailed step-by-step walkthrough with a concrete example of how data flows through the entire pipeline (from Gmail newsletters to trading decisions), see **[data-flow.md](./data-flow.md)**. This document traces 4 sample newsletters through each phase with actual API calls and database operations documented.

### Phase 1: Ingestion & Normalization

**1. Daily Trigger (09:35 ET)** ✅

*   **Tech:** GitHub Actions (Cron)
*   **Goal:** Fire the pipeline 5 minutes after market open to capture live prices.
*   File: .github/workflows/ingest.yml

**1a. Quality Assurance (CI/CD)** ✅

*   **Tech:** GitHub Actions / Pytest
*   **Logic:** *Automatically runs unit tests for core configuration and ingestion utilities on every pull request and push to the `main` branch. This serves as a security/stability gate for the engine.*
*   File: .github/workflows/ci.yml
*   documentation: ./engine/testing.md

**2. Newsletter Ingestion** ✅

*   **Tech:** Python / Gmail API / Gemini API
*   *Scrape unread newsletters into raw text chunks. Each chunk is assigned a unique `SourceID` and `ChunkHash` for attribution.*
*   **LLM De-advertisement:** *Uses Gemini Flash to identify and remove advertisements, referral links, and promotional fluff from newsletter subsections before analysis.*
*   File: apps/engine/ingest/newsletter.py, apps/engine/ingest/cleaner.py
*   **Semantic Monitoring:** *Structured logging alerts (Semantic Fragility Alert) if a previously active sender yields 0 valid content chunks, detecting parsing template changes.*
*   documentation: ./engine/newsletter-ingestion-walkthrough.md

**3. Corporate Action Check** - PENDING - ⏳

*   **Tech:** Python / Market API
*   *Check for stock splits/dividends. Adjust the "Virtual Portfolio" holdings before the LLM sees them to prevent fake price-drop panics.*

**4. Data Snapshotting (Idempotency Layer)** ✅

*   **Tech:** Supabase Postgres
*   *Save the raw newsletter text and current prices.*
*   **Constraint:** *Use a composite unique key (Date + SourceID) to prevent duplicate processing if the job restarts.*
*   documentation: ./engine/data-snapshotting-walkthrough.md

### Phase 2: The Consensus & Attribution Engine

**5. Parallel LLM Analysis (Structured Output)** ✅

*   **Tech:** OpenAI, Claude, Gemini, DeepSeek APIs
*   **Validation:** **Python Pydantic + Instructor**
*   **Active Tool Calling:** LLMs (**OpenAI, Anthropic, Gemini**) utilize multiple tools *during* analysis:
    *   `get_stock_quote`: Verifies ticker existence, real-time pricing, and liquidity.
    *   `get_price_history`: Fetches recent price history to determine if news is "priced in".
    *   `get_position_pnl`: Fetches current unrealized P&L and cost basis for existing positions.
*   **Sophisticated Trading Logic Injection:** *LLMs are instructed to answer critical questions before trading:*
    *   **Is it possible to make a profitable trade based on this?** (Profit potential justification).
    *   **Is this news already priced in?** (Predicting next move, not chasing).
    *   **What is being incentivized right now?** (Awareness of government budgets and objectives).
    *   If I already own this stock, has this trade been profitable?
    *   What is the expected timeline for this catalyst to materialize?
    *   What are the primary risks or counter-arguments to this trade?
    *   How does this stock correlate with my existing portfolio?
*   **Portfolio Context Injection:** *LLMs receive their current Cash, Equity, and Buying Power in the prompt, allowing them to make "Allocation %" decisions rather than just static share counts.*
*   **Catalyst Scoring:** *LLMs categorize trades into types (**MACRO, EARNINGS, M&A, PRODUCT, REGULATORY**) and estimate target **Duration** (INTRADAY, SHORT_TERM, LONG_TERM) for enhanced strategy filtering.*
*   **Efficiency:** **Batch Processing** (Each LLM is called in a tool-calling loop with all daily news chunks to minimize latency and costs).
*   *Force LLMs to adhere to a strict JSON schema for trade signals. If an LLM outputs malformed JSON, `Instructor` automatically loops back the error to the LLM for correction.*
*   *LLMs must return a `DecisionObject` containing the signal (Buy/Sell/Hold) AND the `SourceID` of the news chunk that triggered it.*
*   **Fault Tolerance:** If individual LLM providers fail, the pipeline continues with successful results. CRITICAL alerts are logged if all 4 providers fail.
*   documentation: ./engine/llm-analysis-walkthrough.md

**6. RAG Context Retrieval** ✅

*   **Tech:** **Supabase pgvector**
*   *Before analyzing today's news, the engine queries the vector store for relevant PAST events/trades to ensure the AI's reasoning is consistent with its history.*
*   documentation: ./engine/rag-context-retrieval.md

**7. Decision Attribution Layer** ✅

*   **Tech:** Python Logic / Supabase
*   **Audit Trail:** *Map the `ModelID` + `NewsChunkID` + `LLMReasoningString` into a `decisions` table. This creates a foreign key link between a Trade and the specific sentence in a newsletter that caused it. This table preserves the **individual perspective** of each LLM.*
*   **Vector Attribution:** Store a **Vector Embedding** of the reasoning directly in the `decisions` table. This allows the AI to retrieve its specific trade justifications during future RAG retrieval without cluttering the global macro timeline.
*   **Idempotency:** *Uses UPSERT with unique constraint on `(source_id, ticker, signal, model_provider, model_name)` to prevent duplicate decisions if the pipeline reruns.*
*   documentation: ./engine/decision-attribution-walkthrough.md

**8. Event Consensus Protocol & Memory Chains** ✅
*   **Tech:** Python / Gemini Embeddings / OpenAI Synthesis
*   **Global Timeline:** Promotes synthesized, professional macro events to the `memories` table. These focus strictly on events (e.g., "Fed Rate Cut", "Geopolitical Tension") that affect the broader market.
*   **Semantic Grouping:** Uses **Vector Embeddings** and **Cosine Similarity** to group events with different names but similar meanings (e.g., "Fed Hike" vs "Interest Rate Hike").
*   **Temporal Deduplication:** Checks the `memories` table to skip events promoted in the last 48 hours, keeping the timeline clean.
*   **Memory Chains:** For each new event, the engine performs a "Relationship Analysis" against recent memories.
    *   **Linking:** Links new events to ancestors via `parent_id` (e.g., a "Retraction" linked to a "Threat").
    *   **Auto-Resolution:** Automatically marks ancestors as `RESOLVED` if the new event reverses or completes them.
*   **Memory Optimization:** Memories marked as `RESOLVED` are excluded from LLM context retrieval, keeping analysis focused on active events.
*   **Relevance Decay:** Memories have a `relevance_score` that decays by 50% every 30 days, reducing the impact of old information over time.
*   **Proactive Projections:** During synthesis, the LLM extracts explicitly mentioned future dates and catalysts. These are tracked in a dedicated `future_events` table for proactive positioning.
*   **Contextual Focus:** The engine specifically prioritizes **Ongoing Unresolved Events** (e.g., "Armada is on the way") and **Historical Parallels** to provide agents with a deeper understanding of market regimes.
*   **LLM Synthesis:** For each consensus cluster, a fast LLM pass synthesizes a professional, unified event name and a 1-sentence summary.
*   **Consensus Rule:** An event group is promoted to the **Global Timeline** (memories) if its **Cumulative Model Weight** exceeds the threshold (Default: 2.0).
*   **Weighted Tie-Breaker:** When models are split between BULLISH and BEARISH, the system uses model weights (configured in `config.py`) to determine the majority impact rather than a simple head-count.
*   documentation: ./engine/event-consensus-walkthrough.md

**9. Trend & Concept Momentum Analysis** ✅
*   **Tech:** Supabase pgvector / Python
*   **Vectorized Frequency:** Instead of just counting keywords, the engine embeds the "Concept" (e.g., "NVIDIA Blackwell Delay") and performs a similarity search against the memories table to find semantically related mentions over a rolling 90-day window.
*   **Semantic Merging:** Prevents data fragmentation by automatically merging concepts with $> 0.75$ similarity into a single "Master Concept" record.
*   **Trend Archeology:** Each mention is stored with a first_seen_at timestamp and a cumulative 90-day frequency count.
*   **Momentum Scoring:** The engine calculates a "Momentum Score" based on a hybrid formula: `Intensity * Growth`. 
    *   **Intensity:** Rewards sheer relevance/volume using a log scale: `log(recent_mentions + 1) + 1`.
    *   **Growth:** Rewards acceleration by comparing the 7-day daily average against a 30-day daily average.
*   **Decay:** Stale concepts have their momentum scores reduced by 50% after 28 days of inactivity (half-life decay model), preventing outdated trends from persisting.
*   **Data Structure:** Updates a `concept_metrics` table tracking concept_vector, mention_count, first_mention_date, and velocity_score (used to store Momentum Score). This acts as an **Analytical Aggregation Layer** separate from the raw `memories`.
*   **Visualization:** The daily pipeline automatically calculates 2D PCA coordinates (`pca_x`, `pca_y`) for all concepts, enabling real-time visualization on the [Concept Cluster Map](../../apps/web/src/routes/concepts/index.tsx).
*   documentation: ./engine/trend-momentum-analysis.md

**9.a. General Review**
*   documentation: ./engine/claude-step-9-and-before-review.md

**10. Pre-Market Validation (Hallucination Guardrails)** ✅

*   **Tech:** Python / `MarketDataManager` / yfinance or FMP
*   **Cache-First Architecture:** Uses a `market_data_cache` table in Supabase (4-hour TTL) to minimize external API dependencies and prevent rate limits. A permanent record of all fetched prices is stored in the `price_history` table for long-term analysis.
*   **Guardrail A (Existence):** *Verify ticker exists and is not delisted.*
*   **Guardrail B (Price Banding):** *If AI wants to "Buy AAPL at $50" but market price is $150, reject trade (Price Hallucination).*
*   **Guardrail C (Liquidity):** *Reject tickers with Market Cap < $2B (Penny Stock protection).*
*   **Guardrail D (SMA Floor):** *Reject trades that would push the projected SMA below 10% of total equity to ensure Reg T compliance.*
*   **Guardrail E (Robust Price Fallback):** *In `calculate_reg_t_metrics`, if market data fails (price = 0), positions are valued at their `average_cost_basis`. This prevents "Negative Total Equity" hallucinations for margin accounts.*
*   **Double-Layer Security:** These guardrails run both as an LLM Tool (Phase 2, Step 5) and as a final validation gauntlet before execution. **Ticker Casing** is normalized to uppercase across all layers for consistency.
*   documentation: ./engine/pre-market-validation.md
*   File: `apps/engine/execution/market_data.py`, `apps/engine/execution/validation.py`

### Phase 3: Market Execution (Sequential)

**11. Pre-Execution Margin Validation** ✅

*   **Tech:** Python / Supabase / Reg T Logic
*   **Logic:** *Before moving a decision to "Trade Settlement", the engine validates that the agent has sufficient Buying Power.*
*   **Rule:** *Check `portfolio.buying_power` against the estimated cost of the trade. If `Cost > Buying Power`, reject the trade to prevent negative balances. Allows valid leveraged trades.*
*   **Persistence:** *Portfolios are stored in `portfolios` and `portfolio_positions` tables to maintain state across daily runs.*
*   **Portfolio Context Injection:** *LLMs receive their current Cash, Equity, and Buying Power in the prompt, allowing them to make **"Allocation %"** decisions (e.g., "Use 10% of BP for this trade") rather than just static share counts.*
*   documentation: ./engine/portfolio-management-walkthrough.md

**12. Trade Settlement & Ledgering** ✅

*   **Tech:** Python / Portfolio Class
*   **Logic:** *Execute `portfolio.execute_trade()` for valid decisions.*
*   **Guardrail:** *Enforces **Portfolio Ownership** for SELL signals; if an LLM tries to sell a ticker it doesn't own, the trade is rejected.*
*   **Action:** *Updates `cash_balance`, `sma`, and `portfolio_positions`. **Crucially, inserts a record into the `trades` table to generate a unique `TradeID` for the execution.***
*   **Atomic Settlement Pattern:** *Follows a **"Commit at the End"** logic where `cash_balance` and `sma` are only persisted to the `portfolios` table if both the `portfolio_positions` update and the `trades` ledger entry succeed. This prevents "Phantom Deductions" if the DB connection fails mid-operation.*
*   **Immediate Consistency:** *Recalculates and persists final Reg T metrics to the `portfolios` table immediately after every trade to ensure the dashboard remains accurate between scheduled snapshots.*
*   **Rejection Logic:** *Decisions that fail Validation, Reg T, or **Ownership** checks are NOT discarded. They are saved to `decisions` with a status (e.g., `REJECTED_MARGIN`, `REJECTED_OWNERSHIP`) to preserve the full "Audit Trail" of AI intent.*
*   documentation: ./engine/trade-settlement-walkthrough.md

**12a. Real-time P&L Tracking (SQL View)** ✅

*   **Outcome:** Provides live Profit/Loss USD and % for all active positions.

**13. Attribution Locking** ✅
*   **Tech:** Supabase Postgres
*   *Update the `decisions` table to link the now-generated `TradeID` (from Step 12) to the `DecisionID`. We now have a machine-auditable path: **News -> Reasoning -> Decision -> Trade**.*
*   documentation: ./engine/attribution-locking-walkthrough.md

**14. Ledger & Equity Curve Update** ✅

*   **Tech:** Supabase Postgres
*   **Action:** *Calculate the new total Net Liquidation Value. Write an immutable row for today's performance.*
*   **Update:** *Crucially, it also updates the main `portfolios` summary table with the final calculated Reg T metrics (Equity, Moving SMA, Maintenance Margin) following all executions.*
*   **Idempotency:** *Enforce database constraints on `(portfolio_id, date)` to ensure performance is never double-counted.*
*   documentation: [step-14-ledger-equity-curve.md](./engine/step-14-ledger-equity-curve.md)

**14a. Price Update Utility (Non-LLM)** ✅

*   **Tech:** Python / `update_prices.py`
*   **Goal:** Refresh market prices and recalculate portfolio metrics without invoking the expensive LLM analysis loop.
*   **Usage:** Use this script to update the dashboard's "Live Equity" and "Buying Power" between daily newsletter ingestions.
*   File: `apps/engine/update_prices.py`

**15. Long-term Memory Embedding** ✅

*   **Tech:** **Supabase pgvector (Google Gemini text-embedding-004)**
*   **Decoupled RAG:** *The engine separates **Macro Context** (events in `memories`) from **Strategy Context** (trade reasonings in `decisions`).*
*   **Retrieval:** *During analysis, the engine performs a parallel search across both tables to provide the LLM with a unified view of the market environment and its own past logic.*
*   documentation: [step-15-long-term-memory-embedding.md](./engine/step-15-long-term-memory-embedding.md)

### Phase 4: Frontend & Feedback

**16. Interactive Dashboard** ✅

*   **Tech:** **TanStack Start (Vite + React)**
*   *Server-side rendering for SEO, client-side hydration for interactivity.*
*   **State:** *TanStack Query handles real-time data fetching and caching of stock charts.*
*   *Displays the "Audit Trail" so users can click a trade and see the exact newsletter quote that triggered it.*
*   **Agent Portfolios:** Dedicated [Portfolios UI](./web/portfolios-ui.md) for tracking AI agent performance and holdings.
*   **Documentation:** [Web Application Architecture & Structure](./web/README.md)
*   **Public Insights:** A public [Memories Page](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/web/src/routes/memories/index.tsx) allows users to explore the AI's long-term market perspective, including consensus events and trade reasoning.

**16a. Testing Infrastructure** ✅
*   **Tech:** **Vitest + React Testing Library**
*   **Goal:** Ensure UI reliability and logic correctness for complex frontend components.
*   **Documentation:** [Frontend Testing](./web/testing.md)

**16b. Concept Cluster Map** ✅
*   **Tech:** **D3.js + React**
*   **Visualizing Trends:** A 2D scatter plot visualizing semantic relationships between market concepts.
*   **Coordinates:** Calculated via PCA (Principal Component Analysis) on the python backend to reduce 768-dim embeddings to 2D.
*   **Route:** `/concepts`
*   **Features:** 
    *   **Hybrid Visualization:** Nodes are colored by **Velocity** (Red=Trending, Blue=Stable) to show momentum at a glance.
    *   **Spatial Heatmap:** Background "islands" are colored by **Semantic Position** (Rainbow) to group related concepts.
    *   **Interactive Topography:** Hovering over a background region highlights the entire cluster and identifies the Region Name, creating an explorable "Terrain Map" of the market.
    *   **Temporal Tracking:** Tooltips display both **"First seen"** and **"Last seen"** dates for each concept, allowing users to track the lifespan of market narratives.

**17. Google Authentication** ✅
*   **Tech:** **Supabase Auth (OAuth 2.0)**
*   **Goal:** Enable secure, one-click login for users using their Google accounts, integrated with the project's RLS policies.
*   **Action:** Uses `signInWithOAuth` on the client side to handle the redirect flow and session management.
*   **Implementation Best Practice:** Uses a dual-client approach (Server Client for SSR/Server Functions and Browser Client for OAuth redirects) to maintain session consistency.
*   documentation: [auth-walkthrough.md](./engine/auth-walkthrough.md)

**18. Community Interaction**
*   **Tech:** **Supabase Auth**
*   *Users log in to comment on trades.*
*   **Security:** *Postgres Row Level Security (RLS) ensures only authenticated users can post, and only Admins can write to the Ledger.*

**19. Observability & Health**
* **Tech:** Sentry
* *Log parsing failures or API timeouts.*

**20. Analytics & Growth**

* **Tech:** PostHog
* *Track which AI's reasoning page is most read.*

**21. Regret-Driven Reinforcement (Post-Mortem & Manager Agent)** ✅

* **Tech:** Python / Gemini Flash 3 / pgvector
* **Logic:** *Exactly 5 days after a trade, the **Manager Agent** performs a "Post-Mortem." It compares the AI's reasoning to the actual 5-day price performance.*
* **Outcome:** *Generates "Lessons Learned" (stored as `LESSON_LEARNED` memories) and injects them back into the Long-term Memory (pgvector). This allows the AI to recognize its own past hallucinations or strategic errors in future RAG retrievals.*
* File: `apps/engine/analysis/post_mortem.py`

**22. Contrarian Agent Execution** ✅

* **Tech:** Python / Gemini Flash 3
* **Logic:** *Runs after the primary agents, analyzing their consensus to identify crowded trades or missed risks.*
* **Outcome:** *Executes contrarian trades in a dedicated portfolio.*
* File: `apps/engine/analysis/contrarian.py`

**23. Government Budget & Policy Tracking** ✅

* **Tech:** Python / Gemini Flash 3
* **Logic:** *Monthly pipeline that identifies government incentives, budgets, and objectives.*
* **Outcome:** *Stores findings as `GOVERNMENT_INCENTIVE` memories with expiry dates to inform future analysis.*
* File: `apps/engine/ingest/government.py`

---

## 5. Maintenance & Utilities

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

> [!CAUTION]
> The `clear_db.py` script is destructive and cannot be undone. Use it only when you want to restart all LLM experiments from zero.

## 6. Environment & Security
### Key Management Strategy

We use a **Scoped `.env**` approach. Each service only has access to the variables it needs. For local development, use a `.env.example` as a template.

**Critical Rule:** Never commit `.env` files. Add them to the root `.gitignore`.

### Required Variables

| Service | Variable Name | Description | Required For |
| --- | --- | --- | --- |
| **Global** | `DATABASE_URL` | Supabase Postgres Connection String | Engine, Database Migrations |
|  | `SUPABASE_URL` | Supabase API URL | Web (Frontend), Engine |
| **Engine** | `OPENAI_API_KEY` | OpenAI API Key (Model: `gpt-5-mini`) | Trading Analysis, Embeddings |
|  | `ANTHROPIC_API_KEY` | Claude API Key (Model: `claude-haiku-4-5`) | Trading Analysis |
|  | `GEMINI_API_KEY` | Google Gemini API Key (Model: `gemini-3-flash-preview`) | Trading Analysis |
|  | `DEEPSEEK_API_KEY` | DeepSeek API Key (Model: `deepseek-reasoner`) | Trading Analysis |
|  | `FINANCIAL_API_KEY` | e.g., Financial Modeling Prep (Optional for yfinance) | Price Data & Validation |
|  | `FINANCIAL_PROVIDER` | `fmp` or `yfinance` (Default: `yfinance`) | Selection of price data source |
|  | `FINANCIAL_API_THROTTLE_SECONDS` | Delay between consecutive API calls (Recommended: 2.0) | Rate Limit Prevention |
| **Web** | `VITE_SUPABASE_URL` | Supabase API URL (Exposed to Browser) | Frontend Auth & Data Fetching |
|  | `VITE_SUPABASE_ANON_KEY` | Supabase Anon Key (Exposed to Browser) | Frontend Auth & Data Fetching |

> [!TIP]
> **Vite Prefixing:** Any environment variable used in the browser (client-side code) MUST be prefixed with `VITE_`. Vite automatically strips non-prefixed variables from the client bundle for security.

> [!NOTE]
> **Security of Anon Key:** It is standard practice and safe to expose the `Supabase URL` and `Anon Key` to the frontend. Security in Supabase is enforced via **Row Level Security (RLS)** at the database layer. NEVER expose the `SERVICE_ROLE_KEY` to the client.

> [!CAUTION]
> **Vite Prefixing:** Only variables prefixed with `VITE_` are exposed to the frontend. All Python/Engine keys **must not** have this prefix to prevent accidental exposure via client-side bundles.

### Latest Model Configuration

The engine is currently optimized for these specific versions:

```bash
OPENAI_MODEL="gpt-5-mini"
ANTHROPIC_MODEL="claude-haiku-4-5"
GEMINI_MODEL="gemini-3-flash-preview"
DEEPSEEK_MODEL="deepseek-reasoner"
```

### Local Setup Flow

1. **Root Directory:** No `.env` file (avoids confusion).
2. **`apps/engine/.env`**: Contains all LLM and Broker keys.
3. **`apps/web/.env`**: Contains only Supabase connection keys.
4. **GitHub Secrets**: Add all the above to **Settings > Secrets and Variables > Actions** to enable the 09:35 ET automated pipeline.


## Information Flow

```mermaid
graph TD
    subgraph "Development & CI/CD"
        DEV[Developer Code Change] --> CI[GitHub Actions: ci.yml]
        CI -->|Pass| MAIN[Merge to main]
    end

    subgraph "Daily Pipeline (Phase 1)"
        CRON[Cron Schedule 09:35 ET] --> INGEST[ingest.yml]
        INGEST --> A[Gmail Newsletters]
        A --> B[Data Snapshot + Chunk IDs]
    end

    subgraph "Reasoning & Consensus (Phase 2)"
        B --> C{Context Retrieval}
        C <-->|Query History| V[Supabase pgvector]
        
        C --> D1[OpenAI Batch Analysis]
        C --> D2[Claude Batch Analysis]
        C --> D3[Gemini Batch Analysis]
        C --> D4[DeepSeek Batch Analysis]
        
        D1 & D2 & D3 & D4 --> AT[Decision Attribution Layer]
        AT -->|Map Reasoning to ChunkID| DB[(Decisions Table)]
        
        AT --> CP{Event Consensus Protocol}
        CP -->|Semantic Grouping + Dedupe| SYN[LLM Synthesis]
        
        SYN --> TM[Trend & Momentum Analysis]
        TM -->|Update Velocity| CM[(Concept Metrics)]
        TM -->|Promote 2+ Agreement| G[Global Timeline]
        
        SYN --> E{Hallucination Guardrails}
    end

    subgraph "Execution & Memory (Phase 3 & 4)"
        E -->|Fail| F[Reject (Hallucination Guardrails)]
        E -->|Pass| G[Global Timeline]
        E -->|Pass| H[Execution Engine]
        
        H --> I[Supabase Ledger]
        I -->|Link TradeID| DB
        
        I --> LS[Performance Snapshot]
        LS --> J[TanStack Start Dashboard]
        
        I --> ME[Memory Embedding]
        ME -->|Vectorize reasoning| V
        
        G --> J
        K[User Comments] -->|Supabase Auth| J
    end
```
