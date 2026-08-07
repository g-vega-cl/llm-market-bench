---
tags: [ingestion, newsletter, scraping, pipeline]
category: concept
---

# Ingestion

Ingestion is the first phase of the daily pipeline. It fetches raw data from multiple sources: financial newsletters, economic calendars, and government data feeds. The data is stored in Supabase and later consumed by analysis agents.

## Newsletter Scraping

- **Newsletter Snapshots**: Ingested newsletters are stored in the `newsletter_snapshots` table with a `date` field indicating their publication time.
- **Daily Newsletter Generation**: A separate step (see [[entities/generated-newsletters]]) generates a digest newsletter using DeepSeek V4 Flash. It queries newsletters published within the last **12 hours** (based on the `date` column), not the `ingested_at` timestamp. This rolling window ensures overnight and early-morning editions are captured for the morning session.
- **Lookback Window**: The 12-hour window is measured from the current Eastern Time to the `date` field of each snapshot. The switch from `ingested_at` to `date` improved alignment with actual publication times.

## Economic Calendar

… (existing content)

## Government Data

… (existing content)

## Related

- [[entities/generated-newsletters]]
- [[entities/pipeline]]
- [[concepts/ingestion]]
