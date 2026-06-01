import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import React, { type ComponentProps } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { TodayHeroData } from '~/features/today/api/fetch-today-hero-data';
import * as dateUtils from '~/utils/date';
import { TodayPage } from './TodayPage';

// Mock date utils to spy on them
vi.mock('~/utils/date', async (importOriginal) => {
    const actual = await importOriginal<typeof import('~/utils/date')>();
    return {
        ...actual,
        formatEasternTime: vi.fn(actual.formatEasternTime),
        formatEasternDate: vi.fn(actual.formatEasternDate),
        formatEasternDateTime: vi.fn(actual.formatEasternDateTime),
        formatEasternShortTime: vi.fn(actual.formatEasternShortTime),
        formatEasternShortDate: vi.fn(actual.formatEasternShortDate),
    };
});

// Mock ResizeObserver
class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
}
global.ResizeObserver = ResizeObserverMock;

const mockTodayData = {
    newsletters: [
        {
            id: 'n1',
            newsletter_name: 'Market Brief',
            subject: 'Opening Bell Insights',
            content_summary: 'Brief overview',
            received_at: '2026-05-30T12:00:00Z',
            sender: 'Briefing AI',
            status: 'PROCESSED' as const,
            importance_score: 80,
            primary_topic: 'Markets',
            actionable_insights: [],
            key_metrics: {},
            created_at: '2026-05-30T12:00:00Z',
            updated_at: '2026-05-30T12:00:00Z',
            date: '2026-05-30T12:00:00Z',
        },
    ],
    trades: [
        {
            id: 't1',
            portfolio_id: 'p1',
            ticker: 'SPY',
            signal: 'BUY' as const,
            shares: 10,
            price: 520.0,
            reasoning: 'Strong bullish trend.',
            executed_at: '2026-05-30T13:45:00Z',
            portfolios: { owner_id: 'user1' },
            created_at: '2026-05-30T13:45:00Z',
        },
    ],
    decisions: [
        {
            id: 'd1',
            trade_id: 't1',
            status: 'EXECUTED' as const,
            created_at: '2026-05-30T13:44:00Z',
            reasoning: 'Trade logic',
            model_name: 'gemini-2.5-pro',
            confidence_score: 90,
            metadata: null,
            ticker: 'SPY',
        },
    ],
    memories: [
        {
            id: 'm1',
            content: 'Consensus shift.',
            created_at: '2026-05-30T10:00:00Z',
            memory_type: 'MARKET_EVENT' as const,
            status: 'ACTIVE' as const,
            parent_id: null,
            relationship_type: null,
            relevance_score: 90,
            importance_score: 85,
            target_date: null,
            metadata: { model_name: 'gemini-2.5-pro' },
        },
    ],
    priceUpdates: [],
    futureEvents: [],
    marketFeeling: {
        id: 'f1',
        sentiment_label: 'Bullish',
        sentiment_emoji: '🚀',
        market_direction: 'BULLISH',
        confidence_score: 85,
        why_explanation: 'Macro positive',
        primary_concern: 'Fed',
        created_at: '2026-05-30T11:00:00Z',
    },
    macroStats: [],
    serverTime: '2026-05-30T12:00:00Z',
    isMarketOpen: true,
    isSentimentStale: false,
    todayDateString: '2026-05-30',
};

function createTestQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
                gcTime: 0,
            },
        },
    });
}

describe('TodayPage Performance & Hydration Safety', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('should NOT call client-side temporal formatters during render (to avoid hydration mismatch)', async () => {
        const queryClient = createTestQueryClient();

        const heroFixture: TodayHeroData = {
            marketFeeling: mockTodayData.marketFeeling
                ? ({
                      ...mockTodayData.marketFeeling,
                      formattedTime: '06:00 AM ET',
                  } as unknown as TodayHeroData['marketFeeling'])
                : null,
            isMarketOpen: mockTodayData.isMarketOpen,
            isSentimentStale: mockTodayData.isSentimentStale,
            todayDateString: 'Friday, May 29, 2026',
        };

        render(
            <QueryClientProvider client={queryClient}>
                <React.Suspense fallback={<div>Loading...</div>}>
                    <TodayPage
                        hero={heroFixture}
                        initialData={
                            mockTodayData as unknown as ComponentProps<
                                typeof TodayPage
                            >['initialData']
                        }
                        fetchFn={async () =>
                            mockTodayData as unknown as ComponentProps<
                                typeof TodayPage
                            >['initialData']
                        }
                    />
                </React.Suspense>
            </QueryClientProvider>,
        );

        // Verify that no client-side date instantiations/formatting occurred during render loop
        expect(dateUtils.formatEasternTime).not.toHaveBeenCalled();
        expect(dateUtils.formatEasternDate).not.toHaveBeenCalled();
        expect(dateUtils.formatEasternDateTime).not.toHaveBeenCalled();
        expect(dateUtils.formatEasternShortTime).not.toHaveBeenCalled();
        expect(dateUtils.formatEasternShortDate).not.toHaveBeenCalled();
    });
});
