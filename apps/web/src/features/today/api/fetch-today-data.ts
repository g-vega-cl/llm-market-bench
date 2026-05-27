import type {
    Decision,
    LLMReasoningLog,
    MarketDataCache,
    MarketFeeling,
    Memory,
    NewsletterSnapshot,
    Trade,
} from '@llm-market-bench/database';
import { getSupabaseServerClient } from '~/lib/supabase';
import type { MacroCategory, MacroStat } from '../lib/macro-tickers';
import { calculateMacroStats, MACRO_TICKERS, MACRO_TICKERS_LIST } from '../lib/macro-tickers';

export interface TodayData {
    newsletters: NewsletterSnapshot[];
    trades: (Trade & { portfolios: { owner_id: string } })[];
    decisions: Decision[];
    logs: LLMReasoningLog[];
    memories: Memory[];
    priceUpdates: MarketDataCache[];
    futureEvents: Memory[];
    marketFeeling: MarketFeeling | null;
    macroStats: MacroStat[];
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

function buildHistoryGroup(
    historyRows: PriceHistoryItem[] | null,
): Map<string, PriceHistoryItem[]> {
    const historyGroup = new Map<string, PriceHistoryItem[]>();
    if (!historyRows) return historyGroup;
    for (const row of historyRows) {
        const list = historyGroup.get(row.ticker) || [];
        if (list.length < 30) {
            list.push(row);
        }
        historyGroup.set(row.ticker, list);
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
): MacroStat[] {
    const cacheMap = buildCacheMap(cacheRows);
    const historyGroup = buildHistoryGroup(historyRows);
    return computeMacroStatsList(cacheMap, historyGroup);
}

export async function fetchTodayData(): Promise<TodayData> {
    const supabase = getSupabaseServerClient();

    const now = new Date();
    const estDateStr = now.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });

    const startOfDay = `${estDateStr}T00:00:00`;

    // Fetch core dashboard data in parallel where possible to maximize performance
    const [
        { data: newsletters },
        { data: trades },
        { data: decisions },
        { data: logs },
        { data: memories },
        { data: priceUpdates },
        { data: futureEvents },
        { data: marketFeeling },
        { data: cacheRows },
        { data: historyRows },
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
            .from('llm_reasoning_logs')
            .select('*')
            .gte('created_at', startOfDay)
            .order('created_at', { ascending: false }),
        supabase
            .from('memories')
            .select('*')
            .gte('created_at', startOfDay)
            .order('created_at', { ascending: false }),
        supabase
            .from('market_data_cache')
            .select('*')
            .gte('fetched_at', startOfDay)
            .order('fetched_at', { ascending: false }),
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
        // Fetch historical data for all macro tickers (ordered newest-to-oldest)
        supabase
            .from('price_history')
            .select('ticker, price, fetched_at')
            .in('ticker', MACRO_TICKERS_LIST)
            .order('fetched_at', { ascending: false }),
    ]);

    // Process and calculate macro statistics
    const macroStats = computeMacroStatistics(cacheRows, historyRows);

    return {
        newsletters: (newsletters || []) as NewsletterSnapshot[],
        trades: (trades || []) as (Trade & { portfolios: { owner_id: string } })[],
        decisions: (decisions || []) as Decision[],
        logs: (logs || []) as LLMReasoningLog[],
        memories: (memories || []) as Memory[],
        priceUpdates: (priceUpdates || []) as MarketDataCache[],
        futureEvents: (futureEvents || []) as Memory[],
        marketFeeling: (marketFeeling?.[0] || null) as MarketFeeling | null,
        macroStats,
    };
}
