import type { Memory } from '@llm-market-bench/database';
import { EmptyState, PageLayout } from '@llm-market-bench/ui-design-system';
import { useSuspenseQuery } from '@tanstack/react-query';
import { lazy, Suspense } from 'react';
import type { TodayData } from '../api/fetch-today-data';
import { TodayStatusBar } from '../components/TodayStatusBar';

const AgentInsights = lazy(() =>
    import('../components/AgentInsights').then((m) => ({ default: m.AgentInsights })),
);
const AIFeelingCard = lazy(() =>
    import('../components/AIFeelingCard').then((m) => ({ default: m.AIFeelingCard })),
);
const FutureCatalysts = lazy(() =>
    import('../components/FutureCatalysts').then((m) => ({ default: m.FutureCatalysts })),
);
const GlobalMacroStats = lazy(() =>
    import('../components/GlobalMacroStats').then((m) => ({ default: m.GlobalMacroStats })),
);
const IntradayNewsWire = lazy(() =>
    import('../components/IntradayNewsWire').then((m) => ({ default: m.IntradayNewsWire })),
);
const NewsletterFeed = lazy(() =>
    import('../components/NewsletterFeed').then((m) => ({ default: m.NewsletterFeed })),
);
const TradeActivity = lazy(() =>
    import('../components/TradeActivity').then((m) => ({ default: m.TradeActivity })),
);

import { todayQueries } from '../queries/options';

interface TodayPageProps {
    initialData: TodayData;
    fetchFn: () => Promise<TodayData>;
}

export function TodayPage({ initialData, fetchFn }: TodayPageProps) {
    const { data } = useSuspenseQuery({
        ...todayQueries.data({ fetchFn }),
        initialData,
        initialDataUpdatedAt: 0,
        refetchInterval: 1000 * 60 * 5, // Auto-refetch every 5 minutes
    });

    // Check if everything is empty for today (excluding future events and macro stats)
    const isEmpty =
        !data.newsletters?.length &&
        !data.intradayNews?.length &&
        !data.trades?.length &&
        !data.decisions?.length &&
        !data.memories?.length &&
        !data.priceUpdates?.length;

    return (
        <>
            {/* Slim sticky status bar — replaces the full gradient hero */}
            <TodayStatusBar data={data} />

            {/* Dashboard body — no opaque bg so the dotted GlobalBackground shows through */}
            <PageLayout className="py-6 space-y-6" maxWidth="xl">
                {/* Row 1: Global Macro Stats — full width */}
                <Suspense fallback={null}>
                    <GlobalMacroStats
                        macroStats={data.macroStats}
                        lastUpdated={data.macroLastUpdated}
                    />
                </Suspense>

                {/* Row 2 / Empty state */}
                {isEmpty ? (
                    <EmptyStateView
                        hasFutureEvents={!!data.futureEvents?.length}
                        futureEvents={data.futureEvents}
                    />
                ) : (
                    <div className="space-y-6 animate-slide-up">
                        {/* Row 2: 3-column grid — AgentInsights | NewsletterFeed | AI Feeling */}
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
                            <Suspense fallback={null}>
                                <AgentInsights memories={data.memories} />
                            </Suspense>
                            <Suspense fallback={null}>
                                <NewsletterFeed
                                    newsletters={data.newsletters}
                                    newsSummary={data.marketFeeling?.news_summary}
                                    newsSummaryDate={data.marketFeeling?.formattedDate}
                                    newsSummaryTime={data.marketFeeling?.formattedTime}
                                />
                            </Suspense>
                            <Suspense fallback={null}>
                                <AIFeelingCard
                                    marketFeeling={data.marketFeeling}
                                    trades={data.trades}
                                    isSentimentStale={data.isSentimentStale}
                                />
                            </Suspense>
                            <div className="lg:col-span-3">
                                <Suspense fallback={null}>
                                    <IntradayNewsWire items={data.intradayNews} />
                                </Suspense>
                            </div>
                            <div className="lg:col-span-3">
                                <Suspense fallback={null}>
                                    <TradeActivity
                                        trades={data.trades}
                                        decisions={data.decisions}
                                    />
                                </Suspense>
                            </div>
                        </div>

                        {/* Row 4: Future Catalysts — full width */}
                        <Suspense fallback={null}>
                            <FutureCatalysts events={data.futureEvents as Memory[]} />
                        </Suspense>
                    </div>
                )}
            </PageLayout>
        </>
    );
}

function EmptyStateView({
    hasFutureEvents,
    futureEvents,
}: {
    hasFutureEvents: boolean;
    futureEvents: Memory[];
}) {
    return (
        <div className="animate-scale-in">
            <EmptyState
                emoji="🤖"
                title="AI agents are observing. Quiet before the market session."
                subtitle="First trade insights will update in real-time during market hours."
                actions={[
                    {
                        label: 'View Historical Performance',
                        href: '/memories',
                    },
                    {
                        label: 'How It Works',
                        href: '/how-it-works',
                        variant: 'outline',
                    },
                ]}
            />

            {hasFutureEvents && (
                <div className="pt-6 border-t border-zinc-200 dark:border-zinc-800 animate-slide-up animate-stagger-2">
                    <Suspense fallback={null}>
                        <FutureCatalysts events={futureEvents as Memory[]} />
                    </Suspense>
                </div>
            )}
        </div>
    );
}
