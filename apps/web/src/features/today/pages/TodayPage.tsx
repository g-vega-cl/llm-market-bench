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

/** Thin skeleton placeholder for a dashboard card column */
function CardSkeleton({ rows = 4 }: { rows?: number }) {
    return (
        <div className="space-y-3 animate-pulse">
            <div className="h-4 bg-zinc-200 dark:bg-zinc-800 rounded w-1/3" />
            {Array.from({ length: rows }).map((_, i) => (
                <div
                    // biome-ignore lint/suspicious/noArrayIndexKey: skeleton placeholder
                    key={i}
                    className="h-16 bg-zinc-100 dark:bg-zinc-800/70 rounded-xl"
                />
            ))}
        </div>
    );
}

export function TodayPage({ initialData, fetchFn }: TodayPageProps) {
    const { data } = useSuspenseQuery({
        ...todayQueries.data({ fetchFn }),
        initialData,
        refetchInterval: 1000 * 60 * 5, // Auto-refetch every 5 minutes
    });

    // Check if everything is empty for today (excluding future events and macro stats)
    const isEmpty =
        !data.newsletters?.length &&
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
                <Suspense fallback={<CardSkeleton rows={3} />}>
                    <GlobalMacroStats macroStats={data.macroStats} />
                </Suspense>

                {/* Row 2 / Empty state */}
                {isEmpty ? (
                    <EmptyStateView
                        hasFutureEvents={!!data.futureEvents?.length}
                        futureEvents={data.futureEvents}
                    />
                ) : (
                    <div className="space-y-6 animate-slide-up">
                        {/* Row 2: 3-column grid — AgentInsights | NewsletterFeed | AI Feeling, then Market Execution full-width within the same grid */}
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
                            <Suspense fallback={<CardSkeleton rows={3} />}>
                                <AgentInsights memories={data.memories} />
                            </Suspense>
                            <Suspense fallback={<CardSkeleton rows={3} />}>
                                <NewsletterFeed
                                    newsletters={data.newsletters}
                                    newsSummary={data.marketFeeling?.news_summary}
                                    newsSummaryDate={data.marketFeeling?.formattedDate}
                                    newsSummaryTime={data.marketFeeling?.formattedTime}
                                />
                            </Suspense>
                            <Suspense fallback={<CardSkeleton rows={4} />}>
                                <AIFeelingCard
                                    marketFeeling={data.marketFeeling}
                                    trades={data.trades}
                                    isSentimentStale={data.isSentimentStale}
                                />
                            </Suspense>
                            <div className="lg:col-span-3">
                                <Suspense fallback={<CardSkeleton rows={4} />}>
                                    <TradeActivity
                                        trades={data.trades}
                                        decisions={data.decisions}
                                    />
                                </Suspense>
                            </div>
                        </div>

                        {/* Row 4: Future Catalysts — full width */}
                        <Suspense fallback={<CardSkeleton rows={2} />}>
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
                    <Suspense fallback={<CardSkeleton rows={2} />}>
                        <FutureCatalysts events={futureEvents as Memory[]} />
                    </Suspense>
                </div>
            )}
        </div>
    );
}
