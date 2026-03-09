# Project Overview: AI Wall Street

## 1. Project Summary

### What It Does

An automated platform where six LLMs (**OpenAI, Claude, Gemini, DeepSeek, Contrarian Agent, Manager Agent**) compete in a virtual stock market. Every morning, they parse financial newsletters, debate major global events, analyze government incentives, and rebalance their portfolios.

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
├── docs/                    # Technical Walkthroughs
└── tests/                   # Engine & Web tests
```

## 3. The Daily Pipeline (Phase 1-22)

For a detailed step-by-step walkthrough, see **[data-flow.md](./engine/data-flow.md)**.

### Phase 1: Ingestion & Normalization
1. **Daily Trigger (09:35 ET):** GitHub Actions fires the pipeline.
2. **Newsletter Ingestion:** Scrapes unread emails; removes ads via Gemini Flash.
3. **Corporate Action Check:** (PENDING).
4. **Data Snapshotting:** Save raw text and current prices with idempotency keys.

### Phase 2: Consensus & Attribution
5. **Parallel LLM Analysis:** OpenAI, Claude, Gemini, and DeepSeek generate trade signals using active tools. Agents now identify countries and map them to liquid ETFs (e.g., Japan -> EWJ, Brazil -> EWZ) and formulate long-term strategy reasoning.
6. **RAG Context Retrieval:** Query `memories` and `decisions` for historical context (labeled to distinguish from current holdings).
7. **Decision Attribution:** Map reasoning, strategy intent, and metadata to the `decisions` table.
8. **Event Consensus:** Synthesize global macro events with **Scenario Analysis** (evaluating "If X vs If Y" outcomes); group semantically via pgvector.
9. **Trend Analysis:** Calculate concept momentum and update PCA coordinates for the map.

### Phase 3: Execution & Guardrails
10. **Second-Step Verification**: A skeptical "Verifier" agent (using the original decision's provider) audits BUY/SELL signals, evaluating not just price but also the **Strategic Intent** and **Advance Planning** of the trade.
11. **Trade Abort/Adjustment**: Verification results can force a `REJECTED_VERIFICATION` or `ADJUSTED_ALLOCATION` before money moves.
12. **Pre-Market Validation**: Existence, price banding, and liquidity checks with automated engine-level backfill for missing LLM prices.
13. **Reg T Margin Validation**: Ensure buying power and SMA safety floor.
12. **Trade Settlement:** Atomic updates to cash, positions, and ledger.
13. **Attribution Locking:** Link final `TradeID` to the triggering decision.
14. **Ledger Update:** Daily equity curve snapshot.

### Phase 5: Feedback & Specialized Agents
21. **Post-Analysis (Manager Agent):** Compare reasoning to multi-interval performance; generate lessons.
22. **Contrarian Agent:** Identifies crowded trades or missed risks.
23. **Skeptical Verifier Agent:** Performs just-in-time audits of every trade signal.
24. **Government Tracking:** Monthly audit of incentives and policies.

### Phase 3: Market Execution (Sequential)

**10. Second-Step Verification** ✅

*   **Tech:** Python / Multi-Provider Tool Loop
*   **Logic:** *Every BUY/SELL signal is intercepted by a dedicated verifier.*
*   **Dynamic Provider**: *The verifier uses the **same intelligence profile** (e.g., Anthropic, Gemini) as the original generator.*
*   **Skepticism SOP**: *Checks if news is "priced in" via history, identifies at least two failure modes, and searches for "Silver to our Gold" alternative plays using **Vector-Based Sector Analysis**. Crucially, it now **audits the agent's strategic reasoning** (e.g., "sell X to fund Y") for logical consistency.*
*   **Robust Tooling**: *Universal tool implementation supports complex structured outputs (Anthropic) and safe content parsing (Gemini), enabling diverse models to act as verifiers. The verification layer is designed with **Sync/Async Resilience**, safely handling both native Google SDK response objects and asynchronous OpenAI/Anthropic patterns. Assistant text responses are automatically stripped of trailing whitespace to ensure compliance with strict API validation rules. The engine now correctly maps provider-specific roles (e.g., using 'model' for Gemini) to maintain session integrity during high-volume tool loops.*
*   **Market Data Fallback & Robustness**: *Uses an enhanced `MarketDataManager` that automatically pulls historical prices from **IBKR Proxy** (with YFinance fallback) if local data is missing for a new ticker. For ETFs (like `BDRY`), the engine accurately evaluates liquidity by falling back to `totalAssets` or `netAssets` when `marketCap` is unavailable. The engine uses a **Singleton Connection Pattern** (with robust `finally` cleanup) for providers that require persistent connections, ensuring high-concurrency tool loops never result in port conflicts.*
*   **Outcome**: *Approves, rejects, or shrinks the trade allocation based on price risk and strategic intent.*

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
*   **Usage:** Use this script to update the dashboard's "Live Equity" and "Buying Power" between daily newsletter ingestions. Automatically triggered at 13:00 ET via GitHub Actions.
*   File: `apps/engine/update_prices.py`

**15. Long-term Memory Embedding** ✅

*   **Tech:** **Supabase pgvector (Google Gemini gemini-embedding-001)**
*   **Decoupled RAG:** *The engine separates **Macro Context** (events in `memories`) from **Strategy Context** (trade reasonings in `decisions`).*
*   **Scenario Awareness:** *Memories now incorporate **Scenario Analysis**, allowing models to recall not just what happened, but different ways an event was expected to resolve.*
*   **Retrieval:** *The engine performs a parallel search across both tables to provide the LLM with a unified view of the market environment and its own past logic.*
*   **Schema Robustness:** *Includes automated JSON string parsing, Pydantic field validation to convert `NaN` values to `None`, and expanded `catalyst_type` literals to handle model "Semantic Fragility" during high-volume tool loops.*
*   **Deduplication:** *Enforces a 24-hour lookback window to prevent semantic duplicates of the same event from being stored (Similarity > 0.90).*
*   documentation: [step-15-long-term-memory-embedding.md](./engine/step-15-long-term-memory-embedding.md)

### Phase 4: Frontend & Feedback

**16. Interactive Dashboard** ✅

*   **Tech:** **TanStack Start (Vite + React)**
*   *Server-side rendering for SEO, client-side hydration for interactivity.*
*   **State:** *TanStack Query handles real-time data fetching and caching of stock charts.*
*   **TODAY Dashboard**: The primary entry point (`/`) providing a high-level narrative of the day's events, including AI consensus, news ingestion, and trade executions.
    *   **Horizon Watch**: Tracks pending market catalysts with standardized ISO dates and "tentative" vs "exact" labels.
*   **Audit Trail:** Users can explore the AI's logic on any execution or rejection directly from the **TODAY** dashboard. Clicking an item in the "Market Execution & Guardrails" section reveals the full LLM thought process and reasoning in an interactive drawer.
*   **Agent Portfolios:** Dedicated [Portfolios UI](./web/portfolios-ui.md) for tracking AI agent performance and holdings.
*   **Documentation:** [Web Application Architecture & Structure](./web/README.md)
*   **Hosting & Deployment:** [Netlify Deployment (benchify)](./web/tanstack-start-deploy-official.md)
*   **Live Dashboard:** [benchify.netlify.app](https://benchify.netlify.app)
*   **Public Insights:** A public [Memories Page](file:///home/cv/Documents/Code/llm-market-bench/apps/web/src/routes/memories/index.tsx) allows users to explore the AI's long-term market perspective.
    *   **Event Linking:** Browse related "Update" events and trace their parent origins.
    *   **Flow View:** An interactive, infinite-canvas visualization of narrative threads and event chains.
*   **Reasoning**: A research-grade audit trail with a human-friendly tabbed UI, showing every LLM interaction, tool call, and internal "thought" trace categorized by task type.
*   **How it Works**: A conceptual overview of the agentic pipeline.
    *   **Phase Breakdown:** Ingestion → Analysis → Verification → Execution → Feedback.
    *   **User Education:** Helps users understand the data flow from newsletters to executed trades.

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

**21. Regret-Driven Reinforcement (Post-Analysis & Manager Agent)** ✅

* **Tech:** Python / Gemini Flash 3 / pgvector
* **Logic:** *At multiple intervals (5, 14, 30 days) after a trade, the **Manager Agent** performs a "Post-Analysis." It compares the AI's reasoning to the actual price performance.*
* **Outcome:** *Generates "Lessons Learned" (stored as `LESSON_LEARNED` memories) and injects them back into the Long-term Memory (pgvector). This allows the AI to recognize its own past hallucinations or **strategic planning errors** in future RAG retrievals.*
* File: `apps/engine/analysis/post_analysis.py`

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

> The `clear_db.py` script is destructive and cannot be undone. Use it only when you want to restart all LLM experiments from zero.

### Automating Documentation

To insure the `docs/database-schema.md` is always up to date with the actual Postgres schema:

*   **Script:** `apps/engine/generate_schema_docs.py`
*   **Usage:** `python generate_schema_docs.py`
*   **Requirement:** You must add `DATABASE_URL=postgresql://...` to your `apps/engine/.env` file for this script to work (it requires direct SQL access).

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
|  | `FMP_API_KEY` | e.g., Financial Modeling Prep (Optional for yfinance) | Price Data & Validation |
| **Engine**|  | `FINANCIAL_PROVIDER` | `fmp`, `yfinance`, `ibkr` or `ibkr_proxy` (Default: `ibkr_proxy`) | Selection of price data source |
|  | `FALLBACK_FINANCIAL_PROVIDER` | `fmp`, `yfinance`, `ibkr` or `ibkr_proxy` (Default: `yfinance`) | Selection of fallback data source |
|  | `IBKR_HOST` | Host for IBKR Gateway/TWS (Default: `127.0.0.1`) | [LEGACY] Local market data via IBKR |
|  | `IBKR_PORT` | Port for IBKR Gateway/TWS (Default: `7496`) | [LEGACY] Local market data via IBKR |
|  | `IBKR_CLIENT_ID` | Client ID for IBKR connection (Default: `1`) | [LEGACY] Local market data via IBKR |
|  | `IBKR_PROXY_URL` | URL of the IBKR Proxy server | Market data via Proxy |
|  | `IBKR_PROXY_TOKEN` | Auth token for the IBKR Proxy (Optional if using JWT) | Market data via Proxy |

For detailed setup instructions, see [IBKR Integration Guide](IBKR-Integration.md).
|  | `FINANCIAL_API_THROTTLE_SECONDS` | Delay between consecutive API calls (Recommended: 2.0) | Rate Limit Prevention |
|  | `MIN_TRADE_VALUE` | Minimum purchase/sell value for LLM-driven trades (Default: 1000.0) | Trade Validation |
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
4. **GitHub Secrets**: Add all the above to **Settings > Secrets and Variables > Actions**.
   - **Secrets**: Use for sensitive keys (API Keys, Tokens, URLs).
   - **Variables**: Use for optional configuration overrides (e.g., `FINANCIAL_PROVIDER`, `OPENAI_MODEL`).

### GitHub Actions Configuration

The daily pipeline in `.github/workflows/ingest.yml` explicitly maps Secrets and Variables to the engine. Ensure the following are set in GitHub to avoid failures:

#### Required Secrets
- `IBKR_PROXY_URL`: The public URL of your proxy.
- `IBKR_PROXY_TOKEN`: The secret key for your proxy.
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.
- `SUPABASE_PROJECT_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

#### Optional Variables
You can override default models or providers without code changes by adding these as **Repository Variables**:
- `FINANCIAL_PROVIDER`: Defaults to `ibkr_proxy`.
- `OPENAI_MODEL`, `GEMINI_MODEL`, etc.


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
        
        CP --> VER[Skeptical Verifier Agent]
        VER --> MDM[MarketDataManager]
        MDM -->|Proxy| IBKR[IBKR Proxy]
        MDM -->|Fallback| YF[YFinance]
        VER -->|Abort/Adjust| E{Execution Guardrails}
        
        E -->|Cleanup| CL[Provider disconnect_all]
        
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

    subgraph "Analysis & Feedback (Phase 5)"
        I --> PM[Manager Agent: Post-Analysis]
        PM -->|Lessons Learned| V
        
        CP --> CA[Contrarian Agent]
        CA -->|Counter-Signals| H
        
        GOV[Gov Tracking] -->|Incentives| V
    end
```

## 7. Deployment & Hosting

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
