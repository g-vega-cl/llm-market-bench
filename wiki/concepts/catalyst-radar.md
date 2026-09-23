---
tags: [catalyst-radar, vector-matching, calendar, digestion]
category: concept
---

# Catalyst Radar

The Catalyst Radar is a 4-stage digestion lifecycle and vector-matched concept-calendar radar that links emerging concept themes to upcoming and digesting market events. Price discovery does not finish at the moment an event occurs — the market requires time to digest the catalyst, and the radar tracks where each event sits in that lifecycle so agents can reason about timing.

## 4-Stage Digestion Lifecycle

Catalysts are positioned relative to `days_to_event` (negative = past/digesting, positive = upcoming). Only the active window `[Now - 3 days, Now + 14 days]` participates in matching; events outside that window are expired and no longer attached to concepts.

## Matching

Matching is computed deterministically in memory or database using vector math:

1. **Concept Filtering**: Filters concepts with `velocity_score >= 1.0` (or `1.2` for agent queries) and valid `concept_vector`.
2. **Calendar Memory Filtering**: Filters active calendar memories with `importance_score >= 7` within `[Now - 3 days, Now + 14 days]`, restricted to critical top-10 global economies (US, Canada, Euro Area, Germany, France, UK, Italy, Spain, Switzerland, Netherlands, China, India, Japan, Korea) and systemic Global events (see [[concepts/ingestion]]).
3. **Cosine Similarity**: Computes cosine similarity between `concept_vector` and memory `embedding`.
4. **Keyword Boost**: Adds `+0.15` match boost when a ticker or keyword overlaps between the concept name and event metadata.
5. **Threshold Gate**: Requires overall similarity `>= 0.55` to prevent spurious vector collisions between unrelated central banks.

The engine pre-computes these collisions (`compute_and_store_catalyst_radar`) and stores the best matches in the `catalyst_radar` table for fast retrieval.

## Title Normalization

`clean_catalyst_title` strips `[CALENDAR EVENT]` prefixes, time tags, dates, and `| Impact | Date` suffixes, and also removes strategy/category labels emitted by the calendar relevance analysis:

- Leading prefixes: `GEOPOLITICAL: `, `INFLATION: `, `CENTRAL_BANK: `, `EMPLOYMENT: `, `GDP: `, `HOLIDAY: `, `ToM/PMI: `, `EARNINGS: `
- Trailing suffixes such as ` (CENTRAL_BANK)`, ` (INFLATION)`

If the text before a colon is only a category label, the body after the colon becomes the title (e.g. `INFLATION: US Michigan 5 Year Inflation: Long-term inflation expectation` becomes `US Michigan 5 Year Inflation`).

## Frontend Catalyst Selection (Composite Score)

In the web app (`apps/web/src/features/concepts/api/fetch-concepts.ts`), each concept is attached the single best catalyst via a composite match score:

```
composite = similarity × timeFactor
timeFactor = max(0.4, 1.0 − 0.03 × min(|deltaDays|, 14))
```

The time factor decays from `1.0` on the event date down to a `0.4` floor at 14+ days away, so proximity still matters but similarity dominates. `buildCatalystMap` keeps the highest-composite candidate per concept — preventing a low-similarity Day-0 catalyst from shadowing a high-similarity near-term one (e.g. `0.42 × 1.0 < 0.88 × 0.97`).

## Agent Tooling & Autoresearch

The radar is exposed to analysis agents as a calendar/catalyst awareness surface, and its matching parameters (velocity, similarity threshold) are tuned by the autoresearch loop.

## Related

- [[concepts/ingestion]]
- [[entities/pipeline]]
- [[entities/engine]]
- [[entities/web-app]]
