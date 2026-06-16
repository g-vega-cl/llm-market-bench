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

        const mockComparisonFetch = vi.fn().mockImplementation(async (benchmark, _maxDays) => {
            if (benchmark === 'SPY') {
                return {
                    portfolios: [
                        {
                            portfolioId: 'p1',
                            ownerId: 'agent-1',
                            performance: [{ date: '2026-06-01', value: 0, totalEquity: 100000 }],
                        },
                    ],
                    startDate: '2026-06-01',
                    endDate: '2026-06-01',
                    benchmarkData: {
                        SPY: [{ date: '2026-06-01', price: 500 }],
                    },
                };
            }
            if (benchmark === 'QQQ') {
                return {
                    portfolios: [
                        {
                            portfolioId: 'p1',
                            ownerId: 'agent-1',
                            performance: [{ date: '2026-06-01', value: 0, totalEquity: 100000 }],
                        },
                    ],
                    startDate: '2026-06-01',
                    endDate: '2026-06-01',
                    benchmarkData: {
                        QQQ: [{ date: '2026-06-01', price: 400 }],
                    },
                };
            }
            return { portfolios: [], startDate: '', endDate: '', benchmarkData: {} };
        });

        render(
            <QueryClientProvider client={queryClient}>
                <PortfoliosPage
                    // biome-ignore lint/suspicious/noExplicitAny: mock data
                    initialData={mockPortfolios as any}
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
                                created_at: '2026-05-25T12:00:00.000Z',
                                updated_at: '2026-05-25T12:00:00.000Z',
                            },
                            // biome-ignore lint/suspicious/noExplicitAny: mock data
                        ] as unknown as any
                    }
                    fetchFn={vi.fn()}
                    comparisonFetchFn={vi.fn().mockImplementation(async (benchmark) => ({
                        portfolios: [
                            {
                                portfolioId: 'p1',
                                ownerId: 'agent-1',
                                performance: [
                                    { date: '2026-06-01', value: 0, totalEquity: 100000 },
                                ],
                            },
                        ],
                        startDate: '2026-06-01',
                        endDate: '2026-06-01',
                        benchmarkData: {
                            [benchmark]: [{ date: '2026-06-01', price: 500 }],
                        },
                    }))}
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
});
