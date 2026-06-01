import type {
    Decision,
    MarketDataCache,
    MarketFeeling,
    Memory,
    NewsletterSnapshot,
    Trade,
} from '@llm-market-bench/database';
import { getSupabaseServerClient } from '~/lib/supabase';
import {
    formatEasternDate,
    formatEasternDateTime,
    formatEasternShortDate,
    formatEasternShortTime,
    formatEasternTime,
} from '~/utils/date';
import { isNyseOpenAt } from '~/utils/market-hours';
import type { MacroCategory, MacroStat } from '../lib/macro-tickers';
import { calculateMacroStats, MACRO_TICKERS, MACRO_TICKERS_LIST } from '../lib/macro-tickers';

export interface TodayData {
    newsletters: (NewsletterSnapshot & { formattedTime: string })[];
    trades: (Trade & { portfolios: { owner_id: string }; formattedTime: string })[];
    decisions: (Decision & { formattedTime: string })[];
    memories: (Memory & { formattedShortDate: string; formattedDateTime: string })[];
    priceUpdates: MarketDataCache[];
    futureEvents: (Memory & {
        formattedShortDate: string;
        formattedTargetMonthDay?: string;
        formattedTargetYear?: string;
    })[];
    marketFeeling: (MarketFeeling & { formattedTime: string }) | null;
    macroStats: MacroStat[];
    serverTime?: string;
    isMarketOpen: boolean;
    isSentimentStale: boolean;
    todayDateString: string;
}

interface PriceHistoryItem {
    ticker: string;
    price: number;
    fetched_at: string;
}

function buildCacheMap(cacheRows: MarketDataCache[] | null): Map<string, MarketDataCache> {
    const cacheMap = new Map<string, MarketDataCache>();
    if (!cacheRows) return cacheMap;
    for (const row of cacheRows) {
        cacheMap.set(row.ticker, row);
    }
    return cacheMap;
}

export function buildHistoryGroup(
    historyRows: PriceHistoryItem[] | null,
    estDateStr: string,
): Map<string, PriceHistoryItem[]> {
    const historyGroup = new Map<string, PriceHistoryItem[]>();
    if (!historyRows) return historyGroup;

    // Track seen dates per ticker to deduplicate intraday ticks
    const seenDates = new Map<string, Set<string>>();

    for (const row of historyRows) {
        const ticker = row.ticker;
        const fetchedAt = row.fetched_at || '';
        if (!fetchedAt) continue;

        // Extract date part (YYYY-MM-DD)
        const dateKey = fetchedAt.substring(0, 10);

        // Exclude today's ET date from historical returns calculations
        if (dateKey === estDateStr) {
            continue;
        }

        let tickerSeen = seenDates.get(ticker);
        if (!tickerSeen) {
            tickerSeen = new Set<string>();
            seenDates.set(ticker, tickerSeen);
        }

        if (!tickerSeen.has(dateKey)) {
            const list = historyGroup.get(ticker) || [];
            if (list.length < 30) {
                list.push(row);
                tickerSeen.add(dateKey);
            }
            historyGroup.set(ticker, list);
        }
    }
    return historyGroup;
}

function computeMacroStatsList(
    cacheMap: Map<string, MarketDataCache>,
    historyGroup: Map<string, PriceHistoryItem[]>,
): MacroStat[] {
    const macroStats: MacroStat[] = [];
    for (const [category, categoryDict] of Object.entries(MACRO_TICKERS)) {
        for (const [ticker, name] of Object.entries(categoryDict)) {
            const cacheEntry = cacheMap.get(ticker);
            const historyEntry = historyGroup.get(ticker) || [];

            const currentPrice = cacheEntry
                ? Number(cacheEntry.price)
                : historyEntry[0]
                  ? Number(historyEntry[0].price)
                  : 0;

            if (currentPrice > 0) {
                macroStats.push(
                    calculateMacroStats(
                        ticker,
                        name,
                        category as MacroCategory,
                        currentPrice,
                        historyEntry.map((h) => ({
                            price: Number(h.price),
                            fetched_at: h.fetched_at || '',
                        })),
                    ),
                );
            }
        }
    }
    return macroStats;
}

function computeMacroStatistics(
    cacheRows: MarketDataCache[] | null,
    historyRows: PriceHistoryItem[] | null,
    estDateStr: string,
): MacroStat[] {
    const cacheMap = buildCacheMap(cacheRows);
    const historyGroup = buildHistoryGroup(historyRows, estDateStr);
    return computeMacroStatsList(cacheMap, historyGroup);
}

function extractDate(content: string): string | null {
    const match = content.match(/(\d{4}-\d{2}-\d{2})/);
    return match ? match[1] : null;
}

interface TodayCacheEntry {
    estDateStr: string;
    fetchedAt: number;
    data: TodayData;
}

let todayCache: TodayCacheEntry | null = null;
const TODAY_CACHE_TTL_MS = 60 * 1000;

/** Test-only: clear the in-memory cache for the today-data fetcher. */
export function __resetTodayCacheForTests(): void {
    todayCache = null;
}

export async function fetchTodayData(): Promise<TodayData> {
    const supabase = getSupabaseServerClient();

    const now = new Date();
    const estDateStr = now.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });

    if (
        todayCache &&
        todayCache.estDateStr === estDateStr &&
        Date.now() - todayCache.fetchedAt < TODAY_CACHE_TTL_MS
    ) {
        return todayCache.data;
    }

    const startOfDay = `${estDateStr}T00:00:00`;

    // 45 days ago lookback for historical volatility calculations
    const historyLimitDate = new Date();
    historyLimitDate.setDate(historyLimitDate.getDate() - 45);

    // Fetch core dashboard data in parallel where possible to maximize performance.
    // `price_history` is now resolved via the `latest_per_ticker_per_day` RPC so
    // we get a pre-deduped payload instead of transferring 5000 raw rows.
    const [
        { data: newsletters },
        { data: trades },
        { data: decisions },
        { data: memories },
        { data: priceUpdates },
        { data: futureEvents },
        { data: marketFeeling },
        { data: cacheRows },
        historyResults,
    ] = await Promise.all([
        supabase
            .from('newsletter_snapshots')
            .select('*')
            .gte('date', startOfDay)
            .order('date', { ascending: false }),
        supabase
            .from('trades')
            .select('*, portfolios(owner_id)')
            .gte('executed_at', startOfDay)
            .order('executed_at', { ascending: false }),
        supabase
            .from('decisions')
            .select('*')
            .gte('created_at', startOfDay)
            .order('created_at', { ascending: false }),
        supabase
            .from('memories')
            .select('*')
            .gte('created_at', startOfDay)
            .order('created_at', { ascending: false }),
        supabase.from('market_data_cache').select('id').gte('fetched_at', startOfDay).limit(1),
        supabase
            .from('memories')
            .select('*')
            .eq('status', 'ACTIVE')
            .gte('importance_score', 8)
            .eq('metadata->is_future_catalyst', true)
            .or(`target_date.is.null,target_date.gte.${estDateStr}`)
            .order('created_at', { ascending: false }),
        supabase
            .from('market_feeling')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(1),
        // Fetch all macro quotes
        supabase.from('market_data_cache').select('*').in('ticker', MACRO_TICKERS_LIST),
        // Server-side deduped price history (one row per ticker/calendar day,
        // last 45 days) — replaces the 5000-row raw query.
        supabase.rpc('latest_per_ticker_per_day', {
            p_tickers: MACRO_TICKERS_LIST,
            p_days: 45,
        }),
    ]);

    // The RPC returns an array; the Supabase client wraps it as `{ data, error }`.
    const historyRows = (historyResults?.data || []) as PriceHistoryItem[];

    // Process and calculate macro statistics
    const macroStats = computeMacroStatistics(cacheRows, historyRows, estDateStr);

    const isMarketOpen = isNyseOpenAt(now);

    const marketFeelingObj = (marketFeeling?.[0] || null) as MarketFeeling | null;
    const isSentimentStale = marketFeelingObj
        ? (() => {
              if (!marketFeelingObj.created_at) return true;
              const created = new Date(marketFeelingObj.created_at);
              const ageHours = (now.getTime() - created.getTime()) / 3600000;
              return ageHours > 4;
          })()
        : true;

    const todayDateString = formatEasternDate(now);

    const data: TodayData = {
        newsletters: (newsletters || []).map((n) => ({
            ...n,
            formattedTime: formatEasternShortTime(n.date),
        })) as (NewsletterSnapshot & { formattedTime: string })[],
        trades: (trades || []).map((t) => ({
            ...t,
            formattedTime: formatEasternShortTime(t.executed_at),
        })) as (Trade & { portfolios: { owner_id: string }; formattedTime: string })[],
        decisions: (decisions || []).map((d) => ({
            ...d,
            formattedTime: formatEasternShortTime(d.created_at),
        })) as (Decision & { formattedTime: string })[],
        memories: (memories || []).map((m) => ({
            ...m,
            formattedDateTime: formatEasternDateTime(m.created_at),
            formattedShortDate: formatEasternShortDate(m.created_at),
        })) as (Memory & { formattedShortDate: string; formattedDateTime: string })[],
        priceUpdates: (priceUpdates || []) as unknown as MarketDataCache[],
        futureEvents: (futureEvents || []).map((m) => {
            const eventDate = m.target_date || extractDate(m.content);
            let formattedTargetMonthDay = '';
            let formattedTargetYear = '';
            if (eventDate) {
                const parts = eventDate.split('-');
                if (parts.length === 3) {
                    const months = [
                        'Jan',
                        'Feb',
                        'Mar',
                        'Apr',
                        'May',
                        'Jun',
                        'Jul',
                        'Aug',
                        'Sep',
                        'Oct',
                        'Nov',
                        'Dec',
                    ];
                    const monthName = months[parseInt(parts[1], 10) - 1] || 'Unknown';
                    formattedTargetMonthDay = `${monthName} ${parseInt(parts[2], 10)}`;
                    formattedTargetYear = parts[0];
                }
            }
            return {
                ...m,
                formattedShortDate: formatEasternShortDate(m.created_at),
                formattedTargetMonthDay,
                formattedTargetYear,
            };
        }) as (Memory & {
            formattedShortDate: string;
            formattedTargetMonthDay: string;
            formattedTargetYear: string;
        })[],
        marketFeeling: marketFeelingObj
            ? {
                  ...marketFeelingObj,
                  formattedTime: formatEasternTime(marketFeelingObj.created_at),
              }
            : null,
        macroStats,
        serverTime: now.toISOString(),
        isMarketOpen,
        isSentimentStale,
        todayDateString,
    };

    todayCache = { estDateStr, fetchedAt: Date.now(), data };
    return data;
}
