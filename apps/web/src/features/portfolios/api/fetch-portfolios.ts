import type {
    Portfolio,
    PortfolioPerformance,
    PositionWithReasoning,
    TradeWithReasoning,
} from '@llm-market-bench/database';
import { getSupabaseServerClient } from '~/lib/supabase';
import { getActiveOwnerIds, normalizeOwnerId } from '../lib/config';

export async function fetchPortfolios(): Promise<(Portfolio & { is_active: boolean })[]> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase
        .from('portfolios')
        .select('*')
        .order('total_equity', { ascending: false });

    if (error) throw error;

    const activeIds = new Set(getActiveOwnerIds());
    return data.map((p) => ({
        ...p,
        is_active: activeIds.has(normalizeOwnerId(p.owner_id)),
    }));
}

export async function fetchPortfolioById(id: string): Promise<Portfolio> {
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase.from('portfolios').select('*').eq('id', id).single();

    if (error) throw error;
    return data;
}

export async function fetchPositions(portfolioId: string): Promise<PositionWithReasoning[]> {
    const supabase = getSupabaseServerClient();

    const { data: positions, error: posError } = await supabase
        .from('position_pnl')
        .select('*')
        .eq('portfolio_id', portfolioId)
        .order('ticker', { ascending: true });

    if (posError) throw posError;
    if (!positions || positions.length === 0) return [];

    const tickers = positions.map((p) => p.ticker);

    const { data: decisions, error: decError } = await supabase
        .from('decisions')
        .select('ticker, reasoning, signal, created_at, trade_id')
        .in('ticker', tickers)
        .order('created_at', { ascending: false })
        .limit(100);

    if (decError) throw decError;

    const reasoningMap = new Map<string, string>();

    decisions?.forEach((d) => {
        if (!reasoningMap.has(d.ticker)) {
            reasoningMap.set(d.ticker, d.reasoning);
        }
    });

    return positions.map((pos) => ({
        ...pos,
        reasoning:
            reasoningMap.get(pos.ticker) ||
            'Reasoning not found in recent signals for this ticker.',
    }));
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
        .select('id, ticker, signal, reasoning, trade_id, created_at')
        .in('ticker', tickers)
        .order('created_at', { ascending: false })
        .limit(200);

    if (decError) throw decError;

    return trades.map((trade) => {
        if (trade.decision_id) {
            const match = decisions?.find((d) => d.id === trade.decision_id);
            if (match) return { ...trade, reasoning: match.reasoning };
        }

        const tradePointerMatch = decisions?.find((d) => d.trade_id === trade.id);
        if (tradePointerMatch) return { ...trade, reasoning: tradePointerMatch.reasoning };

        const tradeTime = new Date(trade.executed_at).getTime();
        const proximityMatch = decisions?.find(
            (d) =>
                d.ticker === trade.ticker &&
                d.signal === trade.signal &&
                Math.abs(new Date(d.created_at).getTime() - tradeTime) < 24 * 60 * 60 * 1000,
        );
        if (proximityMatch) return { ...trade, reasoning: proximityMatch.reasoning };

        const fallbackMatch = decisions?.find((d) => d.ticker === trade.ticker);

        return {
            ...trade,
            reasoning:
                fallbackMatch?.reasoning || 'Reasoning not linked to this specific trade record.',
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
    const activePortfolios = portfolios.filter((p) => activeIds.has(normalizeOwnerId(p.owner_id)));

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
    const ninetyDaysAgo = new Date(now.getTime() - maxDays * 24 * 60 * 60 * 1000);

    let mostRecentStartDate = new Date(0);

    for (const [, perf] of portfolioPerformanceMap) {
        if (perf.length > 0) {
            const firstDate = new Date(perf[0].date);
            if (firstDate > mostRecentStartDate) {
                mostRecentStartDate = firstDate;
            }
        }
    }

    const effectiveStartDate =
        mostRecentStartDate > ninetyDaysAgo ? mostRecentStartDate : ninetyDaysAgo;

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
    const { data, error } = await supabase
        .from('price_history')
        .select('ticker, price, fetched_at')
        .in('ticker', tickers)
        .gte('fetched_at', startDate)
        .lte('fetched_at', endDate)
        .order('fetched_at', { ascending: true });

    if (error) throw error;

    const result: Record<string, BenchmarkDataPoint[]> = {};
    for (const ticker of tickers) {
        result[ticker] = [];
    }

    data?.forEach((row) => {
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
