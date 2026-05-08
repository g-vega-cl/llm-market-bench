# AI Wall Street: LLM Market Benchmarking Platform

An automated platform where multiple LLMs compete in a virtual stock market. Multiple times daily during US market hours, they parse financial newsletters, debate major global events, analyze government incentives, and rebalance their portfolios.

## Project Overview

Benchmarks LLM reasoning against S&P 500 performance. Python data engine + React frontend.

### Why It Matters

- **Performance Benchmarking:** Real-world test of LLM reasoning vs. S&P 500.
- **The "Consensus" Effect:** Identifies where AI models agree or diverge on global risks.
- **Research Audit Trail:** Provides a full "Thinking Process" trace for every LLM call, including intermediate tool steps, for behavioral research.
- **Decision Attribution:** Provides a machine-auditable trail from raw news chunk to final trade execution.
- **Memory Integrity:** Tests if LLMs can maintain a consistent world view using Vector RAG (Retrieval-Augmented Generation).

For a deep dive into the system design, see the **[Project Overview](./docs/Overview.md)** and the **[Database Schema](./docs/database-schema.md)**.

## Repository Structure

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
│   ├── config/              # Shared configuration (models.json)
│   ├── database/            # Generated Supabase types
│   └── ui-design-system/    # Shared UI primitives + theme tokens
└── tests/                   # Engine & Web tests
```

- **`apps/engine`**: The Python data engine.
- **`apps/web`**: The TanStack Start dashboard. [Read the Web Architecture Docs](./docs/web/README.md).
- **`supabase`**: SQL migrations and database configuration.
- **`docs`**: Technical documentation and walkthroughs.

## Getting Started

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

## Testing

```bash
./apps/engine/venv/bin/python3 -m pytest
```

## Automation

- **CI Testing**: Runs on every push to `main`. See `.github/workflows/ci.yml`.
- **Daily Pipeline**: Cron-triggered during US market hours, with a holiday-aware market-hours check. Schedule: `.github/workflows/ingest.yml`.
- **Price Updates**: Periodic during market hours. Schedule: `.github/workflows/update-prices.yml`.

## Key Features

### The Daily Pipeline (6 Phases)

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
- **Pre-Market Validation**: FMP-verified market hours, symbol existence, price-deviation banding, liquidity floor
- **Reg T Margin Validation**: Buying power and minimum-trade-value checks (constants in `apps/engine/core/config.py`)
- **Ownership Pre-Validation**: SELL signals for unheld tickers are rejected before execution
- **Semantic Redundancy**: Overtrading prevention via pgvector deduplication

See [ROADMAP.md](./ROADMAP.md) for planned features and improvements.

## Documentation

> **Persistent Wiki**: Synthesized knowledge, entity/concept maps, and source summaries are maintained in the `wiki/` directory (LLM-written, human-curated). See [AGENTS.md](AGENTS.md) for search and ingest workflows.

### Core Documentation

- [System Overview](./docs/Overview.md)
- [Database Schema](./docs/database-schema.md)
- [Type Generation from Supabase](./supabase/TYPE_GENERATION.md)
- [Data Flow & Pipeline Walkthrough](./docs/engine/data-flow.md)
- [Tool Enforcement System](./docs/engine/TOOL_ENFORCEMENT.md)
- [Market Heuristics](./docs/engine/market-heuristics.md)

### Web Documentation

- [Web Application Architecture](./docs/web/README.md)
- [Design System](./docs/web/DESIGN_SYSTEM.md) — Typography, colors, and component patterns
- [TanStack Best Practices Guide](./docs/web/TANSTACK_BEST_PRACTICES.md)
- [Portfolios UI](./docs/web/portfolios-ui.md)
- [Frontend Testing](./docs/web/testing.md)
- [Deployment Guide](./docs/web/tanstack-start-deploy-official.md)

### Utilities & Maintenance

- **Reset State**: `python apps/engine/reset_state.py`
- **Clear Database**: `python apps/engine/clear_db.py`
- **Economic Calendar**: `python apps/engine/main.py calendar`
- **Schema Docs**: `python apps/engine/generate_schema_docs.py`
- **Cleanup Catalysts**: `python apps/engine/cleanup_catalysts.py`

## Technology Stack

### Backend (Engine)

- **Language**: Python 3.10+
- **LLM Providers**: OpenAI, Anthropic, Google Gemini, DeepSeek
- **Database**: Supabase Postgres with pgvector
- **Market Data**: IBKR Proxy, FMP, YFinance
- **Embeddings**: Google Gemini (gemini-embedding-001)

### Frontend (Web)

- **Framework**: TanStack Start (Vite + React)
- **Styling**: Tailwind CSS v4 + homegrown design system (`@llm-market-bench/ui-design-system`)
- **State Management**: TanStack Query v5
- **Visualization**: D3.js
- **Authentication**: Supabase Auth (OAuth 2.0 - Google)
- **Deployment**: Netlify (Serverless)

### DevOps

- **CI/CD**: GitHub Actions
- **Monitoring**: Sentry (error tracking), PostHog (analytics)
- **Testing**: pytest (engine), Vitest + React Testing Library (web)

## Live Dashboard

Visit [benchify.netlify.app](https://benchify.netlify.app) to explore:

- Real-time agent portfolios and performance
- Daily trade executions with full reasoning traces
- AI consensus on global market events
- Horizon Watch: upcoming catalysts and trading plans
- Concept Cluster Map: semantic relationships between market themes
- Historical memories and cause & effect analysis

## Contributing

This is a research and benchmarking platform. Key areas for contribution:

- New LLM provider integrations
- Enhanced guardrails and validation logic
- Dashboard visualizations and UX improvements
- Memory and RAG retrieval optimizations

## License

See LICENSE file for details.
