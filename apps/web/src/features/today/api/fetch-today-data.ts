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
import type { MacroCategory, MacroStat } from '../lib/macro-tickers';
import { MACRO_TICKERS, MACRO_TICKERS_LIST } from '../lib/macro-tickers';

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

let cachedTodayData: TodayData | null = null;
let lastFetchTime = 0;
const CACHE_TTL = 30000; // 30 seconds
const isTest = typeof process !== 'undefined' && process.env.NODE_ENV === 'test';

function computeMacroStatistics(cacheRows: MarketDataCache[] | null): MacroStat[] {
    const macroStats: MacroStat[] = [];
    if (!cacheRows) return macroStats;

    const cacheMap = buildCacheMap(cacheRows);

    for (const [category, categoryDict] of Object.entries(MACRO_TICKERS)) {
        for (const [ticker, name] of Object.entries(categoryDict)) {
            const cacheEntry = cacheMap.get(ticker);
            if (!cacheEntry) continue;

            const price = Number(cacheEntry.price) || 0;
            const todayPctChange = Number(cacheEntry.today_pct_change) || 0;
            const stdevPct = Number(cacheEntry.stdev_pct) || 0;
            const regimeFlag = (cacheEntry.regime_flag || 'Normal') as
                | 'Normal'
                | '❗ UNUSUAL'
                | '⚠️ HIGHLY UNUSUAL';

            macroStats.push({
                ticker,
                name,
                category: category as MacroCategory,
                price,
                todayPctChange,
                stdevPct,
                regimeFlag,
                hasHistory: stdevPct > 0,
            });
        }
    }
    return macroStats;
}

function extractDate(content: string): string | null {
    const match = content.match(/(\d{4}-\d{2}-\d{2})/);
    return match ? match[1] : null;
}

export async function fetchTodayData(limit: number = 50): Promise<TodayData> {
    const nowTime = Date.now();
    // Do not use in-memory cache if we are asking for more items than default
    if (!isTest && cachedTodayData && nowTime - lastFetchTime < CACHE_TTL && limit <= 50) {
        return cachedTodayData;
    }

    const supabase = getSupabaseServerClient();

    const now = new Date();
    const estDateStr = now.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });

    const startOfDay = `${estDateStr}T00:00:00`;

    // Fetch core dashboard data in parallel (reduced from 9 to 7 database queries!)
    const [
        { data: newsletters },
        { data: trades },
        { data: decisions },
        { data: memories },
        { data: futureEvents },
        { data: marketFeeling },
        { data: cacheRows },
    ] = await Promise.all([
        supabase
            .from('newsletter_snapshots')
            .select('*')
            .gte('date', startOfDay)
            .order('date', { ascending: false })
            .limit(limit),
        supabase
            .from('trades')
            .select('*, portfolios(owner_id)')
            .gte('executed_at', startOfDay)
            .order('executed_at', { ascending: false })
            .limit(limit),
        supabase
            .from('decisions')
            .select('*')
            .gte('created_at', startOfDay)
            .order('created_at', { ascending: false })
            .limit(limit),
        supabase
            .from('memories')
            .select('*')
            .gte('created_at', startOfDay)
            .order('created_at', { ascending: false })
            .limit(limit),
        supabase
            .from('memories')
            .select('*')
            .eq('status', 'ACTIVE')
            .gte('importance_score', 8)
            .eq('metadata->is_future_catalyst', true)
            .or(`target_date.is.null,target_date.gte.${estDateStr}`)
            .order('created_at', { ascending: false })
            .limit(limit),
        supabase
            .from('market_feeling')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(1),
        // Fetch all macro quotes + pre-calculated volatility in a single query
        supabase.from('market_data_cache').select('*').in('ticker', MACRO_TICKERS_LIST),
    ]);

    // Derive priceUpdates in-memory from cacheRows to eliminate an entire extra DB query
    const priceUpdates = (cacheRows || []).filter(
        (row) => row.fetched_at && row.fetched_at >= startOfDay,
    ) as unknown as MarketDataCache[];

    // Process and map pre-calculated macro statistics
    const macroStats = computeMacroStatistics(cacheRows);

    const currentHour = now.getUTCHours();
    const currentMinutes = now.getUTCMinutes();
    const dayOfWeek = now.getUTCDay();

    const isMarketOpen =
        dayOfWeek >= 1 &&
        dayOfWeek <= 5 &&
        (currentHour > 13 || (currentHour === 13 && currentMinutes >= 30)) &&
        currentHour < 20;

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

    const result: TodayData = {
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
        priceUpdates,
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

    if (!isTest) {
        cachedTodayData = result;
        lastFetchTime = nowTime;
    }

    return result;
}
