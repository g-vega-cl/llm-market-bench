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
import { GlobalMacroStats } from '../components/GlobalMacroStats';
import { MarketStatusHero } from '../components/MarketStatusHero';
import { NewsletterFeed } from '../components/NewsletterFeed';
import { TradeActivity } from '../components/TradeActivity';
import type { MacroStat } from '../lib/macro-tickers';
import { todayQueries } from '../queries/options';

interface TodayData {
    newsletters: NewsletterSnapshot[];
    trades: (Trade & { portfolios: { owner_id: string } })[];
    decisions: Decision[];
    memories: Memory[];
    priceUpdates: MarketDataCache[];
    futureEvents: Memory[];
    marketFeeling: MarketFeeling | null;
    macroStats: MacroStat[];
    serverTime?: string;
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
                <GlobalMacroStats macroStats={data.macroStats} />

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
                    <FutureCatalysts events={futureEvents} />
                </div>
            )}
        </div>
    );
}
