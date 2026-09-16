---
tags: [tool, pipeline, data-source, congress, stock-act]
category: entity
---

# Congress Trades

A live STOCK Act disclosure ingestion and query system that pulls US Senate and House personal financial transaction filings from Financial Modeling Prep (FMP), normalizes them into a structured Supabase table (`congress_trades`), and exposes them to LLM agents via the `get_congress_trades` pull tool.

This enables trading agents to incorporate the investing behavior of US lawmakers, including transaction type, amount ranges, and filing dates, as a peripheral signal during portfolio construction and rebalancing.

## Architecture

The pipeline has three layers:

1. **Ingestion**: `apps/engine/tools/congress_tools.py` fetches from FMP's `/stable/senate-trades`, `/stable/senate-latest`, `/stable/house-trades`, `/stable/house-latest` endpoints. Raw JSON is normalized via `normalize_fmp_congress_trade()` into a consistent schema (`chamber`, `symbol`, `transaction_date`, `disclosure_date`, `representative_name`, `transaction_type`, `amount_range`, `amount_est_midpoint`, etc.).

2. **Persistence**: Normalized records are upserted to the `public.congress_trades` table in Supabase with a composite unique constraint on `(chamber, representative_name, symbol, transaction_date, transaction_type, amount_range)` to prevent duplicates.

3. **Query**: Agents call the `get_congress_trades` tool (registered in `CANONICAL_TOOLS_REGISTRY` and `packages/config/tools.json`). The handler first tries the database; if empty, it falls back to a live FMP fetch and persists the results as a side effect.

## Database Schema

```sql
CREATE TABLE public.congress_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chamber TEXT NOT NULL CHECK (chamber IN ('senate', 'house')),
    symbol TEXT NOT NULL,
    transaction_date DATE NOT NULL,
    disclosure_date DATE NOT NULL,
    representative_name TEXT NOT NULL,
    district TEXT,
    owner TEXT,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('purchase', 'sale', 'exchange')),
    amount_range TEXT NOT NULL,
    amount_est_midpoint NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    asset_description TEXT,
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_congress_trade UNIQUE (
        chamber, representative_name, symbol, transaction_date, transaction_type, amount_range
    )
);
```

RLS policies allow public `SELECT`, and full access only to `service_role`.

## Tool Signature

The tool accepts optional filters: `ticker` (symbol), `chamber` (senate/house), `days` (lookback window, default 45), `transaction_type` (purchase/sale), and `limit` (max records, default 20). It returns a formatted Markdown table with estimated total bought/sold volume at the top.

## Pipeline Script

`apps/engine/scripts/update_congress_trades.py` provides a CLI entrypoint for ad-hoc or cron-driven batch updates. It fetches both Senate and House disclosures for all (or a specific) symbols and upserts them.

## Related

- [[entities/engine]]: the overarching engine that houses this tool
- [[concepts/tool-first-agency]]: the architectural principle behind pull tools
- [[entities/database]]: the Supabase schema that stores disclosures
