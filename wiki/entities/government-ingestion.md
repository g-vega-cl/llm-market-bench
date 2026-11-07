---
tags: [government, ingestion, treasury, tga, contracts, procurement, whales, sec-13d, 13g, liquidity, catalysts]
category: entity
---

# Government Ingestion Pipeline

The government ingestion subsystem (`apps/engine/ingest/government.py`, `apps/engine/ingest/government_fetchers.py`, and `apps/engine/ingest/whale_fetchers.py`) pulls official government balance-sheet operations, fiscal deficits, procurement awards, and institutional blockholder disclosures into PostgreSQL. It runs outside the daily newsletter/consensus loop and feeds both the [[concepts/catalyst-radar]] and downstream analysis agents with hard fiscal and ownership data.

## Pipeline Stages

`GovernmentPipeline.run()` executes four independent stages in order. Each stage is wrapped in its own `try/except` that logs a warning and continues, so a single upstream outage never aborts the run:

1. **`ingest_liquidity(days=14)`** — US Treasury General Account cash, national debt, and monthly deficit.
2. **`ingest_contracts(limit=50)`** — US federal contract awards plus Canadian federal contracts.
3. **`ingest_whales(symbols=None)`** — SEC Schedule 13D/13G beneficial ownership disclosures.
4. **`extract_policy_memories()`** — LLM extraction of policy/incentive catalysts into `GOVERNMENT_INCENTIVE` memories.

`run()` returns the number of policy memories created. The module-level entry point `run_government_pipeline()` returns a summary dict `{"status": "success", "memories_created": N}` for CLI and scheduled workflow callers.

Both `get_gemini_client()` and `get_supabase_client()` are constructed defensively in `__init__` — a missing credential leaves the attribute `None` rather than raising, and `extract_policy_memories()` short-circuits to `0` when no Gemini client is available.

## Treasury Liquidity & Debt (`fetch_us_treasury_liquidity`)

Queries `api.fiscaldata.treasury.gov` with a browser user agent and a 15s timeout, merging three endpoints into one record per `record_date`:

| Source endpoint | Fields captured |
| :--- | :--- |
| `/v1/accounting/dts/operating_cash_balance` | `tga_balance` (Treasury General Account opening/close balance) |
| `/v2/accounting/od/debt_to_penny` | `tot_pub_debt`, `debt_held_public`, `intragov_holdings` |
| `/v1/accounting/mts/mts_table_1` | `monthly_deficit_surplus` |

Records are keyed by `record_date`, defaulted to `None` for any metric the upstream did not return, sorted newest-first, and upserted into `gov_macro_liquidity` on `record_date`.

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

Prompts Gemini (`GEMINI_MODEL`) with a `DecisionsResponse` schema to identify current and upcoming US and Canadian government budgets, objectives, and incentives that could move markets — renewable energy incentives, infrastructure and pipeline spending, tech/AI subsidies and regulation, critical minerals initiatives, and major budget expiration dates. Each returned macro event is persisted via `add_memory()` as a `GOVERNMENT_INCENTIVE` memory containing the event name, reasoning, impact, and expiry date, feeding the [[concepts/catalyst-radar]].

## Database Tables

| Table | Purpose | Unique key |
| :--- | :--- | :--- |
| `gov_macro_liquidity` | Daily TGA cash, total public debt, debt held by the public, intragovernmental holdings, monthly deficit/surplus | `record_date` |
| `gov_contracts` | US and Canadian federal contract awards with amounts, agencies, and source URLs | `(country, award_id, recipient_name, award_date)` |
| `institutional_whale_stakes` | Schedule 13D/13G filer stakes, percentages, share counts, and exit flags | `(symbol, filer_name, filing_date, percent_of_class)` |

All three tables enable RLS with public `SELECT` and `service_role` full access, and are created by migrations `20261106180000_create_gov_macro_and_contracts.sql` and `20261106190000_create_institutional_whale_stakes.sql` (mirrored in `docker/archive/init.sql`). See [[entities/database]].

## Resilience & Parsing Helpers

- `_safe_float(val, default=0.0)` strips `$`, `%`, and thousands separators and coerces `None`, `""`, and `"null"` to the default — used by both fetcher modules so malformed upstream values never raise.
- Every network call is individually wrapped; failures log a warning and return an empty list, so partial ingestion still persists whatever succeeded.
- Upsert helpers return the number of rows written (falling back to `len(records)` when the client returns no `data`), and log via `logger.error` on database failure.

## Tests

- `apps/engine/tests/test_government_ingest.py` — `_safe_float` coercion, DTS/debt/MTS merge, USAspending parsing, CanadaBuys CSV parsing and network-failure handling, both upsert helpers, and end-to-end `GovernmentPipeline.run()` / `run_government_pipeline()` orchestration.
- `apps/engine/tests/test_institutional_whales.py` — float parsing, `filter_whale_stakes` accumulation/exit/activist classification, FMP fetch success and missing-key paths, stake upserts, `ingest_institutional_whales` flow, and confirmation that `GovernmentPipeline.run()` invokes whale ingestion.

Both suites are fully hermetic (mocked `httpx.AsyncClient` and Supabase clients) per [[concepts/test-coverage]].

## Related

- [[concepts/ingestion]] — the broader ingestion phase this pipeline belongs to
- [[concepts/catalyst-radar]] — consumes the policy and contract catalysts
- [[entities/database]] — table definitions, RLS, and migrations
- [[entities/congress-trades]] — sibling STOCK Act disclosure ingestion
- [[entities/engine]] — the Python data engine hosting this pipeline
- [[entities/pipeline]] — the daily pipeline lifecycle
