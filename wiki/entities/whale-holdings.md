---
tags: [tool, data-source, institutional-holdings, whales, 13f, 13d, 13g]
category: entity
---

# Whale Holdings

An institutional smart-money and whale holding tracker that retrieves Schedule 13D/13G beneficial ownership blockholders (>5% owners) and Form 13F fund portfolio holdings, exposing them to LLM agents via the `get_whale_holdings` pull tool.

This lets portfolio agents evaluate institutional sponsorship, hedge-fund concentration, and blockholder positioning.

## Architecture

1. **Beneficial Ownership (13D/13G)** — `apps/engine/tools/whale_tools.py` fetches from FMP's `/stable/acquisition-of-beneficial-ownership` endpoint and identifies >5% institutional blockholders (e.g. Vanguard, BlackRock, Berkshire Hathaway, activist investors) for any US stock ticker. `format_beneficial_ownership_markdown()` renders a deduplicated Markdown table of filers, ownership type, percent of class, and shares.
2. **Form 13F Fund Portfolios** — `get_fund_holdings()` from `apps/engine/analysis/sec_13f_client.py` retrieves 13F filings for funds in `DEFAULT_THEMATIC_FUNDS` (e.g. `BERKSHIRE_HATHAWAY`, `COATUE`, `APPALOOSA`, `WHALE_ROCK`, `DUQUESNE`). `format_fund_holdings_markdown()` ranks positions by value with portfolio weight.
3. **Query** — Agents call the `get_whale_holdings` tool (registered in `CANONICAL_TOOLS_REGISTRY` and `packages/config/tools.json`). Ticker and fund lookups can be combined in one call; fund names support partial matching against the curated list.

## Tool Signature

The `get_whale_holdings` tool accepts:

- `ticker` (optional) — stock symbol (e.g. `NVDA`) to view major institutional blockholders and percent of class owned.
- `fund_name` (optional) — curated whale fund name to inspect Form 13F portfolio holdings.
- `limit` (optional, default `15`) — maximum filers/holdings returned.

At least one of `ticker` or `fund_name` must be supplied.

## Related

- [[entities/sec-13f-client]] — SEC EDGAR 13F parser and client
- [[entities/insider-trades]] — corporate officer Form 4 insider trading tracker
- [[entities/congress-trades]] — US lawmaker STOCK Act disclosure tracker
- [[entities/thematic-beneficiaries]] — thematic co-ownership clustering
- [[concepts/tool-first-agency]] — architectural principle for agent tools
