import type { Portfolio } from '@llm-market-bench/database';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type * as React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getSystemPortfolioSubtitle, PortfoliosPage } from './PortfoliosPage';

// Mock Tanstack Query's useSuspenseQuery and useQuery to return the data directly
let mockComparisonQueryState = {
    isFetched: true,
    isFetching: false,
    isPending: false,
    isPlaceholderData: false,
};
let mockComparisonData: unknown = null;

vi.mock('@tanstack/react-query', async (importOriginal) => {
    const original = await importOriginal<typeof import('@tanstack/react-query')>();
    const stubQuery = ({
        queryKey,
        initialData,
    }: {
        queryKey?: unknown[];
        initialData?: unknown;
    }) => {
        if (queryKey?.includes('comparison')) {
            return {
                data: mockComparisonData ||
                    initialData || {
                        portfolios: [],
                        startDate: '',
                        endDate: '',
                        benchmarkData: {},
                    },
                ...mockComparisonQueryState,
            };
        }
        return {
            data: initialData,
            isFetched: true,
            isFetching: false,
            isPending: false,
            isPlaceholderData: false,
        };
    };
    return {
        ...original,
        useSuspenseQuery: vi.fn().mockImplementation(stubQuery),
        useQuery: vi.fn().mockImplementation(stubQuery),
        keepPreviousData: original.keepPreviousData,
    };
});

// Mock Tanstack Router's Link
vi.mock('@tanstack/react-router', () => ({
    Link: ({
        children,
        to,
        className,
    }: {
        children: React.ReactNode;
        to: string;
        className?: string;
    }) => (
        <a href={to} className={className} data-testid="portfolio-link">
            {children}
        </a>
    ),
}));

// Mock PostHog
vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        capture: vi.fn(),
    }),
}));

// Mock sub-components
vi.mock('../components/BenchmarkSelector', () => ({
    BenchmarkSelector: () => <div data-testid="benchmark-selector">Mock BenchmarkSelector</div>,
}));

let lastComparisonChartProps: { isSettled?: boolean } | null = null;
vi.mock('../components/PortfolioComparisonChart', () => ({
    PortfolioComparisonChart: (props: { isSettled?: boolean }) => {
        lastComparisonChartProps = props;
        return <div data-testid="portfolio-comparison-chart">Mock Chart</div>;
    },
}));

const mockPortfolios = [
    {
        id: 'p1',
        owner_id: 'gemini-3-flash-preview',
        total_equity: 100000,
        cash_balance: 50000,
        buying_power: 100000,
        is_active: true,
        is_autoresearch: true,
        created_at: '2026-05-25T12:00:00.000Z',
        updated_at: '2026-05-25T12:00:00.000Z',
    },
    {
        id: 'p-sys',
        owner_id: 'sys-pead-drift',
        total_equity: 105000,
        cash_balance: 25000,
        buying_power: 50000,
        is_active: true,
        is_autoresearch: false,
        is_system: true,
        created_at: '2026-05-25T12:00:00.000Z',
        updated_at: '2026-05-25T12:00:00.000Z',
    },
    {
        id: 'p2',
        owner_id: 'gpt-4-retired',
        total_equity: 80000,
        cash_balance: 40000,
        buying_power: 80000,
        is_active: false,
        is_autoresearch: false,
        created_at: '2026-05-25T12:00:00.000Z',
        updated_at: '2026-05-25T12:00:00.000Z',
    },
] as unknown as (Portfolio & { is_active: boolean; is_autoresearch: boolean })[];

describe('PortfoliosPage 3-Block Boxel Layout & Card Heights', () => {
    beforeEach(() => {
        mockComparisonData = null;
        mockComparisonQueryState = {
            isFetched: true,
            isFetching: false,
            isPending: false,
            isPlaceholderData: false,
        };
        lastComparisonChartProps = null;
    });

    it('separates Active LLM Agents and Systematic Strategies into distinct blocks and moves Retired to /lab', async () => {
        const fetchFn = vi.fn().mockResolvedValue(mockPortfolios);
        const comparisonFetchFn = vi.fn().mockResolvedValue({
            portfolios: [],
            startDate: '',
            endDate: '',
            benchmarkData: {},
        });

        render(
            <PortfoliosPage
                initialData={mockPortfolios}
                fetchFn={fetchFn}
                comparisonFetchFn={comparisonFetchFn}
            />,
        );

        await waitFor(() => {
            expect(screen.getByTestId('portfolios-block-llm')).toBeInTheDocument();
            expect(screen.getByTestId('portfolios-block-systematic')).toBeInTheDocument();

            // Only the 2 active portfolios (1 LLM + 1 Systematic) are rendered as portfolio-link cards; retired is in /lab
            const links = screen.getAllByTestId('portfolio-link');
            expect(links.length).toBe(2);
            expect(screen.queryByText(/gpt 4 retired/i)).toBeNull();

            for (const link of links) {
                expect(link.className).toContain('h-full');
                const cardElement = link.firstChild as HTMLElement;
                expect(cardElement).toBeDefined();
                expect(cardElement.className).toContain('h-full');
                expect(cardElement.className).toContain('flex');
                expect(cardElement.className).toContain('flex-col');

                const metricsContainer = cardElement.querySelector('.mt-auto');
                expect(metricsContainer).not.toBeNull();
                expect(metricsContainer?.className).toContain('mt-auto');
                expect(metricsContainer?.className).toContain('gap-3');
            }
        });
    });

    it('resolves correct system portfolio subtitles', () => {
        expect(getSystemPortfolioSubtitle('sys-sector-ls-consensus')).toBe(
            'Consensus Sector Long/Short Dispersion',
        );
        expect(getSystemPortfolioSubtitle('sys-daily-spy-deepseek-v4-flash')).toBe(
            'Daily S&P 500 Intraday Trader (Profit Target Exit)',
        );
        expect(getSystemPortfolioSubtitle('sys-daily-spy-close-deepseek-v4-flash')).toBe(
            'Daily S&P 500 Close Trader (3:50 PM Exit)',
        );
        expect(getSystemPortfolioSubtitle('sys-daily-tlt-close-gpt-5.6-luna')).toBe(
            'Daily 20+ Year Treasury Bond Trader (3:50 PM Exit)',
        );
        expect(getSystemPortfolioSubtitle('sys-pead-drift')).toBe(
            'Post-Earnings Drift Systematic Momentum (SUE + Jev)',
        );
        expect(getSystemPortfolioSubtitle('sys-max-pain')).toBe(
            'Daily Options Max Pain 0DTE Pinning (Ni et al. + Jev)',
        );
        expect(getSystemPortfolioSubtitle('sys-sentiment-fader')).toBe(
            'Contrarian Options Sentiment & Put/Call Ratio Fader',
        );
        expect(getSystemPortfolioSubtitle('custom-model')).toBeUndefined();
    });

    it('renders "Last updated" text when last_updated_at is present on the portfolio', async () => {
        const portfoliosWithTimestamp = [
            {
                ...mockPortfolios[0],
                last_updated_at: '2026-09-29T19:56:32.000Z',
            },
        ] as unknown as (Portfolio & { is_active: boolean; is_autoresearch: boolean })[];

        const fetchFn = vi.fn().mockResolvedValue(portfoliosWithTimestamp);
        const comparisonFetchFn = vi.fn().mockResolvedValue({
            portfolios: [],
            startDate: '',
            endDate: '',
            benchmarkData: {},
        });

        render(
            <PortfoliosPage
                initialData={portfoliosWithTimestamp}
                fetchFn={fetchFn}
                comparisonFetchFn={comparisonFetchFn}
            />,
        );

        await waitFor(() => {
            expect(screen.getByText(/Last updated/i)).toBeInTheDocument();
        });
    });

    it('renders graceful voxel placeholder when active LLM agents list is empty', async () => {
        const fetchFn = vi.fn().mockResolvedValue([]);
        const comparisonFetchFn = vi.fn().mockResolvedValue({
            portfolios: [],
            startDate: '',
            endDate: '',
            benchmarkData: {},
        });

        render(
            <PortfoliosPage
                initialData={[]}
                fetchFn={fetchFn}
                comparisonFetchFn={comparisonFetchFn}
            />,
        );

        await waitFor(() => {
            expect(screen.getByText(/no active models currently available/i)).toBeInTheDocument();
        });
    });

    it('passes isSettled=true when queries are settled, and isSettled=false when unsettled', async () => {
        const today = new Date().toISOString().split('T')[0];
        const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];

        mockComparisonData = {
            portfolios: [
                {
                    portfolioId: 'p1',
                    ownerId: 'gemini-3-flash-preview',
                    performance: [
                        { date: yesterday, totalEquity: 95000, value: 0 },
                        { date: today, totalEquity: 100000, value: 5.26 },
                    ],
                },
            ],
            startDate: yesterday,
            endDate: today,
            benchmarkData: {},
        };
        mockComparisonQueryState = {
            isFetched: true,
            isFetching: false,
            isPending: false,
            isPlaceholderData: false,
        };
        const fetchFn = vi.fn().mockResolvedValue(mockPortfolios);
        const comparisonFetchFn = vi.fn().mockResolvedValue(mockComparisonData);

        const { rerender } = render(
            <PortfoliosPage
                initialData={mockPortfolios}
                fetchFn={fetchFn}
                comparisonFetchFn={comparisonFetchFn}
            />,
        );

        await waitFor(() => {
            expect(lastComparisonChartProps?.isSettled).toBe(true);
            expect(screen.getByText('+5.26%')).toBeInTheDocument();
        });

        // Set comparison query as fetching / unsettled
        mockComparisonQueryState = {
            isFetched: true,
            isFetching: true,
            isPending: false,
            isPlaceholderData: true,
        };

        rerender(
            <PortfoliosPage
                initialData={mockPortfolios}
                fetchFn={fetchFn}
                comparisonFetchFn={comparisonFetchFn}
            />,
        );

        await waitFor(() => {
            expect(lastComparisonChartProps?.isSettled).toBe(false);
            expect(screen.queryByText('+5.26%')).toBeNull();
        });
    });

    it('hydrates immediately from initialComparisonData and switches timeframes (7D, 30D, 90D, ALL) instantaneously from precomputed cache without loading placeholder', async () => {
        const now = new Date();
        const fmt = (daysAgo: number) =>
            new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - daysAgo))
                .toISOString()
                .split('T')[0];

        const initialComparisonData = {
            portfolios: [
                {
                    portfolioId: 'p1',
                    ownerId: 'gemini-3-flash-preview',
                    performance: [
                        { date: fmt(120), totalEquity: 80000, value: 0 },
                        { date: fmt(60), totalEquity: 90000, value: 12.5 },
                        { date: fmt(20), totalEquity: 95000, value: 18.75 },
                        { date: fmt(3), totalEquity: 100000, value: 25.0 },
                        { date: fmt(0), totalEquity: 110000, value: 37.5 },
                    ],
                },
                {
                    portfolioId: 'p-sys',
                    ownerId: 'sys-pead-drift',
                    performance: [
                        { date: fmt(120), totalEquity: 100000, value: 0 },
                        { date: fmt(60), totalEquity: 102000, value: 2.0 },
                        { date: fmt(20), totalEquity: 101000, value: 1.0 },
                        { date: fmt(3), totalEquity: 90000, value: -10.0 },
                        { date: fmt(0), totalEquity: 108000, value: 8.0 },
                    ],
                },
            ],
            startDate: fmt(120),
            endDate: fmt(0),
            benchmarkData: {
                SPY: [
                    { date: fmt(120), price: 500 },
                    { date: fmt(3), price: 520 },
                    { date: fmt(0), price: 530 },
                ],
            },
        };

        const fetchFn = vi.fn().mockResolvedValue(mockPortfolios);
        const comparisonFetchFn = vi.fn().mockResolvedValue(initialComparisonData);

        render(
            <PortfoliosPage
                initialData={mockPortfolios}
                initialComparisonData={initialComparisonData}
                fetchFn={fetchFn}
                comparisonFetchFn={comparisonFetchFn}
            />,
        );

        // Chart is mounted immediately on first render without "Loading performance comparison..."
        expect(screen.queryByText(/Loading performance comparison/i)).toBeNull();
        expect(screen.getByTestId('portfolio-comparison-chart')).toBeInTheDocument();

        // Click 7D timeframe button - in the last 7 days, p-sys went 90k -> 108k (+20%) vs p1 100k -> 110k (+10%)
        const btn7d = screen.getByRole('button', { name: '7D' });
        fireEvent.click(btn7d);

        await waitFor(() => {
            expect(screen.getByTestId('portfolio-comparison-chart')).toBeInTheDocument();
            const chartProps = lastComparisonChartProps as unknown as {
                timeframe?: string;
                data?: { portfolioId: string }[];
            };
            expect(chartProps?.timeframe).toBe('7d');
            expect(chartProps?.data?.[0]?.portfolioId).toBe('p-sys');
        });
    });
});
