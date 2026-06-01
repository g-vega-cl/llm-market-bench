---
tags: [web, utils, market-hours, dst, timezone, bugfix]
category: concept
---

# Market Hours Utility

A single-purpose utility that answers the question "is the NYSE regular trading session open right now?" in a way that survives the EST↔EDT transition. Lives in `apps/web/src/utils/market-hours.ts` and is consumed by every page or loader that renders an "OPEN/CLOSED" badge.

## The DST bug (what this fixes)

A naïve UTC-window check like `currentHour >= 13:30 && currentHour < 20` is **only correct during EDT** (UTC-4). When the US falls back to EST (UTC-5) the NYSE window shifts to 14:30–21:00 UTC, so the same hardcoded check would:

- Report "OPEN" at 8:30 AM ET (1 hour too early) on a January Tuesday
- Report "CLOSED" at 3:00 PM ET (1 hour too early) on a January Tuesday

This was a real bug in three call sites (`fetch-today-hero-data.ts`, `fetch-today-data.ts`, `MarketOverviewPage.tsx`) until 2026-06-01, when they were all unified behind the utility described here.

## The fix: ET-relative via `Intl.DateTimeFormat`

```ts
const ET_TIMEZONE = 'America/New_York';

const WEEKDAY_FROM_SHORT: Record<string, number> = {
    Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6,
};

export interface EasternParts {
    weekday: number;
    hour: number;
    minute: number;
}

export function getEasternParts(now: Date): EasternParts {
    const fmt = new Intl.DateTimeFormat('en-US', {
        timeZone: ET_TIMEZONE,
        weekday: 'short',
        hour: 'numeric',
        minute: '2-digit',
        hour12: false,
    });
    const lookup: Record<string, string> = {};
    for (const part of fmt.formatToParts(now)) {
        lookup[part.type] = part.value;
    }
    return {
        weekday: WEEKDAY_FROM_SHORT[lookup.weekday ?? 'Mon'] ?? 0,
        hour: parseInt(lookup.hour ?? '0', 10),
        minute: parseInt(lookup.minute ?? '0', 10),
    };
}

export function isNyseOpenAt(now: Date): boolean {
    const { weekday, hour, minute } = getEasternParts(now);
    const isWeekday = weekday >= 1 && weekday <= 5;
    const afterOpen = hour > 9 || (hour === 9 && minute >= 30);
    const beforeClose = hour < 16;
    return isWeekday && afterOpen && beforeClose;
}
```

The IANA `America/New_York` zone encodes the full DST transition schedule (2nd Sunday of March → 1st Sunday of November), so the runtime always returns the correct local hour for any instant — no manual offset arithmetic.

## Why not other approaches

- **Manual offset calculation** (`now.getTimezoneOffset()` + add to UTC): requires re-implementing the DST rules yourself. The runtime already does this.
- **Use 14:30–21:00 UTC as a "safe" average**: correct for EST, wrong for EDT — bug shifts instead of disappearing.
- **`date-fns-tz` / `luxon`**: heavy dependency for one boolean.

## TDD coverage (11 boundary cases)

In `apps/web/src/utils/market-hours.test.ts`:

| UTC instant | Local ET | Expected |
|---|---|---|
| 2026-07-15T13:29:00Z (EDT Wed) | 9:29 AM | closed |
| 2026-07-15T13:30:00Z (EDT Wed) | 9:30 AM | **open** (boundary) |
| 2026-07-15T15:00:00Z (EDT Wed) | 11:00 AM | open |
| 2026-07-15T19:59:00Z (EDT Wed) | 3:59 PM | open |
| 2026-07-15T20:00:00Z (EDT Wed) | 4:00 PM | **closed** (boundary) |
| 2026-01-15T14:29:00Z (EST Thu) | 9:29 AM | closed (old code: open) |
| 2026-01-15T14:30:00Z (EST Thu) | 9:30 AM | **open** (old code: closed) |
| 2026-01-15T20:59:00Z (EST Thu) | 3:59 PM | open (old code: closed) |
| 2026-01-15T21:00:00Z (EST Thu) | 4:00 PM | **closed** (boundary) |
| 2026-01-17T15:00:00Z (EST Sat) | 10:00 AM | closed (weekend) |
| 2026-01-18T15:00:00Z (EST Sun) | 10:00 AM | closed (weekend) |

The four EST cases are the ones that the old hardcoded UTC window got wrong. `market-hours.ts` has 100% line coverage.

## Call sites

The utility is now used in three places, all previously duplicating the same buggy logic:

- `apps/web/src/features/today/api/fetch-today-hero-data.ts` — pre-computes `isMarketOpen` for the LCP hero block (`MarketStatusHero`)
- `apps/web/src/features/today/api/fetch-today-data.ts` — same field, populated alongside `marketFeeling`, `isSentimentStale`, and `todayDateString` (Zero-Date Frontend Architecture — see [[concepts/performance-auditing-strategy]])
- `apps/web/src/features/market-overview/pages/MarketOverviewPage.tsx` — drives the "MARKET OPEN / MARKET CLOSED" badge in the hero

## Performance impact

`Intl.DateTimeFormat` is marginally slower than `getUTCHours`, but the function runs at most once per page load (and once per 60 s cache hit in the hero loader). Negligible.

## Known limitations (deferred)

- **NYSE holidays** (10/year: New Year's, MLK, Presidents', Good Friday, Memorial Day, Juneteenth, July 4, Labor Day, Thanksgiving, Christmas) are not modeled. The function reports "OPEN" on July 4th. Requires a holiday calendar data structure (hardcoded list, or a `market_holidays` table) and a follow-up set of TDD cases.
- **Pre-market** (4:00–9:30 AM ET) and **after-hours** (4:00–8:00 PM ET) are not modeled.
- **`MarketOverviewPage`** computes `now` at React render time. The value is now correct, but there's still a pre-existing hydration drift risk if the SSR/CSR instants straddle 9:30 AM or 4:00 PM ET. The clean fix is to pre-compute `isMarketOpen` in the route loader instead.

## Related

- [[entities/web-app]] — the homepage hero is the primary consumer
- [[concepts/hero-loader-split]] — the hero loader returns `isMarketOpen` as part of `TodayHeroData`
- [[concepts/performance-auditing-strategy]] — Zero-Date Frontend Architecture that this utility fits into
- [[wiki/log]] — bugfix entry: `[2026-06-01] bugfix | DST-aware NYSE market open calculation (3 call sites)`
