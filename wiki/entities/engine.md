---
tags: [engine, python, pipeline, ingestion]
category: entity
---

# Engine

The Python data engine (`apps/engine/`) is the core of the platform. It ingests financial newsletters, runs parallel LLM analysis, builds consensus, validates and executes trades, and provides feedback for continuous improvement.

## Architecture

The engine is organized into modules under `apps/engine/`:

- `core/` — configuration, logging, shared utilities
- `ingest/` — newsletter scraping, economic calendar, government data
- `analysis/` — parallel LLM analysis with tool-calling loops
- `consensus/` — semantic grouping, weighted voting, event promotion
- `execution/` — pre-market validation, Reg T checks, trade settlement
- `feedback/` — post-mortem, contrarian analysis, cause & effect
- `autoresearch/` — weekly autonomous prompt improvement loop
- `tests/` — zero-warning test suite with dependency injection

## Newsletter Ingestion

Ingestion is the first phase of the daily pipeline. It fetches newsletters from Gmail using one of two authentication methods:

- **Google App Password (Preferred)**: When `GMAIL_EMAIL` and `GMAIL_APP_PASSWORD` are set, the engine connects directly to `imap.gmail.com:993` via SSL using Python's built-in `imaplib`. It uses Gmail's `X-GM-RAW` search extension to run standard Gmail query filters (`from:(...) newer_than:1d`). This method eliminates the need for Google Cloud OAuth setup, token refresh, and consent screen configuration.
- **OAuth 2.0 (Fallback)**: When `GMAIL_CREDENTIALS_JSON` and `GMAIL_TOKEN_JSON` are provided, the engine falls back to the Google Cloud REST API (`build('gmail', 'v1', ...)`). This path includes resilient JSON secret parsing (`_parse_json_secret`) and automatic retries on transient errors (`502`, `429`).

Both methods parse email bodies (plain text or HTML), extract sender, subject, and date, and produce `NewsletterSnapshot` objects for downstream processing. The IMAP path uses `asyncio.to_thread` to avoid blocking the event loop.

## Related

- [[concepts/ingestion]]
- [[entities/pipeline]]
- [[entities/generated-newsletters]]
- [[concepts/tool-enforcement]]
- [[concepts/rag-strategy]]
