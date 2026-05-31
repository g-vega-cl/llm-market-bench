import type { Memory } from '@llm-market-bench/database';
import { EmptyState, PageLayout } from '@llm-market-bench/ui-design-system';
import { useSuspenseQuery } from '@tanstack/react-query';
import { lazy, Suspense } from 'react';
import type { TodayData } from '../api/fetch-today-data';
import { MarketStatusHero } from '../components/MarketStatusHero';

const AgentInsights = lazy(() =>
    import('../components/AgentInsights').then((m) => ({ default: m.AgentInsights })),
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
        <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
            {/* Market Status Hero */}
            <MarketStatusHero data={data} />

            <PageLayout className="space-y-24 pb-24">
                {/* Global Macro, Bonds & Index Volatility Regime Stats */}
                <Suspense
                    fallback={
                        <div className="animate-pulse bg-zinc-200 dark:bg-zinc-800 h-32 rounded-2xl w-full" />
                    }
                >
                    <GlobalMacroStats macroStats={data.macroStats} />
                </Suspense>

                {isEmpty ? (
                    <EmptyStateView
                        hasFutureEvents={!!data.futureEvents?.length}
                        futureEvents={data.futureEvents}
                    />
                ) : (
                    <div className="space-y-24 animate-slide-up">
                        <Suspense
                            fallback={
                                <div className="animate-pulse bg-zinc-200 dark:bg-zinc-800 h-64 rounded-2xl w-full" />
                            }
                        >
                            <AgentInsights memories={data.memories} />
                        </Suspense>
                        <Suspense
                            fallback={
                                <div className="animate-pulse bg-zinc-200 dark:bg-zinc-800 h-64 rounded-2xl w-full" />
                            }
                        >
                            <NewsletterFeed newsletters={data.newsletters} />
                        </Suspense>
                        <Suspense
                            fallback={
                                <div className="animate-pulse bg-zinc-200 dark:bg-zinc-800 h-64 rounded-2xl w-full" />
                            }
                        >
                            <TradeActivity trades={data.trades} decisions={data.decisions} />
                        </Suspense>
                        <Suspense
                            fallback={
                                <div className="animate-pulse bg-zinc-200 dark:bg-zinc-800 h-64 rounded-2xl w-full" />
                            }
                        >
                            <FutureCatalysts events={data.futureEvents as Memory[]} />
                        </Suspense>
                    </div>
                )}
            </PageLayout>
        </div>
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
                <div className="pt-12 border-t border-zinc-200 dark:border-zinc-800 animate-slide-up animate-stagger-2">
                    <Suspense
                        fallback={
                            <div className="animate-pulse bg-zinc-200 dark:bg-zinc-800 h-64 rounded-2xl w-full" />
                        }
                    >
                        <FutureCatalysts events={futureEvents as Memory[]} />
                    </Suspense>
                </div>
            )}
        </div>
    );
}
