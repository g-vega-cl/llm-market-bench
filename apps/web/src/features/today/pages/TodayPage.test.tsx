import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type * as React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { TodayData } from '~/features/today/api/fetch-today-data';
import { TodayPage } from './TodayPage';

// Mock TanStack Router's Link
vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

// Mock PostHog
vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        capture: vi.fn(),
    }),
}));

const emptyTodayData = {
    newsletters: [],
    trades: [],
    decisions: [],
    memories: [],
    priceUpdates: [],
    futureEvents: [],
    marketFeeling: {
        id: 'mf1',
        sentiment_label: 'Bullish',
        sentiment_emoji: '🐂',
        market_direction: 'BULLISH',
        confidence_score: 75,
        why_explanation: 'Strong macroeconomic indicators and rising momentum.',
        primary_concern: 'Inflation risk',
        created_at: '2026-05-29T14:45:00Z',
        model_used: 'Gemini 3.5 Flash',
        formattedTime: '10:45 AM ET',
    },
    macroStats: [],
    serverTime: '2026-05-29T18:45:00Z',
    isMarketOpen: true,
    isSentimentStale: false,
    todayDateString: 'Friday, May 29, 2026',
} as unknown as TodayData;

describe('TodayPage UI stability & TDD performance checks', () => {
    let queryClient: QueryClient;

    beforeEach(() => {
        queryClient = new QueryClient({
            defaultOptions: {
                queries: {
                    retry: false,
                    gcTime: 0,
                },
            },
        });
        vi.clearAllMocks();
    });

    it('renders a professional static empty state description instead of dynamic jokes', () => {
        render(
            <QueryClientProvider client={queryClient}>
                <TodayPage
                    initialData={emptyTodayData}
                    fetchFn={vi.fn().mockResolvedValue(emptyTodayData)}
                />
            </QueryClientProvider>,
        );

        // Verify the stable, professional text is rendered
        expect(
            screen.getByText('AI agents are observing. Quiet before the market session.'),
        ).toBeInTheDocument();
        expect(
            screen.getByText('First trade insights will update in real-time during market hours.'),
        ).toBeInTheDocument();

        // Verify none of the old randomized jokes exist
        expect(
            screen.queryByText('Neural networks are dreaming of electric sheep.'),
        ).not.toBeInTheDocument();
        expect(screen.queryByText('Crystal ball is warming up.')).not.toBeInTheDocument();
    });

    it('renders the Eastern Time date in MarketStatusHero stable across environments', () => {
        // Set the mock clock to a known time so we can check stable Eastern Time rendering
        // 2026-05-29T18:45:00Z is 14:45:00 (2:45 PM) in Eastern Daylight Time (EDT)
        const mockNow = new Date('2026-05-29T18:45:00Z');
        vi.useFakeTimers();
        vi.setSystemTime(mockNow);

        render(
            <QueryClientProvider client={queryClient}>
                <TodayPage
                    initialData={emptyTodayData}
                    fetchFn={vi.fn().mockResolvedValue(emptyTodayData)}
                />
            </QueryClientProvider>,
        );

        // Verify it formats the date for ET: Friday, May 29, 2026 (irrespective of system local TZ)
        expect(screen.getByText(/Friday, May 29, 2026/)).toBeInTheDocument();

        // Verify the last analyzed time matches the exact ET formatted string: "Last analyzed: 10:45 AM ET"
        // 14:45:00Z from mock sentiment is 10:45 AM EDT (Eastern Daylight Time)
        expect(screen.getByText(/Last analyzed: 10:45 AM ET/)).toBeInTheDocument();

        vi.useRealTimers();
    });

    it('renders the AI News Synthesis card with news summary and the correct pre-formatted date', async () => {
        const testData = {
            ...emptyTodayData,
            newsletters: [
                {
                    id: 'nl-1',
                    subject: 'Test Subject',
                    content: 'Test newsletter content',
                    sender: 'test@example.com',
                    chunk_hash: 'abc123',
                    date: '2025-06-24',
                    ingested_at: '2025-06-24T09:00:00Z',
                    source_id: 'src-1',
                    formattedTime: '09:00 AM',
                },
            ],
            marketFeeling: {
                ...emptyTodayData.marketFeeling,
                news_summary: 'Overall market feeling is positive.',
                formattedDate: 'Thursday, May 28, 2026',
            },
        } as unknown as TodayData;

        render(
            <QueryClientProvider client={queryClient}>
                <TodayPage initialData={testData} fetchFn={vi.fn().mockResolvedValue(testData)} />
            </QueryClientProvider>,
        );

        // Verify the AI News Synthesis heading and content is rendered (wrapped in Suspense)
        expect(await screen.findByText('AI News Synthesis')).toBeInTheDocument();
        expect(screen.getByText('"Overall market feeling is positive."')).toBeInTheDocument();

        // Verify it displays the specific date and time passed to the synthesis card
        expect(screen.getByText('Thursday, May 28, 2026 • 10:45 AM ET')).toBeInTheDocument();
    });

    it('triggers background hydration fetch to expand trades from initial 5 to whole day', async () => {
        const initialTrades = [
            {
                id: 't1',
                ticker: 'SPY',
                signal: 'BUY',
                price: 500,
                executed_at: '2026-05-29T14:00:00Z',
                portfolios: { owner_id: 'Claude' },
                formattedTime: '10:00 AM',
            },
            {
                id: 't2',
                ticker: 'QQQ',
                signal: 'SELL',
                price: 400,
                executed_at: '2026-05-29T14:01:00Z',
                portfolios: { owner_id: 'Claude' },
                formattedTime: '10:01 AM',
            },
            {
                id: 't3',
                ticker: 'AAPL',
                signal: 'BUY',
                price: 180,
                executed_at: '2026-05-29T14:02:00Z',
                portfolios: { owner_id: 'Claude' },
                formattedTime: '10:02 AM',
            },
            {
                id: 't4',
                ticker: 'MSFT',
                signal: 'BUY',
                price: 410,
                executed_at: '2026-05-29T14:03:00Z',
                portfolios: { owner_id: 'Claude' },
                formattedTime: '10:03 AM',
            },
            {
                id: 't5',
                ticker: 'NVDA',
                signal: 'SELL',
                price: 900,
                executed_at: '2026-05-29T14:04:00Z',
                portfolios: { owner_id: 'Claude' },
                formattedTime: '10:04 AM',
            },
        ];
        const expandedTrades = [
            ...initialTrades,
            {
                id: 't6',
                ticker: 'GOOGL',
                signal: 'BUY',
                price: 170,
                executed_at: '2026-05-29T13:30:00Z',
                portfolios: { owner_id: 'Claude' },
                formattedTime: '09:30 AM',
            },
            {
                id: 't7',
                ticker: 'AMZN',
                signal: 'BUY',
                price: 185,
                executed_at: '2026-05-29T13:30:00Z',
                portfolios: { owner_id: 'Claude' },
                formattedTime: '09:30 AM',
            },
        ];

        const initialPayload = {
            ...emptyTodayData,
            trades: initialTrades,
        } as unknown as TodayData;

        const expandedPayload = {
            ...emptyTodayData,
            trades: expandedTrades,
        } as unknown as TodayData;

        const fetchFn = vi.fn().mockResolvedValue(expandedPayload);

        render(
            <QueryClientProvider client={queryClient}>
                <TodayPage initialData={initialPayload} fetchFn={fetchFn} />
            </QueryClientProvider>,
        );

        // Initially renders initial 5 trades
        expect(screen.getByText('NVDA')).toBeInTheDocument();

        // Background refetch should be called immediately on mount due to initialDataUpdatedAt: 0
        expect(fetchFn).toHaveBeenCalledTimes(1);

        // After fetchFn resolves, expanded trades like GOOGL become visible
        expect(await screen.findByText('GOOGL')).toBeInTheDocument();
        expect(screen.getByText('AMZN')).toBeInTheDocument();
    });
});
