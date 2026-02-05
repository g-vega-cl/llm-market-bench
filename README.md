# AI Wall Street: LLM Market Benchmarking Platform

An automated platform where four LLMs (**OpenAI, Claude, Gemini, DeepSeek**) compete in a virtual stock market. Every morning, they parse financial newsletters, debate major global events, and rebalance their portfolios.

## 🚀 Project Overview

This project benchmarks the reasoning capabilities of leading LLMs against the real-world performance of the S&P 500. It features a robust Python-based data engine and a modern React-based frontend.

For a deep dive into the system design, see the **[Project Overview](./docs/Overview.md)**.

## 📂 Repository Structure

This is a monorepo managed with `pnpm`:

*   **`apps/engine`**: The Python pipeline (Ingestion, Analysis, Execution).
*   **`apps/web`**: The TanStack Start dashboard (Frontend). [Read the Web Architecture Docs](./docs/web/README.md).
*   **`supabase`**: SQL migrations and database configuration.
*   **`docs`**: Technical documentation and walkthroughs.

## 🛠️ Getting Started

### Prerequisites
*   Python 3.10+
*   Node.js 20+ & `pnpm`
*   Supabase Account

### Workspace Setup
```bash
pnpm install
``

### Engine Execution
The engine handles the daily pipeline:
```bash
cd apps/engine
source market/bin/activate
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
cd apps/engine
python3 -m pytest
```

## ⚙️ Automation

*   **CI Testing**: Automatically runs on every push to `main`.
*   **Daily Pipeline**: Triggered via GitHub Actions at 09:35 ET (5 minutes after market open).

## 📄 Documentation

*   [System Overview](./docs/Overview.md)
*   [Data Flow & Pipeline Walkthrough](./docs/data-flow.md)
*   [Web Application Architecture](./docs/web/README.mdld)
*   [Decision Attribution Strategy](./docs/engine/decision-attribution-walkthrough.md)