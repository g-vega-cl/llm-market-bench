---
tags: [tool, data-source, insider-trading, sec, form-4]
category: entity
---

# Insider Trades

A corporate insider transaction tracker that ingests, normalizes, and caches SEC Form 4 filings from Financial Modeling Prep (FMP) into the Supabase `insider_trades` table and exposes them to LLM reasoning agents via the `get_insider_trades` pull tool.

This lets trading agents fold the buying and selling activity of C-suite executives (CEOs, CFOs), directors, and 10%+ beneficial owners into pre-market analysis and position sizing.

## Architecture

1. **Ingestion** — `apps/engine/tools/insider_tools.py` fetches from FMP's `/stable/insider-trading/search` and `/stable/insider-trading/statistics` endpoints. Raw JSON is normalized via `normalize_fmp_insider_trade()` into a consistent schema (`symbol`, `filing_date`, `transaction_date`, `reporting_name`, `type_of_owner`, `transaction_type`, `securities_transacted`, `price`, `total_value`, `securities_owned`, `source_url`).
2. **Persistence** — Normalized records are upserted into the `public.insider_trades` Supabase table with a composite unique constraint on `(symbol, reporting_name, transaction_date, filing_date, transaction_type, securities_transacted, price)` to deduplicate filings.
3. **Query** — Agents call the `get_insider_trades` tool (registered in `CANONICAL_TOOLS_REGISTRY` and `packages/config/tools.json`). The handler queries the database first; when empty, it fetches live from FMP and caches the results in Supabase.
4. **Dispatch** — The tool is wired into `TOOL_DISPATCH_TABLE` and marked ticker-required in `TICKER_REQUIRED_TOOLS`; `execute_get_insider_trades_tool` delegates to `handle_get_insider_trades` in `tools/compliance.py`.

## Database Schema

```sql
CREATE TABLE public.insider_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    filing_date DATE NOT NULL,
    transaction_date DATE NOT NULL,
    reporting_name TEXT NOT NULL,
    type_of_owner TEXT,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('purchase', 'sale', 'other')),
    securities_transacted NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    price NUMERIC(14, 4) NOT NULL DEFAULT 0.0000,
    total_value NUMERIC(16, 2) NOT NULL DEFAULT 0.00,
    securities_owned NUMERIC(16, 2),
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_insider_trade UNIQUE (
        symbol, reporting_name, transaction_date, filing_date, transaction_type, securities_transacted, price
    )
);
```

RLS allows public `SELECT` and full access only to `service_role`. Indexed on `symbol`, `filing_date DESC`, and `transaction_date DESC`.

## Tool Signature

The `get_insider_trades` tool accepts:

- `ticker` (required) — stock symbol (e.g. `NVDA`, `AAPL`).
- `days` (optional, default `90`) — lookback window in calendar days.
- `transaction_type` (optional, default `"all"`, choices `all`/`purchase`/`sale`).
- `limit` (optional, default `15`) — maximum records returned.

It returns a Markdown table with total bought/sold volume, a sentiment classification (Bullish Net Buying / Bearish Net Selling / Neutral), quarterly benchmark statistics, and individual transaction rows.

## Related

- [[entities/congress-trades]] — US lawmaker STOCK Act disclosure tracker
- [[entities/whale-holdings]] — Institutional 13F and Schedule 13D/13G whale tracker
- [[concepts/tool-first-agency]] — the architectural principle behind pull tools
- [[entities/engine]] — the execution engine housing this tool
- [[entities/database]] — Supabase schema and migration conventions
