import { keepPreviousData, useQuery } from '@tanstack/react-query';
import * as React from 'react';
import type { BenchmarkDataPoint } from '../api/fetch-portfolios';
import { portfolioQueries } from '../queries/options';

export type BenchmarkStatus = 'idle' | 'loading' | 'settled' | 'error';

interface UsePortfolioBenchmarkOptions {
    startDate: string;
    endDate: string;
    benchmarkFetchFn: (
        tickers: string[],
        startDate: string,
        endDate: string,
    ) => Promise<Record<string, BenchmarkDataPoint[]>>;
    initialBenchmark?: string;
}

function hasTickerPoints(
    benchmarkData: Record<string, BenchmarkDataPoint[]> | undefined,
    ticker: string,
): boolean {
    return Boolean(ticker && (benchmarkData?.[ticker]?.length ?? 0) > 0);
}

function resolveSettledBenchmark(
    selectedBenchmark: string,
    benchmarkData: Record<string, BenchmarkDataPoint[]> | undefined,
    isPlaceholderData: boolean,
): string {
    if (!selectedBenchmark || !benchmarkData) return '';
    if (hasTickerPoints(benchmarkData, selectedBenchmark)) return selectedBenchmark;
    if (isPlaceholderData) {
        return (
            Object.keys(benchmarkData).find((ticker) => hasTickerPoints(benchmarkData, ticker)) ??
            ''
        );
    }
    return '';
}

/**
 * Manages non-suspending benchmark selection and history fetching for portfolio detail views.
 * Derives settled and loading state directly from TanStack Query without duplicate local state.
 */
export function usePortfolioBenchmark({
    startDate,
    endDate,
    benchmarkFetchFn,
    initialBenchmark = '',
}: UsePortfolioBenchmarkOptions) {
    const [selectedBenchmark, setSelectedBenchmark] = React.useState<string>(initialBenchmark);
    const hasDateRange = Boolean(startDate && endDate);

    const benchmarkQuery = useQuery({
        ...portfolioQueries.benchmarks.history({
            tickers: selectedBenchmark ? [selectedBenchmark] : [],
            startDate,
            endDate,
            fetchFn: () =>
                benchmarkFetchFn(selectedBenchmark ? [selectedBenchmark] : [], startDate, endDate),
        }),
        enabled: Boolean(selectedBenchmark && hasDateRange),
        placeholderData: keepPreviousData,
    });

    const status: BenchmarkStatus =
        !selectedBenchmark || !hasDateRange
            ? 'idle'
            : benchmarkQuery.isError
              ? 'error'
              : benchmarkQuery.isFetching
                ? 'loading'
                : 'settled';

    const settledBenchmark = resolveSettledBenchmark(
        selectedBenchmark,
        benchmarkQuery.data,
        benchmarkQuery.isPlaceholderData,
    );

    const pendingBenchmark = status === 'loading' ? selectedBenchmark : undefined;
    const benchmarkError = status === 'error' ? `Failed to load ${selectedBenchmark}` : undefined;

    return {
        selectedBenchmark,
        onBenchmarkChange: setSelectedBenchmark,
        benchmarkData: benchmarkQuery.data,
        settledBenchmark,
        pendingBenchmark,
        benchmarkError,
        status,
    };
}
