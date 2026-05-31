import type { Memory } from '@llm-market-bench/database';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ComponentProps, Suspense } from 'react';
import ReactDOMServer from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { MarketOverviewPage } from '~/features/market-overview/pages/MarketOverviewPage';
import { MemoriesPage } from '~/features/memories/pages/MemoriesPage';
import { PortfoliosPage } from '~/features/portfolios/pages/PortfoliosPage';
import { ReasoningPage } from '~/features/reasoning/pages/ReasoningPage';
import { FutureCatalysts } from '~/features/today/components/FutureCatalysts';
import { MarketStatusHero } from '~/features/today/components/MarketStatusHero';
import { TodayPage } from '~/features/today/pages/TodayPage';
import { Route as HowItWorksRoute } from '~/routes/how-it-works';
import { assertHydrationSymmetry } from './hydration-test-helper';

// -------------------------------------------------------------
// Global Routing & Analytics Mocks
// -------------------------------------------------------------
vi.mock('@tanstack/react-router', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tanstack/react-router')>();
    return {
        ...actual,
        Link: ({
            children,
            to,
            href,
        }: {
            children: React.ReactNode;
            to?: string;
            href?: string;
        }) => <a href={to || href || '#'}>{children}</a>,
    };
});

vi.mock('@posthog/react', () => ({
    usePostHog: () => ({
        capture: vi.fn(),
        identify: vi.fn(),
    }),
}));

// Mock resize observer which might be triggered by chart components (d3/recharts)
class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
}
global.ResizeObserver = ResizeObserverMock;

// -------------------------------------------------------------
// TDD / Reproduction Mocks
// -------------------------------------------------------------
function BrokenMismatchComponent() {
    return (
        <div className={`container-${Math.random()}`}>
            <p>Value: {Math.random()}</p>
        </div>
    );
}

// -------------------------------------------------------------
// Page-Level Mock Payloads
// -------------------------------------------------------------
const mockTodayData = {
    newsletters: [
        {
            id: 'n1',
            newsletter_name: 'Market Brief',
            subject: 'Opening Bell Insights',
            content_summary: 'Brief overview of expectations.',
            received_at: '2026-05-30T12:00:00Z',
            sender: 'Briefing AI',
            status: 'PROCESSED' as const,
            importance_score: 80,
            primary_topic: 'Markets',
            actionable_insights: [],
            key_metrics: {},
            created_at: '2026-05-30T12:00:00Z',
            updated_at: '2026-05-30T12:00:00Z',
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
    decisions: [],
    memories: [
        {
            id: 'm1',
            content: 'Consensus shift to defensive posturing.',
            created_at: '2026-05-30T10:00:00Z',
            memory_type: 'LESSON_LEARNED' as const,
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
    futureEvents: [
        {
            id: 'fe1',
            content: 'US FOMC Interest Rate Decision and economic projections.',
            created_at: '2026-05-30T10:00:00Z',
            memory_type: 'MARKET_EVENT' as const,
            status: 'ACTIVE' as const,
            parent_id: null,
            relationship_type: null,
            relevance_score: 95,
            importance_score: 9,
            target_date: '2026-06-15',
            metadata: {
                importance_score: 9,
                future_date_note: 'June FOMC',
                event_time: '14:00 ET',
                tickers: ['SPY', 'QQQ', 'TLT'],
                scenario_analysis:
                    'Bullish scenario: 0.25% cut (65% probability) -> SPY +1.5%\nBearish scenario: Pause (35% probability) -> SPY -1.2%',
            },
        },
    ],
    marketFeeling: {
        id: 'f1',
        sentiment_label: 'Bullish',
        sentiment_emoji: '🚀',
        market_direction: 'BULLISH',
        confidence_score: 85,
        why_explanation: 'Macro indicators are positive and volumes support the run.',
        primary_concern: 'Fed rate cuts timeline.',
        created_at: '2026-05-30T11:00:00Z',
    },
    macroStats: [
        {
            ticker: 'SPY',
            name: 'S&P 500 ETF',
            price: 520.5,
            change: 1.25,
            changePercent: 0.24,
            direction: 'up' as const,
        },
    ],
    serverTime: '2026-05-30T12:00:00Z',
    isMarketOpen: true,
    isSentimentStale: false,
    todayDateString: '2026-05-30',
};

const mockMemories = [
    {
        id: 'm1',
        content: 'Consensus shift to defensive posturing.',
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
];

const mockReasoningLogs = {
    data: [
        {
            id: 'r1',
            task_type: 'MARKET_ANALYSIS',
            model_name: 'gemini-2.5-pro',
            prompt_raw: 'What is the macro outlook?',
            response_raw: 'Looks bullish.',
            created_at: '2026-05-30T12:00:00Z',
            prompt_tokens: 100,
            completion_tokens: 50,
            cost: 0.001,
            time_taken_ms: 1500,
        },
    ],
    nextCursor: null,
};

const mockPortfolios = [
    {
        id: 'p1',
        name: 'OpenAI Aggressive',
        owner_id: 'user1',
        created_at: '2026-05-30T12:00:00Z',
        updated_at: '2026-05-30T12:00:00Z',
        is_active: true,
        is_autoresearch: false,
    },
];

const mockComparisonData = {
    portfolios: [],
    startDate: '2026-05-25',
    endDate: '2026-05-30',
    benchmarkData: {},
};

const mockMarketOverview = {
    priceUpdates: [],
    sentiment: {
        id: 'f1',
        sentiment_label: 'Bullish',
        sentiment_emoji: '🚀',
        market_direction: 'BULLISH',
        confidence_score: 85,
        why_explanation: 'Strong performance',
        primary_concern: 'Inflation',
        created_at: '2026-05-30T12:00:00Z',
    },
    latestCorrelation: {
        id: 'c1',
        calculation_date: '2026-05-30',
        correlation_matrix: {
            SPY: { SPY: 1.0, TLT: -0.3 },
            TLT: { SPY: -0.3, TLT: 1.0 },
        },
        calculated_at: '2026-05-30T12:00:00Z',
    },
    uncorrelatedPairs: [],
};

// Helper to create a pristine QueryClient for page rendering
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

// -------------------------------------------------------------
// Comprehensive Sitemap Tests
// -------------------------------------------------------------
describe('SSR Hydration Symmetry Regression Suite', () => {
    describe('TDD / Mismatch Check', () => {
        it('should successfully detect text and prop hydration mismatches', () => {
            const errors = assertHydrationSymmetry(<BrokenMismatchComponent />);
            expect(errors.length).toBeGreaterThan(0);
            expect(
                errors.some((err) => {
                    const lower = err.toLowerCase();
                    return (
                        lower.includes("didn't match") ||
                        lower.includes('did not match') ||
                        lower.includes('mismatch') ||
                        lower.includes('hydration')
                    );
                }),
            ).toBe(true);
        });

        it('should hydrate flawlessly even if client-side toLocaleDateString has narrow non-breaking spaces', () => {
            const originalToLocaleDateString = Date.prototype.toLocaleDateString;
            let isHydration = false;

            // Spy on renderToString to set the hydration flag right after SSR completes
            const originalRender = ReactDOMServer.renderToString;
            const renderSpy = vi
                .spyOn(ReactDOMServer, 'renderToString')
                .mockImplementation((el) => {
                    isHydration = false;
                    const res = originalRender(el);
                    isHydration = true;
                    return res;
                });

            // Spy on toLocaleDateString to return narrow non-breaking spaces only during client hydration
            const toLocaleDateStringSpy = vi
                .spyOn(Date.prototype, 'toLocaleDateString')
                .mockImplementation(function (
                    this: Date,
                    ...args: Parameters<typeof Date.prototype.toLocaleDateString>
                ) {
                    const res = originalToLocaleDateString.apply(this, args);
                    if (isHydration) {
                        // Simulate modern browser locale formatting with narrow non-breaking spaces
                        return res.replace(/\s+/g, '\u202f');
                    }
                    return res;
                });

            try {
                const errors = assertHydrationSymmetry(
                    <FutureCatalysts events={mockTodayData.futureEvents as unknown as Memory[]} />,
                );
                // With whitespace normalization in place, this must hydrate flawlessly with zero errors!
                expect(errors).toEqual([]);
            } finally {
                renderSpy.mockRestore();
                toLocaleDateStringSpy.mockRestore();
            }
        });
    });

    describe('Sitemap Hydration Verification (All Pages)', () => {
        it('1. Today Index Page: hydrates flawlessly', () => {
            const errors = assertHydrationSymmetry(
                <QueryClientProvider client={createTestQueryClient()}>
                    <TodayPage
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
                </QueryClientProvider>,
            );
            expect(errors).toEqual([]);
        });

        it('2. How It Works Page: hydrates flawlessly', () => {
            const HowItWorksComponent = HowItWorksRoute.options.component as React.ComponentType;
            expect(HowItWorksComponent).toBeDefined();
            const errors = assertHydrationSymmetry(<HowItWorksComponent />);
            expect(errors).toEqual([]);
        });

        it('3. Memories Page: hydrates flawlessly', () => {
            const errors = assertHydrationSymmetry(
                <QueryClientProvider client={createTestQueryClient()}>
                    <MemoriesPage
                        initialMemories={
                            mockMemories as unknown as ComponentProps<
                                typeof MemoriesPage
                            >['initialMemories']
                        }
                        initialHasMore={false}
                        initialCursor={null}
                        fetchFn={
                            (async () => ({
                                data: [],
                                hasMore: false,
                                nextCursor: null,
                            })) as unknown as ComponentProps<typeof MemoriesPage>['fetchFn']
                        }
                    />
                </QueryClientProvider>,
            );
            expect(errors).toEqual([]);
        });

        it('4. Reasoning Logs Page: hydrates flawlessly', () => {
            const errors = assertHydrationSymmetry(
                <QueryClientProvider client={createTestQueryClient()}>
                    <Suspense fallback={<div>Loading...</div>}>
                        <ReasoningPage
                            fetchFn={
                                (async () => mockReasoningLogs) as unknown as ComponentProps<
                                    typeof ReasoningPage
                                >['fetchFn']
                            }
                        />
                    </Suspense>
                </QueryClientProvider>,
            );
            expect(errors).toEqual([]);
        });

        it('5. Portfolios Page: hydrates flawlessly', () => {
            const errors = assertHydrationSymmetry(
                <QueryClientProvider client={createTestQueryClient()}>
                    <Suspense fallback={<div>Loading...</div>}>
                        <PortfoliosPage
                            initialData={
                                mockPortfolios as unknown as ComponentProps<
                                    typeof PortfoliosPage
                                >['initialData']
                            }
                            fetchFn={
                                (async () => mockPortfolios) as unknown as ComponentProps<
                                    typeof PortfoliosPage
                                >['fetchFn']
                            }
                            comparisonFetchFn={
                                (async () => mockComparisonData) as unknown as ComponentProps<
                                    typeof PortfoliosPage
                                >['comparisonFetchFn']
                            }
                        />
                    </Suspense>
                </QueryClientProvider>,
            );
            expect(errors).toEqual([]);
        });

        it('6. Market Overview Page: hydrates flawlessly', () => {
            const errors = assertHydrationSymmetry(
                <QueryClientProvider client={createTestQueryClient()}>
                    <MarketOverviewPage
                        initialData={
                            mockMarketOverview as unknown as ComponentProps<
                                typeof MarketOverviewPage
                            >['initialData']
                        }
                        fetchFn={
                            (async () => mockMarketOverview) as unknown as ComponentProps<
                                typeof MarketOverviewPage
                            >['fetchFn']
                        }
                    />
                </QueryClientProvider>,
            );
            expect(errors).toEqual([]);
        });

        it('7. MarketStatusHero Component: hydrates flawlessly', () => {
            const errors = assertHydrationSymmetry(
                <MarketStatusHero
                    data={
                        mockTodayData as unknown as ComponentProps<typeof MarketStatusHero>['data']
                    }
                />,
            );
            expect(errors).toEqual([]);
        });
    });
});
