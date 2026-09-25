import type { Portfolio, PortfolioPerformance } from '@llm-market-bench/database';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PortfolioDetailPage } from './PortfolioDetailPage';

vi.mock('@tanstack/react-router', () => ({
    // biome-ignore lint/suspicious/noExplicitAny: mock router Link
    Link: ({ children }: any) => <div>{children}</div>,
}));

vi.mock('@tanstack/react-query', async (importOriginal) => {
    const original = await importOriginal<typeof import('@tanstack/react-query')>();
    return {
        ...original,
        // biome-ignore lint/suspicious/noExplicitAny: mock useSuspenseQuery
        useSuspenseQuery: vi.fn(({ initialData }: any) => ({ data: initialData || {} })),
    };
});

vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        capture: vi.fn(),
    }),
}));

vi.mock('../components/StrategyExplainer', () => ({
    StrategyExplainer: () => <div data-testid="strategy-explainer">Explainer</div>,
}));

vi.mock('../components/PerformanceChart', () => ({
    PerformanceChart: () => <div data-testid="performance-chart">Chart</div>,
}));

vi.mock('../components/BenchmarkSelector', () => ({
    BenchmarkSelector: () => <div data-testid="benchmark-selector">Selector</div>,
}));

vi.mock('../components/PositionsTable', () => ({
    PositionsTable: () => <div data-testid="positions-table">Positions</div>,
}));

vi.mock('../components/TradesTable', () => ({
    TradesTable: () => <div data-testid="trades-table">Trades</div>,
}));

describe('PortfolioDetailPage Daily Move', () => {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
                gcTime: 0,
            },
        },
    });

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

    it('renders the Daily Move metric tile with positive percentage', () => {
        const initialData = {
            portfolio: mockPortfolio,
            positions: [],
            history: mockHistory,
            trades: [],
        };

        render(
            <QueryClientProvider client={queryClient}>
                <PortfolioDetailPage
                    initialData={initialData}
                    fetchFn={vi.fn().mockResolvedValue(initialData)}
                    benchmarkFetchFn={vi.fn().mockResolvedValue({})}
                />
            </QueryClientProvider>,
        );

        expect(screen.getByText('Daily Move')).toBeDefined();
        // (10100 - 10000) / 10000 * 100 = +1.00%
        expect(screen.getByText('+1.00%')).toBeDefined();
    });

    it('renders the Daily Move metric tile with negative percentage', () => {
        const negativeHistory: PortfolioPerformance[] = [
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
                total_equity: 9850,
                cash_balance: 9850,
                buying_power: 39400,
                created_at: '2026-09-25T20:00:00Z',
            },
        ] as unknown as PortfolioPerformance[];

        const initialData = {
            portfolio: mockPortfolio,
            positions: [],
            history: negativeHistory,
            trades: [],
        };

        render(
            <QueryClientProvider client={queryClient}>
                <PortfolioDetailPage
                    initialData={initialData}
                    fetchFn={vi.fn().mockResolvedValue(initialData)}
                    benchmarkFetchFn={vi.fn().mockResolvedValue({})}
                />
            </QueryClientProvider>,
        );

        expect(screen.getByText('Daily Move')).toBeDefined();
        // (9850 - 10000) / 10000 * 100 = -1.50%
        expect(screen.getByText('-1.50%')).toBeDefined();
    });
});
