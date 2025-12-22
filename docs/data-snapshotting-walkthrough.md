# Step 4: Data Snapshotting Walkthrough

This document outlines the implementation of the Data Snapshotting layer for the AI Wall Street project.

## Overview

The goal of this step was to save raw newsletter text and metadata into Supabase Postgres to create an audit trail and ensure idempotency (preventing duplicate processing).

## Architecture

1.  **Ingestion**: `apps/engine/ingest/newsletter.py` fetches newsletters from Gmail.
2.  **Orchestration**: `apps/engine/main.py` coordinates the flow.
3.  **Storage**: `apps/engine/core/db.py` uses the Supabase Python SDK to save data.

## Implementation Details

### Database Schema
The `newsletter_snapshots` table includes:
- `source_id`: Unique identifier for the newsletter.
- `chunk_hash`: Hash of the content.
- `date`: Normalized timestamp.
- **Constraint**: `UNIQUE(date, source_id)` ensures that even if the job runs multiple times, only one copy of a newsletter for a specific date is kept.

### Date Normalization
Gmail headers use various date formats. We implemented `parsedate_to_datetime` from `email.utils` to ensure all dates are converted to valid ISO 8601 strings before being sent to Postgres.

```python
from email.utils import parsedate_to_datetime
# ...
try:
    date_dt = parsedate_to_datetime(raw_date)
    date = date_dt.isoformat()
except Exception:
    date = datetime.now().isoformat()
```

### Security
We use the Supabase **Service Role Key** in the backend engine to bypass Row Level Security (RLS) for internal data management.

## Verification

The pipeline has been verified with a live connection to Supabase:
- Successful ingestion of newsletters.
- Successful upsert into the `newsletter_snapshots` table.
- Verified idempotency by running the script multiple times.

## Files Created/Modified
- `apps/engine/core/db.py` (New)
- `apps/engine/main.py` (Modified)
- `apps/engine/ingest/newsletter.py` (Modified)
- `apps/engine/requirements.txt` (Modified)
- `supabase/migrations/20231221000000_create_newsletters_table.sql` (New)
- `.github/workflows/ingest.yml` (Modified)
