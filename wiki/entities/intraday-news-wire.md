---
tags: [web, today, news, catalysts, component]
category: entity
---

# Intraday News Wire

The Intraday News Wire (`IntradayNewsWire`) is the Today-page component that surfaces Jev-vetted intraday catalysts to human readers. It renders the `intraday_market_news` records as a live card grid, giving a real-time view of what the trading agents are reacting to.

## Data Flow

- `fetchIntradayNews(limit=20)` (`features/today/api/fetch-intraday-news.ts`) queries the `intraday_market_news` table ordered by `event_timestamp` descending and attaches `formattedTime`/`formattedDate` in Eastern time.
- `fetchTodayData()` also loads up to 20 intraday items for the current day into the `TodayData.intradayNews` field, so the wire is part of the single Today-page payload.
- `TodayPage` lazy-loads `IntradayNewsWire` and renders it full-width (`lg:col-span-3`) in the Row 2 grid. The page's empty-state check now also considers `intradayNews`.

## Rendering

Each card shows the ET timestamp, source, a Jev badge (`⚡ MARKET_MOVING <confidence>%`), the headline, a truncated summary, up to four ticker badges, and an external source link when a URL is present. When there are no items, the component shows a standby state ("No breaking catalysts detected yet today") with a "Vetted by Jev AI" marker.

## Related

- [[entities/intraday-news]]
- [[concepts/jev-news-sieve]]
- [[entities/web-app]]
- [[entities/database]]
