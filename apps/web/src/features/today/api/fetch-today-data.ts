import type {
    Decision,
    IntradayMarketNews,
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
    intradayNews: (IntradayMarketNews & { formattedTime: string; formattedDate: string })[];
    trades: (Trade & {
        portfolios: { owner_id: string };
        decisions?: Decision | Decision[] | null;
        formattedTime: string;
    })[];
    decisions: (Decision & { formattedTime: string })[];
    memories: (Memory & { formattedShortDate: string; formattedDateTime: string })[];
    priceUpdates: MarketDataCache[];
    futureEvents: (Memory & {
        formattedShortDate: string;
        formattedTargetMonthDay?: string;
        formattedTargetYear?: string;
    })[];
    marketFeeling: (MarketFeeling & { formattedTime: string; formattedDate: string }) | null;
    macroStats: MacroStat[];
    macroLastUpdated?: string | null;
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
let cachedLimit = 0;
let cachedTradesLimit = 0;
let lastFetchTime = 0;
const CACHE_TTL = 30000; // 30 seconds

export function clearTodayDataCache() {
    cachedTodayData = null;
    cachedLimit = 0;
    cachedTradesLimit = 0;
    lastFetchTime = 0;
}

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
            const fetchedAt = cacheEntry.fetched_at || null;
            const formattedTime = fetchedAt ? formatEasternTime(fetchedAt) : undefined;

            macroStats.push({
                ticker,
                name,
                category: category as MacroCategory,
                price,
                todayPctChange,
                stdevPct,
                regimeFlag,
                hasHistory: stdevPct > 0,
                fetchedAt,
                formattedTime,
            });
        }
    }
    return macroStats;
}

function extractDate(content: string): string | null {
    const match = content.match(/(\d{4}-\d{2}-\d{2})/);
    return match ? match[1] : null;
}

const MONTH_NAMES = [
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

function formatFutureEvents(events: Memory[] | null) {
    return (events || []).map((m) => {
        const eventDate = m.target_date || extractDate(m.content);
        let formattedTargetMonthDay = '';
        let formattedTargetYear = '';
        if (eventDate) {
            const parts = eventDate.split('-');
            if (parts.length === 3) {
                const monthIndex = parseInt(parts[1], 10) - 1;
                const monthName = MONTH_NAMES[monthIndex] || 'Unknown';
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
    });
}

function checkMarketOpen(date: Date): boolean {
    const currentHour = date.getUTCHours();
    const currentMinutes = date.getUTCMinutes();
    const dayOfWeek = date.getUTCDay();

    return (
        dayOfWeek >= 1 &&
        dayOfWeek <= 5 &&
        (currentHour > 13 || (currentHour === 13 && currentMinutes >= 30)) &&
        currentHour < 20
    );
}

function checkSentimentStale(feeling: MarketFeeling | null, now: Date): boolean {
    if (!feeling?.created_at) return true;
    const created = new Date(feeling.created_at);
    const ageHours = (now.getTime() - created.getTime()) / 3600000;
    return ageHours > 4;
}

function computeMacroLastUpdated(
    cacheRows: MarketDataCache[] | null,
    estDateStr: string,
): string | null {
    if (!cacheRows || cacheRows.length === 0) return null;
    let latest: string | null = null;
    for (const row of cacheRows) {
        if (row.fetched_at && (!latest || row.fetched_at > latest)) {
            latest = row.fetched_at;
        }
    }
    if (!latest) return null;
    return latest.startsWith(estDateStr)
        ? formatEasternTime(latest)
        : formatEasternDateTime(latest);
}

function shouldServeCached(nowTime: number, limit: number, tradesLimit: number): boolean {
    return Boolean(
        cachedTodayData &&
            nowTime - lastFetchTime < CACHE_TTL &&
            limit <= cachedLimit &&
            tradesLimit <= cachedTradesLimit,
    );
}

async function executeTodayQueries(
    limit: number,
    effectiveTradesLimit: number,
    startOfDay: string,
    estDateStr: string,
) {
    const supabase = getSupabaseServerClient();
    return Promise.all([
        supabase
            .from('newsletter_snapshots')
            .select('*')
            .gte('date', startOfDay)
            .order('date', { ascending: false })
            .limit(limit),
        supabase
            .from('intraday_market_news')
            .select('*')
            .gte('event_timestamp', startOfDay)
            .order('event_timestamp', { ascending: false })
            .limit(20),
        supabase
            .from('trades')
            .select('*, portfolios(owner_id), decisions(*)')
            .gte('executed_at', startOfDay)
            .order('executed_at', { ascending: false })
            .limit(effectiveTradesLimit),
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
        supabase.from('market_data_cache').select('*').in('ticker', MACRO_TICKERS_LIST),
    ]);
}

interface RawTodayQueryResult {
    newsletters: NewsletterSnapshot[] | null;
    intradayNews: IntradayMarketNews[] | null;
    trades: Trade[] | null;
    decisions: Decision[] | null;
    memories: Memory[] | null;
    futureEvents: Memory[] | null;
    marketFeelingObj: MarketFeeling | null;
    cacheRows: MarketDataCache[] | null;
}

function assembleTodayData(
    raw: RawTodayQueryResult,
    now: Date,
    estDateStr: string,
    startOfDay: string,
): TodayData {
    const priceUpdates = (raw.cacheRows || []).filter(
        (row) => row.fetched_at && row.fetched_at >= startOfDay,
    ) as unknown as MarketDataCache[];

    const macroStats = computeMacroStatistics(raw.cacheRows);
    const macroLastUpdated = computeMacroLastUpdated(raw.cacheRows, estDateStr);

    return {
        newsletters: (raw.newsletters || []).map((n) => ({
            ...n,
            formattedTime: formatEasternShortTime(n.date),
        })) as (NewsletterSnapshot & { formattedTime: string })[],
        intradayNews: (raw.intradayNews || []).map((item) => ({
            ...item,
            formattedTime: formatEasternShortTime(item.event_timestamp),
            formattedDate: formatEasternShortDate(item.event_timestamp),
        })) as (IntradayMarketNews & { formattedTime: string; formattedDate: string })[],
        trades: (raw.trades || []).map((t) => ({
            ...t,
            formattedTime: formatEasternShortTime(t.executed_at),
        })) as (Trade & { portfolios: { owner_id: string }; formattedTime: string })[],
        decisions: (raw.decisions || []).map((d) => ({
            ...d,
            formattedTime: formatEasternShortTime(d.created_at),
        })) as (Decision & { formattedTime: string })[],
        memories: (raw.memories || []).map((m) => ({
            ...m,
            formattedDateTime: formatEasternDateTime(m.created_at),
            formattedShortDate: formatEasternShortDate(m.created_at),
        })) as (Memory & { formattedShortDate: string; formattedDateTime: string })[],
        priceUpdates,
        futureEvents: formatFutureEvents(raw.futureEvents) as (Memory & {
            formattedShortDate: string;
            formattedTargetMonthDay: string;
            formattedTargetYear: string;
        })[],
        marketFeeling: raw.marketFeelingObj
            ? {
                  ...raw.marketFeelingObj,
                  formattedTime: formatEasternTime(raw.marketFeelingObj.created_at),
                  formattedDate: formatEasternDate(raw.marketFeelingObj.created_at),
              }
            : null,
        macroStats,
        macroLastUpdated,
        serverTime: now.toISOString(),
        isMarketOpen: checkMarketOpen(now),
        isSentimentStale: checkSentimentStale(raw.marketFeelingObj, now),
        todayDateString: formatEasternDate(now),
    };
}

export async function fetchTodayData(limit: number = 50, tradesLimit?: number): Promise<TodayData> {
    const effectiveTradesLimit = tradesLimit !== undefined ? tradesLimit : limit;
    const nowTime = Date.now();

    if (shouldServeCached(nowTime, limit, effectiveTradesLimit)) {
        return cachedTodayData as TodayData;
    }

    const now = new Date();
    const estDateStr = now.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
    const startOfDay = `${estDateStr}T00:00:00`;

    let fetchError: unknown = null;
    const queryResults = await executeTodayQueries(
        limit,
        effectiveTradesLimit,
        startOfDay,
        estDateStr,
    ).catch((err) => {
        console.warn('Network or database timeout in fetchTodayData:', err);
        fetchError = err;
        return null;
    });

    if (fetchError || !queryResults) {
        if (cachedTodayData) {
            console.warn('[TodayData] Fetch failed; serving last known good cached data');
            return cachedTodayData;
        }
        throw fetchError instanceof Error
            ? fetchError
            : new Error(`Database connection failed in fetchTodayData: ${String(fetchError)}`);
    }

    const [
        { data: newsletters, error: nlError },
        { data: intradayNews, error: newsError },
        { data: trades, error: tradesError },
        { data: decisions, error: decisionsError },
        { data: memories, error: memError },
        { data: futureEvents, error: feError },
        { data: marketFeeling, error: mfError },
        { data: cacheRows, error: crError },
    ] = queryResults;

    const anyQueryError =
        nlError ||
        newsError ||
        tradesError ||
        decisionsError ||
        memError ||
        feError ||
        mfError ||
        crError;
    if (anyQueryError && !newsletters && !trades && !cacheRows) {
        if (cachedTodayData) {
            console.warn(
                '[TodayData] Database queries returned error; serving last known good cached data',
            );
            return cachedTodayData;
        }
        throw new Error(
            `Database query error in fetchTodayData: ${(anyQueryError as Error)?.message || 'query failed'}`,
        );
    }

    const result = assembleTodayData(
        {
            newsletters,
            intradayNews,
            trades,
            decisions,
            memories,
            futureEvents,
            marketFeelingObj: (marketFeeling?.[0] || null) as MarketFeeling | null,
            cacheRows,
        },
        now,
        estDateStr,
        startOfDay,
    );

    cachedTodayData = result;
    cachedLimit = limit;
    cachedTradesLimit = effectiveTradesLimit;
    lastFetchTime = nowTime;

    return result;
}

let cachedMarketFeeling: MarketFeeling | null = null;

export async function fetchLatestMarketFeeling(): Promise<MarketFeeling | null> {
    try {
        const supabase = getSupabaseServerClient();
        const { data, error } = await supabase
            .from('market_feeling')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(1);

        if (error) {
            console.error('Error fetching latest market feeling:', error);
            return cachedMarketFeeling;
        }

        const feeling = (data?.[0] || null) as MarketFeeling | null;
        if (feeling) {
            cachedMarketFeeling = feeling;
        }
        return feeling ?? cachedMarketFeeling;
    } catch (err) {
        console.warn('Network or database timeout fetching latest market feeling:', err);
        return cachedMarketFeeling;
    }
}
