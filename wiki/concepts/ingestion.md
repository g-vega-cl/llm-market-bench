---
tags: [ingestion, newsletters, calendar, government]
category: concept
---

# Ingestion

Three parallel ingestion streams that feed the pipeline:

- **Newsletters**: Gmail API → HTML parsing (BeautifulSoup) → ad removal
  (Gemini Flash, parallel via `asyncio.gather`) → deterministic hashing → single-transaction bulk `UPSERT` into `newsletter_snapshots` (with automated sequential fallback on failure).
  Source IDs use the `news_{sender_clean}_{MD5[:8]}` pattern for idempotency; chunk hashes are SHA-256.
- **Economic Calendar**: Periodic cron fetches global macro catalysts →
  `CALENDAR_EVENT` memories with `is_future_catalyst=true`.
- **Government Tracking**: Scans for policy bills, subsidies, regulatory changes
  across G7 and major G20 economies. Stores as `GOVERNMENT_INCENTIVE` memories.

## Key Design

Deterministic `source_id = news_{sender_clean}_{MD5[:8]}` (where `sender_clean` is the sender's email address slugified, and the `MD5[:8]` hash is derived from `date_str + sender + subject`) means re-ingesting the same email produces the same ID. UPSERTs are idempotent. If a sender re-sends an article under a new subject, the chunk hash changes and it's treated as new.

## Related

- [[entities/pipeline]]
- [[concepts/reasoning]]
