---
tags: [government, ingestion, treasury, tga, contracts, procurement, whales, sec-13d, 13g, liquidity, catalysts]
category: entity
---

# Government Ingestion Pipeline

The government ingestion subsystem (`apps/engine/ingest/government.py`, `apps/engine/ingest/government_fetchers.py`, `apps/engine/ingest/whale_fetchers.py`, `apps/engine/ingest/congress_fetchers.py`, and `apps/engine/ingest/insider_fetchers.py`) pulls official government balance-sheet operations, fiscal deficits, procurement awards, institutional blockholder disclosures, Congress STOCK Act filings, and corporate/Canadian insider trading into PostgreSQL. It runs outside the daily newsletter/consensus loop and feeds both the [[concepts/catalyst-radar]] and downstream analysis agents with hard fiscal, political, and insider ownership data.

## Pipeline Stages

`GovernmentPipeline.run()` executes six independent stages in order. Each stage is wrapped in its own `try/except` that logs a warning and continues, so a single upstream outage never aborts the run:

1. **`ingest_liquidity(days=14)`** — US Treasury General Account cash, national debt, and monthly deficit (`gov_macro_liquidity`).
2. **`ingest_contracts(limit=50)`** — US federal contract awards plus Canadian federal contracts (`gov_contracts`).
3. **`ingest_whales(symbols=None)`** — SEC Schedule 13D/13G beneficial ownership disclosures (`institutional_whale_stakes`).
4. **`ingest_congress(limit=50)`** — US Senate and House personal transaction disclosures (`congress_trades`).
5. **`ingest_insiders(limit=50)`** — Market-wide SEC Form 4 filings and active universe corporate & Canadian insider activity (`insider_trades`).
6. **`extract_policy_memories()`** — LLM extraction of policy/incentive catalysts into `GOVERNMENT_INCENTIVE` memories.

`run()` returns the number of policy memories created. The module-level entry point `run_government_pipeline()` returns a summary dict `{"status": "success", "memories_created": N}` for CLI and scheduled workflow callers.

Both `get_gemini_client()` and `get_supabase_client()` are constructed defensively in `__init__` — a missing credential leaves the attribute `None` rather than raising, and `extract_policy_memories()` short-circuits to `0` when no Gemini client is available.

## Treasury Liquidity & Debt (`fetch_us_treasury_liquidity`)

Queries `api.fiscaldata.treasury.gov` with a browser user agent and a 15s timeout, merging three endpoints into one record per `record_date`:

| Source endpoint | Fields captured |
| :--- | :--- |
| `/v1/accounting/dts/operating_cash_balance` | `tga_balance` (scaled from millions to exact dollars), plus `tga_deposits` and `tga_withdrawals` in `raw_metadata` |
| `/v2/accounting/od/debt_to_penny` | `tot_pub_debt`, `debt_held_public`, `intragov_holdings` |
| `/v1/accounting/mts/mts_table_1` | `monthly_deficit_surplus` (latest reported monthly deficit/surplus) and `fytd_deficit_surplus`, `fytd_receipts`, `fytd_outlays` in `raw_metadata` |

Records are keyed by `record_date`, defaulted to `None` for any metric the upstream did not return, sorted newest-first, and upserted into `gov_macro_liquidity` on `record_date`.

## Agent Tools for Sovereign & Corporate Spending

Trading agents access government fiscal data, international sovereign budgets, contract deals, and corporate capital allocation through two pull-based tools:

1. **`get_government_fiscal_and_spending` (`apps/engine/tools/government_tools.py`)**:
   - **US Money Creation, TGA Liquidity & Debt**: Queries `gov_macro_liquidity`, FRED (`M2SL`, `WALCL`, `RRPONTSYD`), and Treasury Average Interest Rates (`/v2/accounting/od/avg_interest_rates`). Computes the 14-day TGA drawdown/refill liquidity impulse and 14-day net debt issuance delta.
   - **US Federal Budget Priorities**: Fetches Monthly Treasury Statement Table 9 (`/v1/accounting/mts/mts_table_9`) for FYTD and monthly outlays across Social Security, Medicare, Net Interest, Health, National Defense, Income Security, Veterans, Science/Space/Tech, Energy, and Transportation, alongside USAspending top-tier agency budget authorities (`/api/v2/references/toptier_agencies/`).
   - **Canadian Federal Budget by Ministry**: Fetches Public Accounts of Canada budgetary authorities (`budgetaires-budgetary.csv`) to rank ministry expenditures and YoY growth in CAD (such as National Defence and Public Services and Procurement).
   - **Global Sovereign Defense & Infrastructure Surges**: Queries World Bank indicators (`MS.MIL.XPND.CD` and `NE.GDI.TOTL.CD`) across `USA`, `CAN`, `GBR`, `DEU`, `FRA`, `JPN`, `CHN`, and `IND` for YoY defense and gross capital formation growth, paired with Eurostat (`gov_10dd_edpt1`) sovereign fiscal deficits (`B9`) and gross debt (`GD`) as a percentage of GDP for the Euro Area (`EA20`), Germany (`DE`), France (`FR`), and Italy (`IT`).
   - **Federal Contract Deals**: Queries `gov_contracts` and live `fetch_usaspending_contracts` / `fetch_canadabuys_contracts`, supporting company-level contract lookups via `ticker` or `recipient`.
2. **`get_corporate_spending` (`apps/engine/tools/corporate_spending_tools.py`)**:
   - Combines FMP `/stable/cash-flow-statement`, `/stable/income-statement`, `/stable/key-metrics`, and `/stable/mergers-acquisitions-latest` with federal contract awards to audit single-ticker or hyperscaler basket (`MSFT`, `AMZN`, `GOOGL`, `META`, `NVDA`) CapEx, CapEx YoY growth, CapEx/Revenue, CapEx/OCF, R&D intensity, SG&A, share buybacks, dividends, M&A cash spend, Free Cash Flow, and ROIC.

## Federal Contracts (US & Canada)

### USAspending (`fetch_usaspending_contracts`)

POSTs to `api.usaspending.gov/api/v2/search/spending_by_award/` with a `time_period` window (default 14 days) and `award_type_codes` `A`–`D`. Each award is normalized to `country="US"`, `award_id`, `recipient_name`, `award_amount`, `currency="USD"`, `description`, `agency_name`, `award_date`, `contract_number`, and a `source_url` pointing at `usaspending.gov/award/<generated_internal_id>`. Awards missing an ID or recipient are dropped.

### CanadaBuys (`fetch_canadabuys_contracts` / `parse_canadabuys_csv`)

Downloads the Open Government contract-history CSV from `canadabuys.canada.ca` (redirects followed) and parses it with `csv.DictReader`. Bilingual column names are resolved with fallbacks:

- Contract number — `contractNumber-numeroContrat` → `referenceNumber-numeroReference`
- Supplier — `supplierStandardizedName-nomNormaliseFournisseur` → `supplierLegalName-nomLegalFournisseur` → `supplierOperatingName-nomCommercialFournisseur`
- Value — `contractValue-valeurContrat`
- Award date — `contractAwardDate-dateAttributionContrat` → `publicationDate-datePublication` → today
- Description — `title-titre-eng` → `description-description-eng` → `title-titre-fra`
- Buyer — `buyerOrganizationName-nomOrganisationAcheteur-eng` (defaults to `Government of Canada`)

Records are emitted with `country="CA"` and `currency="CAD"`. Rows without a contract number or supplier are skipped, and parsing stops at `limit`.

Both contract sources are upserted into `gov_contracts` on the composite key `(country, award_id, recipient_name, award_date)`.

## Institutional Whale Stakes (`whale_fetchers.py`)

Tracks activist blockholder entries (Schedule 13D), major institutional positions (Schedule 13G), and complete liquidations.

- **`fetch_beneficial_ownership(symbol)`** — calls FMP `/stable/acquisition-of-beneficial-ownership` with `FMP_API_KEY`. Returns `[]` (with a warning) when the key is missing or the response is non-200.
- **`filter_whale_stakes(raw_filings, min_percent=4.0, max_records=50)`** — keeps filings whose `percentOfClass` is at or above `min_percent`, plus any filing with `percentOfClass == 0` or `amountBeneficiallyOwned == 0` (flagged `is_exit=True`). `filing_type` is derived from the SEC document URL (`13D` when the URL contains `13D`, otherwise `13G`).
- **`upsert_institutional_whale_stakes(records)`** — upserts into `institutional_whale_stakes` on `(symbol, filer_name, filing_date, percent_of_class)`.
- **`ingest_institutional_whales(symbols=None, min_percent=4.0)`** — iterates the watchlist (default `DEFAULT_WHALE_UNIVERSE`: `NVDA`, `AAPL`, `MSFT`, `PLTR`, `AMZN`, `GOOGL`, `META`, `TSLA`, `AMD`, `AVGO`, `LMT`, `BA`, `RTX`, `SHOP`, `ENB`, `CCJ`, `TECK`), fetching and filtering each symbol sequentially, and returns `{"symbols_processed": N, "stakes_upserted": M}`.

## Policy Catalyst Memories (`extract_policy_memories`)

Assembles real-world source context via `fetch_policy_grounding_context()` from:
- `fetch_federal_register_documents()` in `apps/engine/ingest/federal_register.py` (`https://www.federalregister.gov/api/v1/documents.json` significant rules/notices)
- Latest balanced US and Canadian procurement awards (`gov_contracts`, 30-day window), US Treasury liquidity (`gov_macro_liquidity`, 30-day window), and recent market newsletter summaries (`generated_newsletters`, 14-day window) in Supabase.

If no grounding context is retrieved, `extract_policy_memories()` skips the LLM call and returns `0`. Otherwise, it prompts Gemini (`GEMINI_MODEL`) with a `DecisionsResponse` schema to synthesize verified US and Canadian budgets, rules, and incentives grounded strictly in that source payload. Each returned macro event is persisted via `add_memory()` as a `GOVERNMENT_INCENTIVE` memory containing the event name, reasoning, impact, and expiry date, feeding the [[concepts/catalyst-radar]].

## Congress Disclosures (`congress_fetchers.py`)

Ingests recent STOCK Act personal stock transactions for the US Senate and House of Representatives.

- **`fetch_latest_congress_trades(limit=50)`** — queries FMP `/stable/senate-latest` and `/stable/house-latest`, normalizing representative names, ticker symbols, transaction types (`purchase`/`sale`/`exchange`), and estimated dollar value midpoints.
- **`upsert_congress_trades(records)`** — deduplicates on `(chamber, representative_name, symbol, transaction_date, transaction_type, amount_range)` and upserts into `public.congress_trades`.

## Corporate & Canadian Insider Activity (`insider_fetchers.py`)

Ingests corporate executive and director transactions, focusing on high-conviction Form 4 filings and Canadian cross-listed equities.

- **`fetch_latest_insider_trades(limit=100)`** — pulls market-wide filings from FMP `/stable/insider-trading/latest`.
- **`fetch_universe_insider_trades(symbols=None, limit_per_symbol=25)`** — concurrent asynchronous scanner for core mega-caps and Canadian bellwethers (`SHOP`, `SU`, `ENB`, `RY`, `TD`, `CNR`, `CP`, `BMO`, `BNS`, `MFC`, `BCE`, `WCN`, `OTEX`, `NTR`, `FNV`, `AGI`).
- **`upsert_insider_trades(records)`** — deduplicates on `(symbol, reporting_name, transaction_date, filing_date, transaction_type, securities_transacted, price)` and upserts into `public.insider_trades`.

## Database Tables

| Table | Purpose | Unique key |
| :--- | :--- | :--- |
| `gov_macro_liquidity` | Daily TGA cash, total public debt, debt held by the public, intragovernmental holdings, monthly deficit/surplus | `record_date` |
| `gov_contracts` | US and Canadian federal contract awards with amounts, agencies, and source URLs | `(country, award_id, recipient_name, award_date)` |
| `institutional_whale_stakes` | Schedule 13D/13G filer stakes, percentages, share counts, and exit flags | `(symbol, filer_name, filing_date, percent_of_class)` |
| `congress_trades` | US Senate and House personal transaction disclosures | `(chamber, representative_name, symbol, transaction_date, transaction_type, amount_range)` |
| `insider_trades` | SEC Form 4 insider transactions for corporate officers, directors, and 10%+ owners | `(symbol, reporting_name, transaction_date, filing_date, transaction_type, securities_transacted, price)` |

All five tables enable RLS with public `SELECT` and `service_role` full access. The fiscal/contract/whale trio is created by migrations `20261106180000_create_gov_macro_and_contracts.sql` and `20261106190000_create_institutional_whale_stakes.sql` (mirrored in `docker/archive/init.sql`); `congress_trades` and `insider_trades` are populated by the Congress and insider stages of this pipeline. See [[entities/database]].

## Resilience & Parsing Helpers

- `_safe_float(val, default=0.0)` strips `$`, `%`, and thousands separators and coerces `None`, `""`, and `"null"` to the default — used by both fetcher modules so malformed upstream values never raise.
- Every network call is individually wrapped; failures log a warning and return an empty list, so partial ingestion still persists whatever succeeded.
- Upsert helpers return the number of rows written (falling back to `len(records)` when the client returns no `data`), and log via `logger.error` on database failure.

## Tests

- `apps/engine/tests/test_government_ingest.py` — `_safe_float` coercion, DTS/debt/MTS merge, USAspending parsing, CanadaBuys CSV parsing and network-failure handling, both upsert helpers, and end-to-end `GovernmentPipeline.run()` / `run_government_pipeline()` orchestration.
- `apps/engine/tests/test_government_and_corporate_spending_tools.py` — hermetic unit tests for `execute_get_government_fiscal_and_spending_tool`, `execute_get_corporate_spending_tool` (single-ticker and hyperscaler basket), inner sovereign budget fetchers, and `get_key_metrics` reinvestment ratios.
- `apps/engine/tests/test_institutional_whales.py` — float parsing, `filter_whale_stakes` accumulation/exit/activist classification, FMP fetch success and missing-key paths, stake upserts, `ingest_institutional_whales` flow, and confirmation that `GovernmentPipeline.run()` invokes whale ingestion.
- `apps/engine/tests/test_congress_insider_ingest.py` — hermetic coverage of `fetch_latest_congress_trades` (both chambers, normalized fields, positive `amount_est_midpoint`), `upsert_congress_trades`, `fetch_latest_insider_trades`, `fetch_universe_insider_trades`, `upsert_insider_trades`, and a full `GovernmentPipeline.run()` orchestration test asserting all six stages fire.

All suites are fully hermetic (mocked `httpx.AsyncClient` and Supabase clients) per [[concepts/test-coverage]].

## Related

- [[concepts/ingestion]] — the broader ingestion phase this pipeline belongs to
- [[concepts/catalyst-radar]] — consumes the policy and contract catalysts
- [[entities/database]] — table definitions, RLS, and migrations
- [[entities/congress-trades]] — sibling STOCK Act disclosure ingestion
- [[entities/insider-trades]] — corporate and Canadian insider transaction ingestion
- [[entities/engine]] — the Python data engine hosting this pipeline
- [[entities/pipeline]] — the daily pipeline lifecycle
