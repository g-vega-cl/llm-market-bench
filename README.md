# AI Wall Street: LLM Market Benchmarking Platform

An automated platform where six LLMs (**OpenAI, Claude, Gemini, DeepSeek, Contrarian Agent, Manager Agent**) compete in a virtual stock market. Three times a day during market hours (09:30, 12:30, 15:30 ET), they parse financial newsletters, debate major global events, analyze government incentives, and rebalance their portfolios.

**New: Real-Time Web Search** - Agents now have access to live web search (Anthropic `web_search`, Gemini `google_search`) to verify breaking news, check corporate actions, and fact-check claims before trading. All searches include citations for audit trails.

**New: Stock Screener Tool & Discovery Agent** - All LLMs can now invoke a `run_stock_screener` tool to find investable assets by sector, market cap, beta, volume, and dividend filters. A specialized `DiscoveryAgent` uses this tool to populate the "Investable Assets" section of the AI's memory with high-conviction, data-backed candidates.

## 🚀 Project Overview

This project benchmarks the reasoning capabilities of leading LLMs against the real-world performance of the S&P 500. It features a robust Python-based data engine and a modern React-based frontend.

### Why It Matters

- **Performance Benchmarking:** Real-world test of LLM reasoning vs. S&P 500.
- **The "Consensus" Effect:** Identifies where AI models agree or diverge on global risks.
- **Research Audit Trail:** Provides a full "Thinking Process" trace for every LLM call, including intermediate tool steps, for behavioral research.
- **Decision Attribution:** Provides a machine-auditable trail from raw news chunk to final trade execution.
- **Memory Integrity:** Tests if LLMs can maintain a consistent world view using Vector RAG (Retrieval-Augmented Generation).

For a deep dive into the system design, see the **[Project Overview](./docs/Overview.md)** and the **[Database Schema](./docs/database-schema.md)**.

## 📂 Repository Structure

This is a monorepo managed with `pnpm`:

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
├── packages/
│   └── config/              # Shared configuration (models.json)
└── tests/                   # Engine & Web tests
```

- **`apps/engine`**: The Python pipeline (Ingestion, Analysis, Execution).
- **`apps/web`**: The TanStack Start dashboard (Frontend). [Read the Web Architecture Docs](./docs/web/README.md).
- **`supabase`**: SQL migrations and database configuration.
- **`docs`**: Technical documentation and walkthroughs.

## 🛠️ Getting Started

### Prerequisites

- Python 3.10+
- Node.js 20+ & `pnpm`
- Supabase Account

### Workspace Setup

```bash
pnpm install
```

### Environment Configuration

The project uses a scoped `.env` approach. Each service only has access to the variables it needs.

**Engine (`apps/engine/.env`):**

```bash
# Database
DATABASE_URL=your_supabase_connection_string
SUPABASE_URL=your_supabase_url

# LLM API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GEMINI_API_KEY=your_gemini_key
DEEPSEEK_API_KEY=your_deepseek_key

# Market Data
FMP_API_KEY=your_fmp_key
FINANCIAL_PROVIDER=fmp
IBKR_PROXY_URL=your_ibkr_proxy_url
IBKR_PROXY_TOKEN=your_ibkr_proxy_token

# Web Search (Optional)
ENABLE_ANTHROPIC_WEB_SEARCH=true
ENABLE_GEMINI_WEB_SEARCH=true
```

**Web (`apps/web/.env`):**

```bash
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

> [!NOTE]
> Model names are defined in `packages/config/models.json` — not environment variables.

### Engine Execution

The engine handles the daily pipeline:

```bash
cd apps/engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py ingest
```

### Web Development

To run the dashboard locally:

```bash
pnpm --filter web dev
```

## 🧪 Testing

We maintain a high stability gate for the core engine:

```bash
./apps/engine/market/bin/python3 -m pytest
```

## ⚙️ Automation

- **CI Testing**: Automatically runs on every push to `main`.
- **Daily Pipeline**: Triggered via GitHub Actions at 09:35, 12:35, and 15:35 ET (holiday-aware market hours check).
- **Midday Update**: Price updates every 30 minutes during market hours (approx. 14:00 - 21:00 UTC).

## 📊 Key Features

### The Daily Pipeline (22 Phases)

1. **Ingestion & Normalization**: Newsletter scraping, economic calendar fetch, data snapshotting
2. **Consensus & Attribution**: Parallel LLM analysis with RAG context retrieval, decision attribution
3. **Execution & Guardrails**: Second-step verification, hard tool enforcement, Reg T margin validation
4. **Frontend & Feedback**: Interactive dashboard, memory embedding, post-analysis
5. **Specialized Agents**: Contrarian trades, government tracking, cause & effect analysis
6. **Discovery Agent**: Converts market themes into a high-conviction "Investable Assets" list using `run_stock_screener` and web search in a tool-calling reasoning loop

For a detailed step-by-step walkthrough, see **[Data Flow & Pipeline](./docs/engine/data-flow.md)**.

### Interactive Dashboard

**Live URL**: [benchify.netlify.app](https://benchify.netlify.app)

- **TODAY Dashboard**: High-level narrative of daily events, AI consensus, and trade executions
- **Horizon Watch**: Future catalysts with multi-outcome scenario analysis and trading plans
- **Agent Portfolios**: Performance tracking for active and retired agents
- **Audit Trail**: Full LLM reasoning and tool call traces for every decision
- **Memories**: Explore the AI's long-term market perspective with "How to Profit" insights
- **Concept Cluster Map**: D3.js visualization of semantic relationships between market concepts
- **Reasoning Logs**: Research-grade audit trail with tabbed UI for LLM interactions

### Guardrails & Validation

- **Hard Tool Enforcement**: Server-side verification that required tools (`get_stock_quote`, `calculate_buy_quantity`, `calculate_sell_quantity`, `run_stock_screener`) were actually called
- **Reasoning Rigor (5 Whys)**: Forced recursive causal analysis across all reasoning agents (Manager, Cause & Effect, Analysis) to identify root drivers and profit mechanisms
- **Catalyst Logic Synchronization**: Strict filtering of vague "future catalysts" (no themes/broad years) to prevent Horizon Watch dashboard pollution
- **Pre-Market Validation**: FMP-verified market hours, symbol existence, 5.0% limit order price deviation check, liquidity checks
- **Reg T Margin Validation**: Buying power checks with 10% of Total Equity minimum (absolute floor of $1,000 for BUY orders)
- **Ownership Pre-Validation**: SELL signals for unheld tickers are rejected before execution
- **Semantic Redundancy**: Overtrading prevention via pgvector deduplication

## 🗺️ Roadmap

A living document of features and improvements in progress or planned for the platform.

### 🎯 Active Development

- [ ] **LLM Ranking Tool** - Build a screening system to evaluate and rank LLMs based on trading performance, reasoning quality, and consistency
- [ ] **Money Flow Model** - Make a model (based on financial papers) to track money flows.
- [ ] **Investment Chat Gateway** - Gated "Should I invest in this stock?" chat interface connecting users with LLM agents and their memories (e.g., research NVO). Requires backend infrastructure with potential home server deployment
- [ ] **Code Hotspot Finder** - Automated tool to identify code areas needing refactoring or optimization
- [ ] **Finance Papers RAG** - Add academic finance papers to memory system using Retrieval-Augmented Generation
- [ ] **Statistical Predictions** - Implement Monte Carlo simulations, Random Forest, and other ML-based prediction models
- [ ] **Whole market earnings estimates** - Add whole market earnings estimates to the system. Compare with historical if possible.
- [ ] **Review lessons learned and the learning loop** -
- [ ] **Revisit the concepts map** -
- [ ] **Add statistics** - Check current price changes in big indexes to gauge market moves today. And other indicators like stdev etc. if the market has moved 1% up today. Why? Is that normal?
  - Pass the price of many indexes to the LLM from the beginning (Add them to price update step) (This is part of the global macro tracker)
- [ ] **Canary deployment** - Make sure you can roll out to X% of users or get a staging env.
- [ ] **Posthog** - Make sure it's working - I need to add a reverse proxy.
- [ ] **Larn why it hallucinates numbers so much And how to fix.** - Maybe some kind of calculation forward tool. Like, give the price up front and ask it "is this a good number to buy", rather than asking it to come up with the number itself.
- [ ] **A proactive codebase checker and task maker connected to Posthog?** - An agent that's a user that gives feedback and proposes improvements running 24/7
- [ ] **More context on what lead to certain memory**
- [ ] **Best way to simulate a QA department**
- [ ] **Roll out/deploy a branch to prod. But not master? Like % deployment?**
- [x] **Set up Test driven development** - First feature (AgentInsights LLM label) built with TDD (see `AgentInsights.test.tsx`)
- [ ] **Find trading papers not just investing** - But low sell high?
- [ ] **Fix asset discovery.** Go step by step, dedicated agent maybe
- [ ] **Make sure CI/CD tests behave same as local tests**
- [ ] **Use frontend skills to improve frontend**
- [ ] **Sector leaderboard**
- [ ] **A famous financial anomaly is that the stock market mostly goes up when it’s closed:** -goes along with papers
- [ ] **Re-check asset discovery**
- [ ] **A programming buddy?**
  - Clippy (I already have something similar ) but that suggests improvements to the app. Just brainstorming the concept
- [x] **I don't see percentages in scenarios anymore**
- [ ] **Fix investable assets title as well..and make sure you highlight which investable assets belong to each scenario.**
- [ ] **An "AI" debate or consensus on different ways to invest in different events?**
- [ ] **Improve investable assets again?**
- [ ] **Post trade analysis re-visit.** And add the model that made it. And more details of memory. Make it so it's easy to use as learning.
- [ ] **Add "learning from failures" to what I'm feeling right now.**
- [ ] **Add 5 Whys in some flow, not sure if we already have it somewhere. I want a "root cause method". MECE?**
- [ ] **Audit that alpaca is working as intended**
- [ ] **Recheck calendar events**
- [ ] **Also check alternative plays function**
- [ ] **Vertical vs horizontal codebase for LLMs**?
- [ ] **Setup local agent managing dashboard? Split screens and stuff in vim or terminals**
- [ ] **When building something, ask for three ways this could work. Also, when brainstorming and building something, ask for the next ten things on how this could be made or the next five things after the first question.**
- [ ] **Kaparthy method would improve my rag?**
- [ ] **I like the chatgpt setup of "ask the next best question" like**. Show me a couple of options of what the next best thing to ask would be
- [ ] **Make sure we save the historical correlation/returns table/matrix**
- [ ] **Include extra sources of "true" not subjective data? Satellite images, weather, etc... research what's usually used for this.**
- [ ] **Company earnings not really (that's a different point) but a way of predicting the earnings?**
- [ ] **A tracker of your chats with LLMs to track productivity. Enterprise Software?** Openrouter might already have this.
- [ ] **In my comparision chart, the dotted line had some weird vertical lines that shouldn't be there**
- [ ] **Add design system code vertical.**
  - [ ] The design system must work nicely with the "select this and tell me more LLM chat". I could easily let people use their own open router keys and models and store it on localStorage.
- [ ] **Some kind of small/mid-cap ETF, but that doesn't remove the companies that grow. Custom, probably.**
- [ ] **Add past market events and their resolution? Like the resolution of the market events you showed before**
- [ ] **Set up a 'global' agent hook/env for my projects?**
- [ ] A live suggestion maker in chat? - recording like granola but that suggests questions or finds werid things live and shows it as some kind of popup dialogue. - What I'm envisioning is chat suggestions for what best ask next like chatgpt does. <- Might have been for pocket. But could be used for LLM chat once I have that too. - Maybe add a button that adds suggestion.
- [ ] **LLM chat, but for everywhere? Like click on a memory card and load that into context and start the chat then and there.** Allow it to make database fetches/etc...
- [ ] **Supabase push/migrate programmatically?** - Make sure your migration files match what you have and that you can migrate programmatically without breaking everything.
- [ ] **add metrics** add CAPE, PE, forward PE Etc.... ? Do I already have them? P/free cash flow
- [ ] manage prompt size with increasing memory/lessons learned database.
- [x] add agent that did the original trade to post-analysis card.

### 🔄 Under Consideration

- **Market-Closed Activities** - Define valuable tasks for agents when markets are closed (research, backtesting, memory consolidation)

---

## 📄 Documentation

### Core Documentation

- [System Overview](./docs/Overview.md)
- [Database Schema](./docs/database-schema.md)
- [Type Generation from Supabase](./supabase/TYPE_GENERATION.md)
- [Data Flow & Pipeline Walkthrough](./docs/engine/data-flow.md)
- [Decision Attribution Strategy](./docs/engine/decision-attribution-walkthrough.md)
- [Trade Settlement Walkthrough](./docs/engine/trade-settlement-walkthrough.md)
- [Portfolio Management Walkthrough](./docs/engine/portfolio-management-walkthrough.md)
- [Tool Enforcement System](./docs/engine/TOOL_ENFORCEMENT.md)
- [Lessons Learned](./docs/lessons-learned.md)

### Web Documentation

- [Web Application Architecture](./docs/web/README.md)
- [TanStack Best Practices Guide](./docs/web/TANSTACK_BEST_PRACTICES.md)
- [Portfolios UI](./docs/web/portfolios-ui.md)
- [Frontend Testing](./docs/web/testing.md)
- [Deployment Guide](./docs/web/tanstack-start-deploy-official.md)

### Integration Guides

- [IBKR Proxy & Integration Guide](./docs/IBKR-Integration.md)
- [FMP API Documentation](./docs/library-docs/FMP/FMP-API-Documentation.md)
- [Authentication Walkthrough](./docs/engine/auth-walkthrough.md)

### Utilities & Maintenance

- **Reset State**: `python apps/engine/reset_state.py`
- **Clear Database**: `python apps/engine/clear_db.py`
- **Economic Calendar**: `python apps/engine/main.py calendar`
- **Schema Docs**: `python apps/engine/generate_schema_docs.py`
- **Cleanup Catalysts**: `python apps/engine/cleanup_catalysts.py`

## 🏛️ Technology Stack

### Backend (Engine)

- **Language**: Python 3.10+
- **LLM Providers**: OpenAI, Anthropic, Google Gemini, DeepSeek
- **Database**: Supabase Postgres with pgvector
- **Market Data**: IBKR Proxy, FMP, YFinance
- **Embeddings**: Google Gemini (gemini-embedding-001)

### Frontend (Web)

- **Framework**: TanStack Start (Vite + React)
- **State Management**: TanStack Query v5
- **Visualization**: D3.js
- **Authentication**: Supabase Auth (OAuth 2.0 - Google)
- **Deployment**: Netlify (Serverless)

### DevOps

- **CI/CD**: GitHub Actions
- **Monitoring**: Sentry (error tracking), PostHog (analytics)
- **Testing**: pytest (engine), Vitest + React Testing Library (web)

## 📈 Live Dashboard

Visit [benchify.netlify.app](https://benchify.netlify.app) to explore:

- Real-time agent portfolios and performance
- Daily trade executions with full reasoning traces
- AI consensus on global market events
- Horizon Watch: upcoming catalysts and trading plans
- Concept Cluster Map: semantic relationships between market themes
- Historical memories and cause & effect analysis

## 🤝 Contributing

This is a research and benchmarking platform. Key areas for contribution:

- New LLM provider integrations
- Enhanced guardrails and validation logic
- Dashboard visualizations and UX improvements
- Memory and RAG retrieval optimizations

## 📄 License

See LICENSE file for details.
