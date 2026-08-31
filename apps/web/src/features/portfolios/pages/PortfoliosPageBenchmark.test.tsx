import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PortfoliosPage } from './PortfoliosPage';

vi.mock('@tanstack/react-router', () => ({
    // biome-ignore lint/suspicious/noExplicitAny: mock router Link
    Link: ({ children }: any) => <div>{children}</div>,
}));

// biome-ignore lint/suspicious/noExplicitAny: chart props holder
let lastChartProps: any = null;
vi.mock('../components/PortfolioComparisonChart', () => ({
    // biome-ignore lint/suspicious/noExplicitAny: mock chart props
    PortfolioComparisonChart: (props: any) => {
        lastChartProps = props;
        return <div data-testid="portfolio-comparison-chart">Mock Chart</div>;
    },
}));

describe('PortfoliosPage QQQ Benchmark Bug', () => {
    let queryClient: QueryClient;

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

    it('should pass QQQ benchmark data to the comparison chart when QQQ is selected', async () => {
        const today = new Date().toISOString().split('T')[0];
        const mockPortfolios = [
            {
                id: 'p1',
                owner_id: 'agent-1',
                total_equity: 100000,
                cash_balance: 50000,
                buying_power: 100000,
                is_active: true,
                is_autoresearch: true,
                created_at: `${today}T12:00:00.000Z`,
                updated_at: `${today}T12:00:00.000Z`,
            },
        ];

        const mockComparisonFetch = vi.fn().mockResolvedValue({
            portfolios: [
                {
                    portfolioId: 'p1',
                    ownerId: 'agent-1',
                    performance: [{ date: today, value: 0, totalEquity: 100000 }],
                },
            ],
            startDate: today,
            endDate: today,
            benchmarkData: {
                SPY: [{ date: today, price: 500 }],
                QQQ: [{ date: today, price: 400 }],
            },
        });

        render(
            <QueryClientProvider client={queryClient}>
                <PortfoliosPage
                    initialData={
                        mockPortfolios as unknown as Parameters<
                            typeof PortfoliosPage
                        >[0]['initialData']
                    }
                    fetchFn={vi.fn()}
                    comparisonFetchFn={mockComparisonFetch}
                />
            </QueryClientProvider>,
        );

        // Initially, SPY comparison data is fetched and passed
        await waitFor(() => {
            expect(lastChartProps).not.toBeNull();
            expect(lastChartProps.selectedBenchmark).toBe('SPY');
            expect(lastChartProps.benchmarkData?.SPY).toBeDefined();
        });

        // Now select QQQ as benchmark
        const select = screen.getByRole('combobox');
        fireEvent.change(select, { target: { value: 'QQQ' } });

        // Wait for the chart props to update with QQQ selected
        await waitFor(() => {
            expect(lastChartProps.selectedBenchmark).toBe('QQQ');
            expect(lastChartProps.benchmarkData?.QQQ).toBeDefined();
        });
    });

    it('should not remount the chart when the benchmark changes (no flash)', async () => {
        const today = new Date().toISOString().split('T')[0];
        render(
            <QueryClientProvider client={queryClient}>
                <PortfoliosPage
                    initialData={
                        [
                            {
                                id: 'p1',
                                owner_id: 'agent-1',
                                total_equity: 100000,
                                cash_balance: 50000,
                                buying_power: 100000,
                                is_active: true,
                                is_autoresearch: true,
                                created_at: `${today}T12:00:00.000Z`,
                                updated_at: `${today}T12:00:00.000Z`,
                            },
                            // biome-ignore lint/suspicious/noExplicitAny: mock data
                        ] as unknown as any
                    }
                    fetchFn={vi.fn()}
                    comparisonFetchFn={vi.fn().mockResolvedValue({
                        portfolios: [
                            {
                                portfolioId: 'p1',
                                ownerId: 'agent-1',
                                performance: [{ date: today, value: 0, totalEquity: 100000 }],
                            },
                        ],
                        startDate: today,
                        endDate: today,
                        benchmarkData: {
                            SPY: [{ date: today, price: 500 }],
                            QQQ: [{ date: today, price: 500 }],
                        },
                    })}
                />
            </QueryClientProvider>,
        );

        // Wait for the initial chart to appear
        const chartEl = await screen.findByTestId('portfolio-comparison-chart');

        // Capture the DOM node reference before the benchmark switch
        const nodeBeforeSwitch = chartEl;

        // Switch benchmark
        const select = screen.getByRole('combobox');
        fireEvent.change(select, { target: { value: 'QQQ' } });

        await waitFor(() => {
            expect(lastChartProps?.selectedBenchmark).toBe('QQQ');
        });

        // The DOM node must be the same object — no unmount/remount occurred
        const nodeAfterSwitch = screen.getByTestId('portfolio-comparison-chart');
        expect(nodeAfterSwitch).toBe(nodeBeforeSwitch);
    });

    it('should slice data client-side without re-fetching when timeframe filter is clicked', async () => {
        const mockPortfolios = [
            {
                id: 'p1',
                owner_id: 'agent-1',
                total_equity: 100000,
                cash_balance: 50000,
                buying_power: 100000,
                is_active: true,
                is_autoresearch: true,
                created_at: '2026-05-25T12:00:00.000Z',
                updated_at: '2026-05-25T12:00:00.000Z',
            },
        ];

        // Provide 100 days of history
        const performanceData = [];
        for (let i = 0; i < 100; i++) {
            const date = new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
            performanceData.push({ date, value: i, totalEquity: 100000 + i * 100 });
        }
        performanceData.reverse();

        const mockComparisonFetch = vi.fn().mockResolvedValue({
            portfolios: [
                {
                    portfolioId: 'p1',
                    ownerId: 'agent-1',
                    performance: performanceData,
                },
            ],
            startDate: performanceData[0].date,
            endDate: performanceData[performanceData.length - 1].date,
            benchmarkData: {
                SPY: performanceData.map((p) => ({ date: p.date, price: 500 })),
            },
        });

        render(
            <QueryClientProvider client={queryClient}>
                <PortfoliosPage
                    initialData={
                        mockPortfolios as unknown as Parameters<
                            typeof PortfoliosPage
                        >[0]['initialData']
                    }
                    fetchFn={vi.fn()}
                    comparisonFetchFn={mockComparisonFetch}
                />
            </QueryClientProvider>,
        );

        // Wait for initial load
        await waitFor(() => {
            expect(mockComparisonFetch).toHaveBeenCalledTimes(1);
            expect(lastChartProps).not.toBeNull();
            // Initially defaults to 90d, so should have 91 data points (including today)
            expect(lastChartProps.data[0].performance.length).toBe(91);
        });

        // Click the 30D timeframe button
        const btn30d = screen.getByRole('button', { name: '30D' });
        fireEvent.click(btn30d);

        // Verify that the chart data has been sliced to 31 data points (including today)
        await waitFor(() => {
            expect(lastChartProps.data[0].performance.length).toBe(31);
        });

        // Verify that no extra network request was triggered (fetch count remains 1)
        expect(mockComparisonFetch).toHaveBeenCalledTimes(1);
    });
});
