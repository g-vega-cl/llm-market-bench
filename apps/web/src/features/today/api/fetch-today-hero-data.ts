/**
 * fetchTodayHeroData — minimal data for the homepage hero block.
 *
 * Why this exists
 * ---------------
 * The full `fetchTodayData` runs 9 parallel Supabase queries (newsletters,
 * trades, decisions, memories, future events, macro ticker cache, 5000-row
 * price_history, plus the market feeling) and serializes ~290 KB of HTML
 * on the homepage. Lighthouse measured the homepage document at 730 ms TTFB
 * with LCP 4.2 s.
 *
 * The hero block (Market Status + market feeling) only needs a single
 * `market_feeling` row and the server's view of the current ET day. By
 * splitting the loader into a hero pass and a full pass we:
 *   1. Drop the critical-path Supabase queries from 9 to 1.
 *   2. Make the hero's HTML payload ~5 KB instead of ~290 KB.
 *   3. Allow the full data to stream in (Suspense + lazy) without blocking
 *      the LCP element.
 *
 * The result is wired into the homepage via `getTodayHeroData()` and
 * `getTodayData()` running in parallel inside the route loader.
 */

import type { MarketFeeling } from '@llm-market-bench/database';
import { getSupabaseServerClient } from '~/lib/supabase';
import { formatEasternDate, formatEasternTime } from '~/utils/date';

export interface TodayHeroData {
    marketFeeling: (MarketFeeling & { formattedTime: string }) | null;
    isMarketOpen: boolean;
    isSentimentStale: boolean;
    todayDateString: string;
}

interface CacheEntry {
    estDateStr: string;
    fetchedAt: number;
    data: TodayHeroData;
}

let cache: CacheEntry | null = null;
const CACHE_TTL_MS = 60 * 1000;

function computeIsMarketOpen(now: Date): boolean {
    const dayOfWeek = now.getUTCDay();
    const currentHour = now.getUTCHours();
    const currentMinutes = now.getUTCMinutes();
    return (
        dayOfWeek >= 1 &&
        dayOfWeek <= 5 &&
        (currentHour > 13 || (currentHour === 13 && currentMinutes >= 30)) &&
        currentHour < 20
    );
}

/**
 * Returns the minimal hero data for the homepage. Cached for 60 s per
 * Eastern date key so warm function instances pay nothing for repeat hits.
 */
export async function fetchTodayHeroData(): Promise<TodayHeroData> {
    const now = new Date();
    const estDateStr = now.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });

    if (cache && cache.estDateStr === estDateStr && Date.now() - cache.fetchedAt < CACHE_TTL_MS) {
        return cache.data;
    }

    const supabase = getSupabaseServerClient();

    const { data: marketFeeling } = await supabase
        .from('market_feeling')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(1);

    const marketFeelingObj = (marketFeeling?.[0] || null) as MarketFeeling | null;
    const isSentimentStale = marketFeelingObj
        ? (() => {
              if (!marketFeelingObj.created_at) return true;
              const created = new Date(marketFeelingObj.created_at);
              const ageHours = (now.getTime() - created.getTime()) / 3600000;
              return ageHours > 4;
          })()
        : true;

    const data: TodayHeroData = {
        marketFeeling: marketFeelingObj
            ? {
                  ...marketFeelingObj,
                  formattedTime: formatEasternTime(marketFeelingObj.created_at),
              }
            : null,
        isMarketOpen: computeIsMarketOpen(now),
        isSentimentStale,
        todayDateString: formatEasternDate(now),
    };

    cache = { estDateStr, fetchedAt: Date.now(), data };
    return data;
}

/** Test-only: clear the in-memory cache. */
export function __resetHeroCacheForTests(): void {
    cache = null;
}
