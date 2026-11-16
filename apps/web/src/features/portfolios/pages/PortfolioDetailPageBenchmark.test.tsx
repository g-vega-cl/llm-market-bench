import type { Portfolio, PortfolioPerformance } from '@llm-market-bench/database';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import * as React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { BenchmarkDataPoint } from '../api/fetch-portfolios';
import { PortfolioDetailPage } from './PortfolioDetailPage';

vi.mock('@tanstack/react-router', () => ({
    // biome-ignore lint/suspicious/noExplicitAny: mock router Link
    Link: ({ children }: any) => <div>{children}</div>,
}));

vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        capture: vi.fn(),
    }),
}));

vi.mock('../components/StrategyExplainer', () => ({
    StrategyExplainer: () => <div data-testid="strategy-explainer">Explainer</div>,
}));

// biome-ignore lint/suspicious/noExplicitAny: capture chart props in test
let lastChartProps: any = null;
vi.mock('../components/PerformanceChart', () => ({
    // biome-ignore lint/suspicious/noExplicitAny: mock PerformanceChart
    PerformanceChart: (props: any) => {
        lastChartProps = props;
        return (
            <div data-testid="performance-chart">
                {props.pendingBenchmark ? `Loading ${props.pendingBenchmark}...` : 'Chart Ready'}
            </div>
        );
    },
}));

vi.mock('../components/PositionsTable', () => ({
    PositionsTable: () => <div data-testid="positions-table">Positions</div>,
}));

vi.mock('../components/TradesTable', () => ({
    TradesTable: () => <div data-testid="trades-table">Trades</div>,
}));

function createDeferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return { promise, resolve, reject };
}

describe('PortfolioDetailPage Benchmark Switching (Zero Suspense Reload)', () => {
    let queryClient: QueryClient;

    const mockPortfolio = {
        id: 'sys-port-1',
        owner_id: 'sys-daily-spy-deepseek-v4-flash',
        total_equity: 10100,
        cash_balance: 10100,
        buying_power: 40400,
        created_at: '2026-09-01T00:00:00Z',
        updated_at: '2026-09-25T16:00:00Z',
    } as unknown as Portfolio;

    const mockHistory: PortfolioPerformance[] = [
        {
            id: 'h1',
            portfolio_id: 'sys-port-1',
            date: '2026-09-24',
            total_equity: 10000,
            cash_balance: 10000,
            buying_power: 40000,
            created_at: '2026-09-24T20:00:00Z',
        },
        {
            id: 'h2',
            portfolio_id: 'sys-port-1',
            date: '2026-09-25',
            total_equity: 10100,
            cash_balance: 10100,
            buying_power: 40400,
            created_at: '2026-09-25T20:00:00Z',
        },
    ] as unknown as PortfolioPerformance[];

    const initialData = {
        portfolio: mockPortfolio,
        positions: [],
        history: mockHistory,
        trades: [],
    };

    beforeEach(() => {
        queryClient = new QueryClient({
            defaultOptions: {
                queries: {
                    retry: false,
                    gcTime: 0,
                    staleTime: 1000 * 60 * 5,
                },
            },
        });
        lastChartProps = null;
    });

    it('keeps page and chart mounted without triggering Suspense fallback when switching benchmarks', async () => {
        const spyDeferred = createDeferred<Record<string, BenchmarkDataPoint[]>>();
        const qqqDeferred = createDeferred<Record<string, BenchmarkDataPoint[]>>();

        const benchmarkFetchFn = vi.fn((tickers: string[]) => {
            if (tickers[0] === 'SPY') return spyDeferred.promise;
            if (tickers[0] === 'QQQ') return qqqDeferred.promise;
            return Promise.resolve({});
        });

        render(
            <QueryClientProvider client={queryClient}>
                <React.Suspense fallback={<div data-testid="page-reloading">Reloading...</div>}>
                    <PortfolioDetailPage
                        initialData={initialData}
                        fetchFn={vi.fn().mockResolvedValue(initialData)}
                        benchmarkFetchFn={benchmarkFetchFn}
                    />
                </React.Suspense>
            </QueryClientProvider>,
        );

        expect(screen.getByText('Current Positions')).toBeInTheDocument();
        expect(screen.getByTestId('performance-chart')).toBeInTheDocument();
        expect(benchmarkFetchFn).not.toHaveBeenCalled();

        const select = screen.getByLabelText(/Benchmark/i) as HTMLSelectElement;
        expect(select.value).toBe('');

        // Switch from None -> SPY while fetch is still in-flight
        fireEvent.change(select, { target: { value: 'SPY' } });

        await waitFor(() => {
            expect(benchmarkFetchFn).toHaveBeenCalledWith(['SPY'], '2026-09-24', '2026-09-25');
        });

        // Page MUST NOT suspend/reload while SPY is loading
        expect(screen.queryByTestId('page-reloading')).toBeNull();
        expect(screen.getByText('Current Positions')).toBeInTheDocument();
        expect(screen.getByTestId('performance-chart')).toBeInTheDocument();
        expect(lastChartProps.selectedBenchmark).toBe('');
        expect(lastChartProps.showPercentage).toBe(false);
        expect(lastChartProps.pendingBenchmark).toBe('SPY');

        // Resolve SPY fetch
        spyDeferred.resolve({
            SPY: [
                { date: '2026-09-24', price: 500 },
                { date: '2026-09-25', price: 505 },
            ],
        });

        await waitFor(() => {
            expect(lastChartProps.selectedBenchmark).toBe('SPY');
            expect(lastChartProps.showPercentage).toBe(true);
            expect(lastChartProps.pendingBenchmark).toBeUndefined();
            expect(lastChartProps.benchmarkData?.SPY).toHaveLength(2);
        });

        // Switch from SPY -> QQQ while fetch is still in-flight
        fireEvent.change(select, { target: { value: 'QQQ' } });

        await waitFor(() => {
            expect(benchmarkFetchFn).toHaveBeenCalledWith(['QQQ'], '2026-09-24', '2026-09-25');
        });

        // Page MUST NOT suspend/reload; previous settled SPY view stays intact until QQQ resolves
        expect(screen.queryByTestId('page-reloading')).toBeNull();
        expect(screen.getByText('Current Positions')).toBeInTheDocument();
        expect(lastChartProps.selectedBenchmark).toBe('SPY');
        expect(lastChartProps.showPercentage).toBe(true);
        expect(lastChartProps.pendingBenchmark).toBe('QQQ');

        // Resolve QQQ fetch
        qqqDeferred.resolve({
            QQQ: [
                { date: '2026-09-24', price: 450 },
                { date: '2026-09-25', price: 459 },
            ],
        });

        await waitFor(() => {
            expect(lastChartProps.selectedBenchmark).toBe('QQQ');
            expect(lastChartProps.showPercentage).toBe(true);
            expect(lastChartProps.pendingBenchmark).toBeUndefined();
            expect(lastChartProps.benchmarkData?.QQQ).toHaveLength(2);
        });

        // Switch back to None -> zero extra fetch, immediately clears benchmark
        const callCountBeforeNone = benchmarkFetchFn.mock.calls.length;
        fireEvent.change(select, { target: { value: '' } });

        await waitFor(() => {
            expect(lastChartProps.selectedBenchmark).toBe('');
            expect(lastChartProps.showPercentage).toBe(false);
            expect(lastChartProps.pendingBenchmark).toBeUndefined();
        });
        expect(benchmarkFetchFn).toHaveBeenCalledTimes(callCountBeforeNone);
    });

    it('clears loading state on empty {} response or fetch error without hanging', async () => {
        const benchmarkFetchFn = vi.fn((tickers: string[]) => {
            if (tickers[0] === 'GLD') {
                return Promise.reject(new Error('Network error'));
            }
            return Promise.resolve({});
        });

        render(
            <QueryClientProvider client={queryClient}>
                <React.Suspense fallback={<div data-testid="page-reloading">Reloading...</div>}>
                    <PortfolioDetailPage
                        initialData={initialData}
                        fetchFn={vi.fn().mockResolvedValue(initialData)}
                        benchmarkFetchFn={benchmarkFetchFn}
                    />
                </React.Suspense>
            </QueryClientProvider>,
        );

        const select = screen.getByLabelText(/Benchmark/i) as HTMLSelectElement;

        // Empty {} response -> must settle with pendingBenchmark undefined and no mislabeled benchmark
        fireEvent.change(select, { target: { value: 'TLT' } });
        await waitFor(() => {
            expect(benchmarkFetchFn).toHaveBeenCalledWith(['TLT'], '2026-09-24', '2026-09-25');
            expect(lastChartProps.pendingBenchmark).toBeUndefined();
            expect(lastChartProps.selectedBenchmark).toBe('');
            expect(lastChartProps.benchmarkError).toBeUndefined();
        });

        // Error response -> surfaces benchmarkError and clears pendingBenchmark
        fireEvent.change(select, { target: { value: 'GLD' } });
        await waitFor(() => {
            expect(lastChartProps.pendingBenchmark).toBeUndefined();
            expect(lastChartProps.benchmarkError).toBe('Failed to load GLD');
        });
    });
});
