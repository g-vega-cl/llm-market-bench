import type {
    Portfolio,
    PortfolioPerformance,
    PositionWithReasoning,
    TradeWithReasoning,
} from '@llm-market-bench/database';
import { queryOptions } from '@tanstack/react-query';
import type { BenchmarkDataPoint, PortfolioPerformanceItem } from '../api/fetch-portfolios';
import { portfolioQueryKeys } from './keys';

type PortfolioWithActive = Portfolio & { is_active: boolean };

interface PortfolioDetailData {
    portfolio: Portfolio;
    positions: PositionWithReasoning[];
    history: PortfolioPerformance[];
    trades: TradeWithReasoning[];
}

interface ComparisonData {
    portfolios: PortfolioPerformanceItem[];
    startDate: string;
    endDate: string;
    benchmarkData: Record<string, BenchmarkDataPoint[]>;
}

export const portfolioQueries = {
    list: <T extends PortfolioWithActive[]>(opts?: { fetchFn?: () => Promise<T> }) =>
        queryOptions({
            queryKey: portfolioQueryKeys.list(),
            queryFn: opts?.fetchFn,
            staleTime: 1000 * 60 * 5, // 5 minutes
        }),

    detail: <T extends PortfolioDetailData>(opts: { id: string; fetchFn?: () => Promise<T> }) =>
        queryOptions({
            queryKey: portfolioQueryKeys.detail(opts.id),
            queryFn: opts.fetchFn,
            staleTime: 1000 * 60 * 5, // 5 minutes
        }),

    comparison: <T extends ComparisonData>(opts: {
        benchmark: string;
        fetchFn?: () => Promise<T>;
    }) =>
        queryOptions({
            queryKey: portfolioQueryKeys.comparison(opts.benchmark),
            queryFn: opts.fetchFn,
            staleTime: 1000 * 60 * 5, // 5 minutes
        }),

    benchmarks: {
        history: <T extends Record<string, BenchmarkDataPoint[]>>(opts: {
            tickers: string[];
            startDate: string;
            endDate: string;
            fetchFn?: () => Promise<T>;
        }) =>
            queryOptions({
                queryKey: portfolioQueryKeys.benchmarks.history(
                    opts.tickers,
                    opts.startDate,
                    opts.endDate,
                ),
                queryFn: opts.fetchFn,
                staleTime: 1000 * 60 * 5, // 5 minutes
            }),
    },
};
