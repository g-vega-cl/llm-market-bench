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
│       ├── execution/       # Broker API & Idempotency logic
│       ├── memory/          # RAG logic for pgvector
│       └── main.py          # Entry point for Cron jobs
├── packages/
│   └── database/            # Shared Supabase types/schemas
├── supabase/                # SQL Migrations, RLS policies, & Vector setup
    └── workflows/           # CI/CD & Cron schedules
        ├── ci.yml           # Automated testing on PR/Push
        └── ingest.yml       # Daily ingestion (08:00 ET)

```

## 3. The 17-Step Daily Pipeline

### Phase 1: Ingestion & Normalization

**1. Scheduler (08:00 ET)** ✅

* **Tech:** GitHub Actions (Cron)
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

**5. Parallel LLM Analysis (Structured Output)**

* **Tech:** OpenAI, Claude, Gemini, DeepSeek APIs
* **Validation:** **Python Pydantic + Instructor**
* *Force LLMs to adhere to a strict JSON schema for trade signals. If an LLM outputs malformed JSON, `Instructor` automatically loops back the error to the LLM for correction.*
* *LLMs must return a `DecisionObject` containing the signal (Buy/Sell/Hold) AND the `SourceID` of the news chunk that triggered it.*
* documentation: ./docs/llm-analysis-walkthrough.md

**6. RAG Context Retrieval**

* **Tech:** **Supabase pgvector**
* *Before analyzing today's news, the engine queries the vector store for relevant PAST events/trades to ensure the AI's reasoning is consistent with its history.*

**7. Decision Attribution Layer**

* **Tech:** Python Logic / Supabase
* **Audit Trail:** *Map the `ModelID` + `NewsChunkID` + `LLMReasoningString` into a `decisions` table. This creates a foreign key link between a Trade and the specific sentence in a newsletter that caused it.*

**8. Event Consensus Protocol**

* **Tech:** Python Logic
* *Compare events from all 4 models. If 2+ models identify "Fed Rate Hike," it's promoted to the **Global Timeline**. Outlier events are discarded.*

**9. Pre-Market Validation (Hallucination Guardrails)**

* **Tech:** Python / Financial Modeling Prep API
* **Guardrail A (Existence):** *Verify ticker exists and is not delisted.*
* **Guardrail B (Price Banding):** *If AI wants to "Buy AAPL at $50" but market price is $150, reject trade (Price Hallucination).*
* **Guardrail C (Liquidity):** *Reject tickers with Market Cap < $2B (Penny Stock protection).*

### Phase 3: Market Execution

**10. Execution Trigger (09:30 ET)**

* **Tech:** GitHub Actions
* *Fire the second job at the official market open.*

**11. Trade Settlement**

* **Tech:** Python / Market Data API
* *Fetch the official "Open Price." Move orders from `PENDING` to `FILLED` in the ledger.*

**12. Attribution Locking**

* **Tech:** Supabase Postgres
* *Update the `decisions` table to link the now-filled `TradeID` to the `DecisionID`. We now have a machine-auditable path: **News -> Reasoning -> Trade**.*

**13. Ledger & Equity Curve Update**

* **Tech:** Supabase Postgres
* *Calculate the new total Net Liquidation Value. Write an immutable row for today's performance.*
* **Idempotency:** *Enforce database constraints on `(model_id, date)` to ensure performance is never double-counted.*

**14. Long-term Memory Embedding**

* **Tech:** **Supabase pgvector (OpenAI text-embedding-3-small)**
* *Embed consensus events and the attributed reasoning for future RAG retrieval.*

### Phase 4: Frontend & Feedback

**15. Interactive Dashboard**

* **Tech:** **TanStack Start (Vite + React)**
* *Server-side rendering for SEO, client-side hydration for interactivity.*
* **State:** *TanStack Query handles real-time data fetching and caching of stock charts.*
* *Displays the "Audit Trail" so users can click a trade and see the exact newsletter quote that triggered it.*

**16. Community Interaction**
* **Tech:** **Supabase Auth**
* *Users log in to comment on trades.*
* **Security:** *Postgres Row Level Security (RLS) ensures only authenticated users can post, and only Admins can write to the Ledger.*

**17.Observability & Health**

* **Tech:** Sentry
* *Log parsing failures or API timeouts.*

**16. Analytics & Growth**

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
|  | `FINANCIAL_API_KEY` | e.g., Financial Modeling Prep / Alpha Vantage | Price Data & Validation |
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
        
        C --> D1[OpenAI + Instructor]
        C --> D2[Claude + Instructor]
        C --> D3[Gemini + Instructor]
        C --> D4[DeepSeek + Instructor]
        
        D1 & D2 & D3 & D4 --> AT[Decision Attribution Layer]
        AT -->|Map Reasoning to ChunkID| DB[(Decisions Table)]
        
        AT --> E{Validation & Consensus}
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
