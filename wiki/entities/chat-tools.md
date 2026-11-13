---
tags: [chat, tools, investment-chat-gateway]
category: entity
---

# Chat Tools

Server-side tool definitions and handlers for the Investment Chat Gateway. These tools enable the conversational agent to query memories, theses, causal chains, and the live database schema.

## Tools

### search_memories_and_theses

Searches past agent market memories, lessons learned, historical parallels, causal chains (cause_and_effect), and scenario analyses by ticker or thematic query.

**Parameters:**
- `ticker` (optional): Stock ticker symbol
- `query` (optional): Thematic search string

**Returns:** Structured results with:
- `memories`: Array of memory objects, each now including a `historical_parallel` field (structured object with title, timeframe, precedent, market_reaction, takeaway, affected_assets) when the memory has an associated historical parallel stored in metadata.
- `causalRecords`: Array of cause-and-effect records.

The tool fetches memories from the `memories` table including the `metadata` column, then extracts `historical_parallel` from metadata into a top-level field for easy consumption by the LLM and UI.

### executeDatabaseQueryTool

Executes a bounded, read-only PostgREST select against a whitelisted table so the chat agent can answer questions about government fiscal data, insider/whale filings, Congress disclosures, and FRED cache rows without bespoke tools per table.

**Parameters:** `table_name` (required), `select_columns`, `filter_column`, `filter_value`, `order_by`, `ascending`, `limit`.

**Behavior:**
- **Table-aware default ordering** — when `order_by` is omitted, `DEFAULT_ORDER_BY_COLUMN` supplies a sensible timestamp column instead of a blanket `created_at`:

  | Table | Default `order_by` |
  | :--- | :--- |
  | `fred_series_cache` | `fetched_at` |
  | `portfolios` | `last_updated_at` |
  | `trades` | `executed_at` |
  | `gov_macro_liquidity` | `record_date` |
  | `gov_contracts` | `award_date` |
  | `institutional_whale_stakes` | `filing_date` |
  | `congress_trades` | `disclosure_date` |
  | `insider_trades` | `filing_date` |
  | *(any other table)* | `created_at` |

- **Vector egress stripping** — `stripVectorFields(rows)` deletes any `embedding` key from returned rows before serialization, so pgvector payloads never reach the model or the browser (see [[concepts/vector-egress-stripping]]).
- **Bounded limits** — `limit` is clamped to `1..50`.

### getDatabaseSchemaSummary

Builds the `Available Database Tables:` catalog injected into the chat system prompt. It samples `portfolios` and `trades` for live column names, then appends the shared static catalog (`SHARED_STATIC_TABLES_SUMMARY`), which covers `memories`, `cause_and_effect`, `market_feeling`, `portfolio_snapshots`, `sector_predictions`, `prompt_experiments`, `generated_newsletters`, `decisions`, `leaderboard`, plus the government/macro tables:

- `gov_macro_liquidity`: `record_date, tga_balance, tot_pub_debt, debt_held_public, intragov_holdings, monthly_deficit_surplus`
- `gov_contracts`: `country, award_id, recipient_name, award_amount, currency, agency_name, award_date, description`
- `congress_trades`: `chamber, symbol, representative_name, transaction_date, disclosure_date, transaction_type, amount_range`
- `insider_trades`: `symbol, reporting_name, filing_date, transaction_date, transaction_type, securities_transacted, total_value`
- `institutional_whale_stakes`: `symbol, filer_name, filing_date, filing_type, percent_of_class, shares_beneficially_owned, is_exit`
- `fred_series_cache`: `series_id, title, units, frequency, latest_date, latest_value, observations, fetched_at`

The summary is cached in-process for 7 days (`CACHE_TTL_MS`); `FALLBACK_SCHEMA_SUMMARY` is the static catalog used when the live sample query fails.

## Related

- [[entities/investment-chat-gateway]]
- [[concepts/memory-feedback]]
- [[concepts/vector-egress-stripping]]
- [[entities/government-ingestion]]
- [[entities/database]]
- [[entities/web-app]]
