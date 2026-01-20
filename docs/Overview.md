# Project Overview: AI Wall Street

## 1. Project Summary

### What It Does

An automated platform where four LLMs (**OpenAI, Claude, Gemini, DeepSeek**) compete in a virtual stock market. Every morning, they parse financial newsletters, debate major global events, and rebalance their portfolios.

### Why It Matters

* **Performance Benchmarking:** Real-world test of LLM reasoning vs. S&P 500.
* **The "Consensus" Effect:** Identifies where AI models agree or diverge on global risks.
* **Decision Attribution:** Provides a machine-auditable trail from raw news chunk to final trade execution.
* **Memory Integrity:** Tests if LLMs can maintain a consistent world view using Vector RAG (Retrieval-Augmented Generation).

## 2. Technical Architecture & Repo Structure

The project follows a **Monorepo** structure to keep the Python Data Engine and the TypeScript Frontend synchronized while separating concerns.

**Repository Organization:**

```text
ai-wallstreet/
├── apps/
│   ├── web/                 # TanStack Start (Frontend)
│   │   ├── app/             # File-based routing
│   │   ├── components/      # Shared UI components
│   │   └── utils/           # TanStack Query hooks
│   └── engine/              # Python (The Backend Pipeline)
│       ├── core/            # LLM clients (Instructor/Pydantic models)
│       ├── ingest/          # Newsletter scrapers
│       ├── attribution/     # Decision mapping & audit trail logic
│       ├── analysis/        # Trend & momentum analysis logic
│       ├── execution/       # Trade Settlement & Idempotency logic
│       ├── memory/          # RAG logic for pgvector
│       └── main.py          # Entry point for Cron jobs
├── packages/
│   └── database/            # Shared Supabase types/schemas
├── supabase/                # SQL Migrations, RLS policies, & Vector setup
    └── workflows/           # CI/CD & Cron schedules
        ├── ci.yml           # Automated testing on PR/Push
        └── ingest.yml       # Daily consolidated pipeline (09:35 ET)

```

## 3. The 17-Step Daily Pipeline

For a detailed step-by-step walkthrough with a concrete example of how data flows through the entire pipeline (from Gmail newsletters to trading decisions), see **[data-flow.md](./data-flow.md)**. This document traces 4 sample newsletters through each phase with actual API calls and database operations documented.

### Phase 1: Ingestion & Normalization

**1. Daily Trigger (09:35 ET)** ✅

* **Tech:** GitHub Actions (Cron)
* **Goal:** Fire the pipeline 5 minutes after market open to capture live prices.
* File: .github/workflows/ingest.yml

**1a. Quality Assurance (CI/CD)** ✅

* **Tech:** GitHub Actions / Pytest
* **Logic:** *Automatically runs unit tests for core configuration and ingestion utilities on every pull request and push to the `main` branch. This serves as a security/stability gate for the engine.*
* File: .github/workflows/ci.yml
* documentation: ./docs/testing.md

**2. Newsletter Ingestion** ✅

* **Tech:** Python / Gmail API
* *Scrape unread newsletters into raw text chunks. Each chunk is assigned a unique `SourceID` and `ChunkHash` for attribution.*
* File: apps/engine/ingest/newsletter.py
* documentation: ./docs/newsletter-ingestion-walkthrough

**3. Corporate Action Check** - PENDING - ⏳

* **Tech:** Python / Market API
* *Check for stock splits/dividends. Adjust the "Virtual Portfolio" holdings before the LLM sees them to prevent fake price-drop panics.*

**4. Data Snapshotting (Idempotency Layer)** ✅

* **Tech:** Supabase Postgres
* *Save the raw newsletter text and current prices.*
* **Constraint:** *Use a composite unique key (Date + SourceID) to prevent duplicate processing if the job restarts.*
* documentation: ./docs/data-snapshotting-walkthrough

### Phase 2: The Consensus & Attribution Engine

**5. Parallel LLM Analysis (Structured Output)** ✅

*   **Tech:** OpenAI, Claude, Gemini, DeepSeek APIs
*   **Validation:** **Python Pydantic + Instructor**
*   **Active Tool Calling:** LLMs utilize the `get_stock_quote` tool *during* analysis to verify ticker existence, real-time pricing, and liquidity before making a recommendation.
*   **Portfolio Context Injection:** *LLMs receive their current Cash, Equity, and Buying Power in the prompt, allowing them to make "Allocation %" decisions rather than just static share counts.*
*   **Efficiency:** **Batch Processing** (Each LLM is called in a tool-calling loop with all daily news chunks to minimize latency and costs).
*   *Force LLMs to adhere to a strict JSON schema for trade signals. If an LLM outputs malformed JSON, `Instructor` automatically loops back the error to the LLM for correction.*
*   *LLMs must return a `DecisionObject` containing the signal (Buy/Sell/Hold) AND the `SourceID` of the news chunk that triggered it.*
*   **Fault Tolerance:** If individual LLM providers fail, the pipeline continues with successful results. CRITICAL alerts are logged if all 4 providers fail.
*   documentation: ./docs/llm-analysis-walkthrough.md

**6. RAG Context Retrieval** ✅

*   **Tech:** **Supabase pgvector**
*   *Before analyzing today's news, the engine queries the vector store for relevant PAST events/trades to ensure the AI's reasoning is consistent with its history.*
*   documentation: ./docs/rag-context-retrieval.md

**7. Decision Attribution Layer** ✅

*   **Tech:** Python Logic / Supabase
*   **Audit Trail:** *Map the `ModelID` + `NewsChunkID` + `LLMReasoningString` into a `decisions` table. This creates a foreign key link between a Trade and the specific sentence in a newsletter that caused it.*
*   **Idempotency:** *Uses UPSERT with unique constraint on `(source_id, ticker, signal, model_provider, model_name)` to prevent duplicate decisions if the pipeline reruns.*
*   documentation: ./docs/decision-attribution-walkthrough.md

**8. Event Consensus Protocol** ✅

*   **Tech:** Python / Gemini Embeddings / OpenAI Synthesis
*   **Semantic Grouping:** Uses **Vector Embeddings** and **Cosine Similarity** to group events with different names but similar meanings (e.g., "Fed Hike" vs "Interest Rate Hike").
*   **Temporal Deduplication:** Checks the `memories` table to skip events promoted in the last 48 hours, keeping the timeline clean.
*   **LLM Synthesis:** For each consensus cluster, a fast LLM pass synthesizes a professional, unified event name and a 1-sentence summary.
*   **Consensus Rule:** An event group is promoted to the **Global Timeline** (memories) if 2+ models identify it.
*   **Impact Tie-Breaker:** When models are split between BULLISH and BEARISH, the system defaults to NEUTRAL to avoid non-deterministic behavior.
*   documentation: ./docs/event-consensus-walkthrough.md

**9. Trend & Concept Momentum Analysis** ✅
*   **Tech:** Supabase pgvector / Python
*   **Vectorized Frequency:** Instead of just counting keywords, the engine embeds the "Concept" (e.g., "NVIDIA Blackwell Delay") and performs a similarity search against the memories table to find semantically related mentions over a rolling 90-day window.
*   **Semantic Merging:** Prevents data fragmentation by automatically merging concepts with $> 0.90$ similarity into a single "Master Concept" record.
*   **Trend Archeology:** Each mention is stored with a first_seen_at timestamp and a cumulative 90-day frequency count.
*   **Momentum Scoring:** The engine calculates a "Velocity Score" based on mention frequency acceleration (Recent 24h vs. 7-day baseline).
*   **Velocity Decay:** Stale concepts have their velocity scores reduced by 50% after 28 days of inactivity (half-life decay model), preventing outdated trends from persisting.
*   **Data Structure:** Updates a `concept_metrics` table tracking concept_vector, mention_count, first_mention_date, and velocity_score.
*   documentation: ./docs/trend-momentum-analysis.md

**9.a. General Review**
* documentation: ./docs/claude-step-9-and-before-review.md

**10. Pre-Market Validation (Hallucination Guardrails)** ✅

* **Tech:** Python / `MarketDataManager` / yfinance or FMP
* **Cache-First Architecture:** Uses a `market_data_cache` table in Supabase (4-hour TTL) to minimize external API dependencies and prevent rate limits.
* **Guardrail A (Existence):** *Verify ticker exists and is not delisted.*
* **Guardrail B (Price Banding):** *If AI wants to "Buy AAPL at $50" but market price is $150, reject trade (Price Hallucination).*
* **Guardrail C (Liquidity):** *Reject tickers with Market Cap < $2B (Penny Stock protection).*
* **Double-Layer Security:** These guardrails run both as an LLM Tool (Phase 2, Step 5) and as a final validation gauntlet before execution.
* documentation: ./docs/pre-market-validation.md
* File: `apps/engine/execution/market_data.py`, `apps/engine/execution/validation.py`

### Phase 3: Market Execution (Sequential)

**11. Pre-Execution Margin Validation** ✅

* **Tech:** Python / Supabase / Reg T Logic
* **Logic:** *Before moving a decision to "Trade Settlement", the engine validates that the agent has sufficient Buying Power.*
* **Rule:** *Check `portfolio.buying_power` against the estimated cost of the trade. If `Cost > Buying Power`, reject the trade to prevent negative balances. Allows valid leveraged trades.*
* **Persistence:** *Portfolios are stored in `portfolios` and `portfolio_positions` tables to maintain state across daily runs.*
* documentation: ./docs/portfolio-management-walkthrough.md

**12. Trade Settlement & Ledgering** ✅

* **Tech:** Python / Portfolio Class
* **Logic:** *Execute `portfolio.execute_trade()` for valid decisions.*
* **Action:** *Updates `cash_balance`, `sma`, and `portfolio_positions`. **Crucially, inserts a record into the `trades` table to generate a unique `TradeID` for the execution.***
* **Rejection Logic:** *Decisions that fail Validation or Reg T checks are NOT discarded. They are saved to `decisions` with a status (e.g., `REJECTED_MARGIN`, `REJECTED_GUARDRAIL`) to preserve the full "Audit Trail" of AI intent.*
* documentation: ./docs/trade-settlement-walkthrough.md

**13. Attribution Locking** ✅
* **Tech:** Supabase Postgres
* *Update the `decisions` table to link the now-generated `TradeID` (from Step 12) to the `DecisionID`. We now have a machine-auditable path: **News -> Reasoning -> Decision -> Trade**.*
* documentation: ./docs/attribution-locking-walkthrough.md

**14. Ledger & Equity Curve Update**

* **Tech:** Supabase Postgres
* *Calculate the new total Net Liquidation Value. Write an immutable row for today's performance.*
* **Idempotency:** *Enforce database constraints on `(model_id, date)` to ensure performance is never double-counted.*

**15. Long-term Memory Embedding**

* **Tech:** **Supabase pgvector (OpenAI text-embedding-3-small)**
* *Embed consensus events and the attributed reasoning for future RAG retrieval.*

### Phase 4: Frontend & Feedback

**16. Interactive Dashboard**

* **Tech:** **TanStack Start (Vite + React)**
* *Server-side rendering for SEO, client-side hydration for interactivity.*
* **State:** *TanStack Query handles real-time data fetching and caching of stock charts.*
* *Displays the "Audit Trail" so users can click a trade and see the exact newsletter quote that triggered it.*

**17. Community Interaction**
* **Tech:** **Supabase Auth**
* *Users log in to comment on trades.*
* **Security:** *Postgres Row Level Security (RLS) ensures only authenticated users can post, and only Admins can write to the Ledger.*

**18. Observability & Health**

* **Tech:** Sentry
* *Log parsing failures or API timeouts.*

**19. Analytics & Growth**

* **Tech:** PostHog
* *Track which AI's reasoning page is most read.*

---

## 4. Environment & Security
### Key Management Strategy

We use a **Scoped `.env**` approach. Each service only has access to the variables it needs. For local development, use a `.env.example` as a template.

**Critical Rule:** Never commit `.env` files. Add them to the root `.gitignore`.

### Required Variables

| Service | Variable Name | Description | Required For |
| --- | --- | --- | --- |
| **Global** | `DATABASE_URL` | Supabase Postgres Connection String | Engine, Database Migrations |
|  | `SUPABASE_URL` | Supabase API URL | Web (Frontend), Engine |
| **Engine** | `OPENAI_API_KEY` | OpenAI API Key (Model: GPT-4o) | Trading Analysis, Embeddings |
|  | `ANTHROPIC_API_KEY` | Claude 3.5 Sonnet API Key | Trading Analysis |
|  | `GEMINI_API_KEY` | Google Gemini 1.5 Pro API Key | Trading Analysis |
|  | `DEEPSEEK_API_KEY` | DeepSeek-V3 API Key | Trading Analysis |
|  | `FINANCIAL_API_KEY` | e.g., Financial Modeling Prep (Optional for yfinance) | Price Data & Validation |
|  | `FINANCIAL_PROVIDER` | `fmp` or `yfinance` (Default: `yfinance`) | Selection of price data source |
|  | `FINANCIAL_API_THROTTLE_SECONDS` | Delay between consecutive API calls (Recommended: 2.0) | Rate Limit Prevention |
| **Web** | `VITE_SUPABASE_ANON_KEY` | Supabase Client Key | Frontend Auth & Data Fetching |

> [!CAUTION]
> **Vite Prefixing:** Only variables prefixed with `VITE_` are exposed to the frontend. All Python/Engine keys **must not** have this prefix to prevent accidental exposure via client-side bundles.

### Local Setup Flow

1. **Root Directory:** No `.env` file (avoids confusion).
2. **`apps/engine/.env`**: Contains all LLM and Broker keys.
3. **`apps/web/.env`**: Contains only Supabase connection keys.
4. **GitHub Secrets**: Add all the above to **Settings > Secrets and Variables > Actions** to enable the 08:00 ET automated pipeline.


## Information Flow

```mermaid
graph TD
    subgraph "Development & CI/CD"
        DEV[Developer Code Change] --> CI[GitHub Actions: ci.yml]
        CI -->|Pass| MAIN[Merge to main]
    end

    subgraph "Daily Pipeline (Phase 1)"
        CRON[Cron Schedule 08:00 ET] --> INGEST[ingest.yml]
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

    subgraph "Execution & Feedback (Phase 3 & 4)"
        E -->|Fail| F[Reject (Hallucination Guardrails)]
        E -->|Pass| G[Global Timeline]
        E -->|Pass| H[Execution Engine]
        
        H --> I[Supabase Ledger]
        I -->|Link TradeID| DB
        I --> J[TanStack Start Dashboard]
        G --> J
        K[User Comments] -->|Supabase Auth| J
    end
```
