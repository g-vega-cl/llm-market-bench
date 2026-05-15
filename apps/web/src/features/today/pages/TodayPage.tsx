import type {
    Decision,
    MarketDataCache,
    MarketFeeling,
    Memory,
    NewsletterSnapshot,
    Trade,
} from '@llm-market-bench/database';
import { EmptyState, PageLayout } from '@llm-market-bench/ui-design-system';
import { useSuspenseQuery } from '@tanstack/react-query';
import { AgentInsights } from '../components/AgentInsights';
import { FutureCatalysts } from '../components/FutureCatalysts';
import { MarketStatusHero } from '../components/MarketStatusHero';
import { NewsletterFeed } from '../components/NewsletterFeed';
import { TradeActivity } from '../components/TradeActivity';
import { todayQueries } from '../queries/options';

interface TodayData {
    newsletters: NewsletterSnapshot[];
    trades: (Trade & { portfolios: { owner_id: string } })[];
    decisions: Decision[];
    memories: Memory[];
    priceUpdates: MarketDataCache[];
    futureEvents: Memory[];
    marketFeeling: MarketFeeling | null;
}

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

    // Check if everything is empty for today (excluding future events)
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
                {isEmpty ? (
                    <EmptyStateView
                        hasFutureEvents={!!data.futureEvents?.length}
                        futureEvents={data.futureEvents}
                    />
                ) : (
                    <div className="space-y-24 animate-slide-up">
                        <AgentInsights memories={data.memories} />
                        <NewsletterFeed newsletters={data.newsletters} />
                        <TradeActivity trades={data.trades} decisions={data.decisions} />
                        <FutureCatalysts events={data.futureEvents} />
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
    const jokes = [
        {
            emoji: '🤖',
            title: 'AI is observing. Markets are sleeping.',
            subtitle: 'First trade incoming during market hours.',
        },
        {
            emoji: '📊',
            title: 'The algorithms are sharpening their models.',
            subtitle: 'Quiet before the storm.',
        },
        {
            emoji: '🧠',
            title: 'Neural networks are dreaming of electric sheep.',
            subtitle: 'And alpha signals.',
        },
        {
            emoji: '⚡',
            title: 'Charging the neural nets.',
            subtitle: 'Back during market hours with insights.',
        },
        { emoji: '🔮', title: 'Crystal ball is warming up.', subtitle: 'Predictions loading...' },
        {
            emoji: '💤',
            title: 'Agents are in power-saving mode.',
            subtitle: 'Wake up call during market hours.',
        },
    ];

    const randomJoke = jokes[Math.floor(Math.random() * jokes.length)];

    return (
        <div className="animate-scale-in">
            <EmptyState
                emoji={randomJoke.emoji}
                title={randomJoke.title}
                subtitle={randomJoke.subtitle}
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
                    <FutureCatalysts events={futureEvents} />
                </div>
            )}
        </div>
    );
}
