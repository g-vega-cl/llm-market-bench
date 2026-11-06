---
tags: [web, today, news, catalysts, component]
category: entity
---

# Intraday News Wire

The Intraday News Wire (`IntradayNewsWire`) is the Today-page component that surfaces Jev-vetted intraday catalysts to human readers. It renders the `intraday_market_news` records as a live card grid, giving a real-time view of what the trading agents are reacting to.

## Data Flow

- `fetchIntradayNews(limit=50)` (`apps/web/src/features/today/api/fetch-intraday-news.ts`) queries the `intraday_market_news` table ordered by `event_timestamp` descending and attaches `formattedTime`/`formattedDate` in Eastern time.
- `fetchTodayData()` loads up to 50 intraday items for the current day into the `TodayData.intradayNews` field, so both vetted catalysts and filtered noise items are part of the single Today-page payload.
- `TodayPage` lazy-loads `IntradayNewsWire` and renders it full-width (`lg:col-span-3`) in the Row 2 grid. The page's empty-state check now also considers `intradayNews`.

## Rendering & Tabs

The header includes a two-tab switcher built with `@llm-market-bench/ui-design-system` `Button` primitives:
- **⚡ Catalysts (`MARKET_MOVING`)** — default active tab showing high-impact catalysts with green `success` badges (`⚡ MARKET_MOVING <confidence>%`).
- **🔇 Filtered Noise (`NOISE`)** — secondary tab showing headlines rejected by Jev with neutral badges (`🔇 NOISE <confidence>%`), allowing human readers to audit what the sieve filtered out.

Each card shows the ET timestamp, source, Jev badge, headline, truncated summary, up to four ticker badges, and an external source link when a URL is present.

## Related

- [[entities/intraday-news]]
- [[concepts/jev-news-sieve]]
- [[entities/web-app]]
- [[entities/database]]
