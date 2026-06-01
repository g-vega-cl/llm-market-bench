import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type * as React from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { TodayData } from '~/features/today/api/fetch-today-data';
import type { TodayHeroData } from '~/features/today/api/fetch-today-hero-data';
import { TodayPage } from './TodayPage';

// Mock TanStack Router's Link
vi.mock('@tanstack/react-router', () => ({
    Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
        <a href={to}>{children}</a>
    ),
}));

// Mock PostHog
vi.mock('~/lib/posthog-client', async (importOriginal) => {
    const actual = await importOriginal<typeof import('~/lib/posthog-client')>();
    return {
        ...actual,
        useAnalytics: () => ({
            capture: vi.fn(),
        }),
    };
});

const heroFixture: TodayHeroData = {
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
    } as unknown as TodayHeroData['marketFeeling'],
    isMarketOpen: true,
    isSentimentStale: false,
    todayDateString: 'Friday, May 29, 2026',
};

const emptyTodayData = {
    newsletters: [],
    trades: [],
    decisions: [],
    memories: [],
    priceUpdates: [],
    futureEvents: [],
    marketFeeling: heroFixture.marketFeeling,
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
                    hero={heroFixture}
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
                    hero={heroFixture}
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
});
