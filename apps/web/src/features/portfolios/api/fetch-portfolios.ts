import type {
    Portfolio,
    PortfolioPerformance,
    PositionWithReasoning,
    TradeWithReasoning,
} from '@llm-market-bench/database';
import { getSupabaseServerClient } from '~/lib/supabase';
import {
    getActiveOwnerIds,
    isAutoresearchPortfolio,
    isSystemPortfolio,
    normalizeOwnerId,
} from '../lib/config';

export async function fetchPortfolios(): Promise<
    (Portfolio & { is_active: boolean; is_autoresearch: boolean; is_system: boolean })[]
> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase
        .from('portfolios')
        .select('*')
        .order('total_equity', { ascending: false });

    if (error) throw error;

    const activeIds = new Set(getActiveOwnerIds());
    return data.map((p) => {
        const isSystem = isSystemPortfolio(p.owner_id);
        return {
            ...p,
            is_active: isSystem || activeIds.has(normalizeOwnerId(p.owner_id)),
            is_autoresearch: isAutoresearchPortfolio(p.owner_id),
            is_system: isSystem,
        };
    });
}

export async function fetchPortfolioById(
    id: string,
): Promise<Portfolio & { is_autoresearch: boolean }> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase.from('portfolios').select('*').eq('id', id).single();

    if (error) throw error;
    return {
        ...data,
        is_autoresearch: isAutoresearchPortfolio(data.owner_id),
    };
}

export async function fetchPortfolioByOwnerId(
    ownerId: string,
): Promise<(Portfolio & { is_autoresearch: boolean }) | null> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase
        .from('portfolios')
        .select('*')
        .eq('owner_id', ownerId)
        .maybeSingle();

    if (error) throw error;
    if (!data) return null;
    return {
        ...data,
        is_autoresearch: isAutoresearchPortfolio(data.owner_id),
    };
}

export async function fetchPositions(portfolioId: string): Promise<PositionWithReasoning[]> {
    const supabase = getSupabaseServerClient();

    const [posRes, tradesRes] = await Promise.all([
        supabase
            .from('position_pnl')
            .select('*')
            .eq('portfolio_id', portfolioId)
            .order('ticker', { ascending: true }),
        supabase
            .from('trades')
            .select('*')
            .eq('portfolio_id', portfolioId)
            .in('signal', ['SHORT', 'COVER'])
            .order('executed_at', { ascending: true }),
    ]);

    if (posRes.error) throw posRes.error;
    if (tradesRes.error) throw tradesRes.error;

    const rawPositions = posRes.data || [];
    const shortCoverTrades = tradesRes.data || [];

    // Chronologically match SHORT and COVER trades per ticker to identify true open lots
    const openLotsByTicker = new Map<
        string,
        Array<{ trade: (typeof shortCoverTrades)[0]; remainingQty: number }>
    >();

    for (const trade of shortCoverTrades) {
        const ticker = trade.ticker?.toUpperCase();
        if (!ticker) continue;
        const sig = trade.signal?.toUpperCase();
        const qty = Number(trade.quantity) || 0;

        if (sig === 'SHORT') {
            // If the SHORT trade explicitly has realized_pnl recorded, it is already closed
            if (trade.realized_pnl !== null && trade.realized_pnl !== undefined) {
                continue;
            }
            if (!openLotsByTicker.has(ticker)) {
                openLotsByTicker.set(ticker, []);
            }
            openLotsByTicker.get(ticker)!.push({ trade, remainingQty: qty });
        } else if (sig === 'COVER') {
            const lots = openLotsByTicker.get(ticker) || [];
            let coverQtyNeeded = qty;
            while (lots.length > 0 && coverQtyNeeded > 0) {
                const oldest = lots[0];
                if (oldest.remainingQty <= coverQtyNeeded) {
                    coverQtyNeeded -= oldest.remainingQty;
                    lots.shift();
                } else {
                    oldest.remainingQty -= coverQtyNeeded;
                    coverQtyNeeded = 0;
                }
            }
        }
    }

    const openShorts: typeof shortCoverTrades = [];
    for (const lots of openLotsByTicker.values()) {
        for (const lot of lots) {
            if (lot.remainingQty > 0) {
                openShorts.push({
                    ...lot.trade,
                    quantity: lot.remainingQty,
                });
            }
        }
    }

    if (rawPositions.length === 0 && openShorts.length === 0) return [];

    const longPositions: PositionWithReasoning[] = rawPositions.map((pos) => ({
        ...pos,
        side: 'LONG' as const,
    }));

    let shortPositions: PositionWithReasoning[] = [];
    if (openShorts.length > 0) {
        const shortTickers = Array.from(new Set(openShorts.map((s) => s.ticker)));
        const { data: cacheData, error: cacheError } = await supabase
            .from('market_data_cache')
            .select('ticker, price, fetched_at')
            .in('ticker', shortTickers);

        if (cacheError) throw cacheError;

        const marketMap = new Map<string, { price: number; fetched_at: string }>();
        if (cacheData) {
            for (const item of cacheData) {
                marketMap.set(item.ticker, {
                    price: Number(item.price),
                    fetched_at: item.fetched_at,
                });
            }
        }

        shortPositions = openShorts.map((trade) => {
            const avgCost = Number(trade.price) || 0;
            const marketQuote = marketMap.get(trade.ticker);
            const currentPrice = marketQuote ? marketQuote.price : avgCost;
            const priceFetchedAt = marketQuote?.fetched_at || trade.executed_at;
            const qty = Number(trade.quantity) || 0;

            const unrealizedPnlUsd = (avgCost - currentPrice) * qty;
            const unrealizedPnlPct = avgCost > 0 ? ((avgCost - currentPrice) / avgCost) * 100 : 0;

            return {
                position_id: trade.id,
                portfolio_id: trade.portfolio_id,
                owner_id: null,
                ticker: trade.ticker,
                quantity: qty,
                average_cost_basis: avgCost,
                current_price: currentPrice,
                price_fetched_at: priceFetchedAt,
                unrealized_pnl_usd: unrealizedPnlUsd,
                unrealized_pnl_pct: unrealizedPnlPct,
                side: 'SHORT' as const,
            };
        });
    }

    const allTickers = Array.from(
        new Set(
            [...longPositions.map((p) => p.ticker), ...shortPositions.map((p) => p.ticker)].filter(
                Boolean,
            ),
        ),
    ) as string[];

    const reasoningMap = new Map<string, string>();
    if (allTickers.length > 0) {
        const { data: decisions, error: decError } = await supabase
            .from('decisions')
            .select('ticker, reasoning, signal, created_at, trade_id')
            .in('ticker', allTickers)
            .order('created_at', { ascending: false })
            .limit(100);

        if (decError) throw decError;

        decisions?.forEach((d) => {
            if (!reasoningMap.has(d.ticker)) {
                reasoningMap.set(d.ticker, d.reasoning);
            }
        });
    }

    const combinedPositions = [...longPositions, ...shortPositions].map((pos) => ({
        ...pos,
        reasoning:
            reasoningMap.get(pos.ticker || '') ||
            (pos.side === 'SHORT'
                ? 'Systematic short sector allocation.'
                : 'Reasoning not found in recent signals for this ticker.'),
    }));

    return combinedPositions.sort((a, b) => (a.ticker || '').localeCompare(b.ticker || ''));
}

export async function fetchTrades(portfolioId: string): Promise<TradeWithReasoning[]> {
    const supabase = getSupabaseServerClient();

    const { data: trades, error: tradeError } = await supabase
        .from('trades')
        .select('*')
        .eq('portfolio_id', portfolioId)
        .order('executed_at', { ascending: false })
        .limit(50);

    if (tradeError) throw tradeError;
    if (!trades || trades.length === 0) return [];

    const tickers = Array.from(new Set(trades.map((t) => t.ticker)));
    const { data: decisions, error: decError } = await supabase
        .from('decisions')
        .select('id, ticker, signal, reasoning, trade_id, created_at, metadata')
        .in('ticker', tickers)
        .order('created_at', { ascending: false })
        .limit(200);

    if (decError) throw decError;

    if (!decisions) {
        return trades.map((trade) => ({
            ...trade,
            reasoning: 'Reasoning not linked to this specific trade record.',
        }));
    }

    const decisionsById = new Map<string, (typeof decisions)[0]>();
    const decisionsByTradeId = new Map<string, (typeof decisions)[0]>();
    const decisionsByTicker = new Map<string, ((typeof decisions)[0] & { timestamp: number })[]>();

    for (const d of decisions) {
        decisionsById.set(d.id, d);
        if (d.trade_id) {
            decisionsByTradeId.set(d.trade_id, d);
        }

        let arr = decisionsByTicker.get(d.ticker);
        if (!arr) {
            arr = [];
            decisionsByTicker.set(d.ticker, arr);
        }
        arr.push({
            ...d,
            timestamp: new Date(d.created_at).getTime(),
        });
    }

    return trades.map((trade) => {
        if (trade.decision_id) {
            const match = decisionsById.get(trade.decision_id);
            if (match) return { ...trade, reasoning: match.reasoning, metadata: match.metadata };
        }

        const tradePointerMatch = decisionsByTradeId.get(trade.id);
        if (tradePointerMatch)
            return {
                ...trade,
                reasoning: tradePointerMatch.reasoning,
                metadata: tradePointerMatch.metadata,
            };

        const tradeTime = new Date(trade.executed_at).getTime();
        const tickerDecisions = decisionsByTicker.get(trade.ticker) || [];

        const proximityMatch =
            tickerDecisions.find(
                (d) =>
                    d.signal === trade.signal &&
                    Math.abs(d.timestamp - tradeTime) < 24 * 60 * 60 * 1000,
            ) ?? null;

        if (proximityMatch)
            return {
                ...trade,
                reasoning: proximityMatch.reasoning,
                metadata: proximityMatch.metadata,
            };

        const fallbackMatch = tickerDecisions.length > 0 ? tickerDecisions[0] : null;

        return {
            ...trade,
            reasoning:
                fallbackMatch?.reasoning || 'Reasoning not linked to this specific trade record.',
            metadata: fallbackMatch?.metadata || null,
        };
    });
}

export async function fetchPerformanceHistory(
    portfolioId: string,
): Promise<PortfolioPerformance[]> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase
        .from('portfolio_performance')
        .select('*')
        .eq('portfolio_id', portfolioId)
        .order('date', { ascending: true });

    if (error) throw error;
    return data;
}

export interface BenchmarkDataPoint {
    date: string;
    price: number;
}

export interface PortfolioPerformanceItem {
    portfolioId: string;
    ownerId: string;
    performance: { date: string; value: number; totalEquity: number }[];
}

export async function fetchAllActivePortfolioPerformance(maxDays: number = 90): Promise<{
    portfolios: PortfolioPerformanceItem[];
    startDate: string;
    endDate: string;
}> {
    const supabase = getSupabaseServerClient();

    const { data: portfolios, error: portfoliosError } = await supabase
        .from('portfolios')
        .select('*')
        .order('total_equity', { ascending: false });

    if (portfoliosError) throw portfoliosError;

    const activeIds = new Set(getActiveOwnerIds());
    const activePortfolios = portfolios.filter(
        (p) => isSystemPortfolio(p.owner_id) || activeIds.has(normalizeOwnerId(p.owner_id)),
    );

    if (activePortfolios.length === 0) {
        return { portfolios: [], startDate: '', endDate: '' };
    }

    const portfolioIds = activePortfolios.map((p) => p.id);

    const { data: allPerformance, error: perfError } = await supabase
        .from('portfolio_performance')
        .select('*')
        .in('portfolio_id', portfolioIds)
        .order('date', { ascending: true });

    if (perfError) throw perfError;

    const portfolioPerformanceMap = new Map<string, { date: string; totalEquity: number }[]>();
    for (const p of activePortfolios) {
        portfolioPerformanceMap.set(p.id, []);
    }

    for (const row of allPerformance || []) {
        const arr = portfolioPerformanceMap.get(row.portfolio_id);
        if (arr) {
            arr.push({ date: row.date, totalEquity: Number(row.total_equity) });
        }
    }

    const now = new Date();
    const ninetyDaysAgo = new Date(
        Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - maxDays),
    );

    let earliestStartDate: Date | null = null;

    for (const [, perf] of portfolioPerformanceMap) {
        if (perf.length > 0) {
            const firstDate = new Date(perf[0].date);
            if (!earliestStartDate || firstDate < earliestStartDate) {
                earliestStartDate = firstDate;
            }
        }
    }

    const effectiveStartDate =
        earliestStartDate && earliestStartDate > ninetyDaysAgo ? earliestStartDate : ninetyDaysAgo;

    const filteredPortfolios: PortfolioPerformanceItem[] = [];

    for (const portfolio of activePortfolios) {
        const perf = portfolioPerformanceMap.get(portfolio.id) || [];
        const filtered = perf.filter((p) => {
            const d = new Date(p.date);
            return d >= effectiveStartDate;
        });

        if (filtered.length === 0) continue;

        const firstEquity = filtered[0].totalEquity;

        const normalized = filtered.map((p) => ({
            date: p.date,
            value: firstEquity > 0 ? ((p.totalEquity - firstEquity) / firstEquity) * 100 : 0,
            totalEquity: p.totalEquity,
        }));

        filteredPortfolios.push({
            portfolioId: portfolio.id,
            ownerId: portfolio.owner_id,
            performance: normalized,
        });
    }

    const sortedByDate = filteredPortfolios.map((p) => ({
        ...p,
        performance: [...p.performance].sort((a, b) => a.date.localeCompare(b.date)),
    }));

    const endDate =
        sortedByDate.length > 0
            ? sortedByDate[0].performance[sortedByDate[0].performance.length - 1].date
            : '';

    return {
        portfolios: sortedByDate,
        startDate: effectiveStartDate.toISOString().split('T')[0],
        endDate,
    };
}

export async function fetchBenchmarkHistory(
    tickers: string[],
    startDate: string,
    endDate: string,
): Promise<Record<string, BenchmarkDataPoint[]>> {
    if (tickers.length === 0) return {};

    const supabase = getSupabaseServerClient();
    const allData: { ticker: string; price: number; fetched_at: string }[] = [];
    const limit = 1000;
    let from = 0;

    while (true) {
        const { data, error } = await supabase
            .from('price_history')
            .select('ticker, price, fetched_at')
            .in('ticker', tickers)
            .gte('fetched_at', startDate)
            .lte('fetched_at', endDate)
            .order('fetched_at', { ascending: true })
            .range(from, from + limit - 1);

        if (error) throw error;
        if (!data || data.length === 0) break;

        allData.push(...data);
        if (data.length < limit) break;
        from += limit;
    }

    const result: Record<string, BenchmarkDataPoint[]> = {};
    for (const ticker of tickers) {
        result[ticker] = [];
    }

    allData.forEach((row) => {
        if (result[row.ticker]) {
            const date = row.fetched_at.split('T')[0];
            const existingIndex = result[row.ticker].findIndex((d) => d.date === date);
            if (existingIndex !== -1) {
                result[row.ticker][existingIndex] = {
                    date,
                    price: Number(row.price),
                };
            } else {
                result[row.ticker].push({
                    date,
                    price: Number(row.price),
                });
            }
        }
    });

    return result;
}

export interface FrontierTheme {
    id: string;
    portfolio_id: string;
    theme_name: string;
    thesis: string;
    catalysts: string;
    rubric_score: number;
    status: string;
    tickers: string[];
    created_at?: string;
    updated_at?: string;
}

export async function fetchFrontierThemes(portfolioId: string): Promise<FrontierTheme[]> {
    const supabase = getSupabaseServerClient();
    try {
        const { data, error } = await supabase
            .from('frontier_themes')
            .select('*')
            .eq('portfolio_id', portfolioId)
            .eq('status', 'active')
            .order('rubric_score', { ascending: false });

        if (error) {
            return [];
        }
        return (data as FrontierTheme[]) || [];
    } catch {
        return [];
    }
}

export interface FutureForce {
    id: string;
    portfolio_id?: string;
    force_title: string;
    archetype: string;
    thesis: string;
    catalyst_event: string;
    horizon_months: number;
    target_date?: string | null;
    invalidation_triggers: string;
    transmission_mechanism?: string | null;
    tickers: string[];
    conviction_score: number;
    status: string;
    invalidation_reason?: string | null;
    audited_at?: string | null;
    created_at?: string;
    updated_at?: string;
}

export async function fetchFutureForces(portfolioId?: string): Promise<FutureForce[]> {
    const supabase = getSupabaseServerClient();
    try {
        let query = supabase
            .from('future_forces')
            .select('*')
            .in('status', ['active', 'pending_liquidation']);

        if (portfolioId) {
            query = query.eq('portfolio_id', portfolioId);
        }

        const { data, error } = await query.order('conviction_score', { ascending: false });

        if (error) {
            return [];
        }
        return (data as FutureForce[]) || [];
    } catch {
        return [];
    }
}
