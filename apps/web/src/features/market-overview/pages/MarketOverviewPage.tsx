import type { MarketFeeling } from '@llm-market-bench/database';
import {
    Badge,
    Button,
    Card,
    ConfidenceBar,
    EmptyState,
    HeroBackground,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { useSuspenseQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import * as React from 'react';
import type { CorrelationData, MarketOverviewData } from '../api/fetch-market-overview';
import { CorrelationHeatmap } from '../components/CorrelationHeatmap';
import { CorrelationHistoryExplorer } from '../components/CorrelationHistoryExplorer';
import { UncorrelatedPairs } from '../components/UncorrelatedPairs';
import { marketOverviewQueries } from '../queries/options';

interface MarketOverviewPageProps {
    initialData: MarketOverviewData;
    fetchFn: () => Promise<MarketOverviewData>;
}

export function MarketOverviewPage({ initialData, fetchFn }: MarketOverviewPageProps) {
    const { data } = useSuspenseQuery({
        ...marketOverviewQueries.data({ fetchFn }),
        initialData,
    });

    const [activeTab, setActiveTab] = React.useState<'current' | 'history'>('current');
    const [selectedPair, setSelectedPair] = React.useState<{
        tickerA: string;
        tickerB: string;
    } | null>(null);

    const handleSelectPairForHistory = (tickerA: string, tickerB: string) => {
        setSelectedPair({ tickerA, tickerB });
        setActiveTab('history');
    };

    return (
        <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
            <MarketOverviewHero marketFeeling={data.marketFeeling} />

            <PageLayout className="space-y-16 pb-24">
                {/* Modern Premium Sub-Navigation Tabs */}
                <div className="flex justify-center animate-slide-up">
                    <div className="flex gap-1.5 p-1.5 bg-white/50 dark:bg-zinc-900/50 backdrop-blur-md rounded-2xl border border-zinc-200/60 dark:border-zinc-800/80 shadow-md">
                        <Button
                            variant={activeTab === 'current' ? 'solid' : 'ghost'}
                            colorScheme={activeTab === 'current' ? 'accent' : 'neutral'}
                            onClick={() => setActiveTab('current')}
                            className="px-6 py-2.5 rounded-xl font-bold transition-all duration-200"
                        >
                            📊 Current Regime
                        </Button>
                        <Button
                            variant={activeTab === 'history' ? 'solid' : 'ghost'}
                            colorScheme={activeTab === 'history' ? 'accent' : 'neutral'}
                            onClick={() => setActiveTab('history')}
                            className="px-6 py-2.5 rounded-xl font-bold transition-all duration-200"
                        >
                            📈 Historical Progression
                        </Button>
                    </div>
                </div>

                {activeTab === 'current' ? (
                    data.correlationRun ? (
                        <div className="space-y-24 animate-slide-up">
                            <CorrelationHeatmap
                                correlationData={data.correlationData}
                                tickers={data.correlationRun.tickers}
                            />
                            <UncorrelatedPairs
                                correlationData={data.correlationData}
                                onSelectPair={handleSelectPairForHistory}
                            />
                            <SectorPerformanceGrid correlationData={data.correlationData} />
                        </div>
                    ) : (
                        <EmptyCorrelationState />
                    )
                ) : (
                    <CorrelationHistoryExplorer
                        tickers={data.correlationRun?.tickers ?? []}
                        initialPair={selectedPair}
                    />
                )}
            </PageLayout>
        </div>
    );
}

function MarketOverviewHero({ marketFeeling }: { marketFeeling: MarketFeeling | null }) {
    const now = new Date();
    const currentHour = now.getUTCHours();
    const currentMinutes = now.getUTCMinutes();
    const dayOfWeek = now.getUTCDay();

    const isMarketOpen =
        dayOfWeek >= 1 &&
        dayOfWeek <= 5 &&
        (currentHour > 13 || (currentHour === 13 && currentMinutes >= 30)) &&
        currentHour < 20;

    const formatTimeAgo = (dateStr: string | null | undefined): string => {
        if (!dateStr) return 'Unknown';
        const date = new Date(dateStr);
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
        });
    };

    const getDirectionColor = (direction: string | null | undefined): string => {
        switch (direction?.toUpperCase()) {
            case 'BULLISH':
                return 'text-neon-green-400';
            case 'BEARISH':
                return 'text-alert-red-400';
            default:
                return 'text-steel-400';
        }
    };

    const getConfidenceColorScheme = (
        score: number | null | undefined,
    ): 'accent' | 'success' | 'danger' | 'info' | 'warning' => {
        if (!score) return 'accent';
        if (score >= 70) return 'success';
        if (score >= 40) return 'warning';
        return 'danger';
    };

    const isStale = marketFeeling
        ? (() => {
              if (!marketFeeling.created_at) return true;
              const created = new Date(marketFeeling.created_at);
              const ageHours = (now.getTime() - created.getTime()) / 3600000;
              return ageHours > 4;
          })()
        : true;

    return (
        <HeroBackground gradient="electric">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                <div className="space-y-6 animate-slide-up">
                    <div className="flex flex-col sm:flex-row sm:items-center gap-4 flex-wrap">
                        <h1 className="text-5xl sm:text-6xl font-black text-white tracking-tighter text-display drop-shadow-lg">
                            MARKET OVERVIEW
                        </h1>
                        <div className="px-4 py-2 bg-white/20 backdrop-blur-sm text-white text-sm font-bold rounded-full border border-white/30 shadow-lg">
                            {now.toLocaleDateString('en-US', {
                                weekday: 'long',
                                month: 'long',
                                day: 'numeric',
                                year: 'numeric',
                            })}
                        </div>
                    </div>

                    <p className="text-lg text-electric-blue-100 font-light leading-relaxed max-w-2xl drop-shadow">
                        Real-time correlation matrix, uncorrelated asset pairs, and macro sentiment
                        analysis. Updated weekly on Sundays.
                    </p>

                    <div className="flex items-center gap-4">
                        <Badge
                            variant="soft"
                            colorScheme={isMarketOpen ? 'success' : 'neutral'}
                            className="gap-2"
                        >
                            <span
                                className={
                                    isMarketOpen ? 'live-dot' : 'w-2 h-2 rounded-full bg-steel-400'
                                }
                            />
                            {isMarketOpen ? 'MARKET OPEN' : 'MARKET CLOSED'}
                        </Badge>
                        <Link
                            to="/"
                            className="text-sm text-electric-blue-200 hover:text-white transition-colors underline underline-offset-2"
                        >
                            View AI Trading Activity →
                        </Link>
                    </div>
                </div>

                <div className="space-y-6 animate-slide-up animate-stagger-2">
                    <Card variant="glass" padding="md" className="rounded-3xl shadow-2xl">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-xs font-black text-electric-blue-200 uppercase tracking-widest">
                                How I'm Feeling
                            </span>
                            <div className="flex items-center gap-2">
                                <span className="text-2xl animate-float">
                                    {marketFeeling?.sentiment_emoji || '🤔'}
                                </span>
                                {isStale && marketFeeling && (
                                    <span
                                        className="text-xs px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded-full"
                                        title="Data is older than 4 hours"
                                    >
                                        ⚠
                                    </span>
                                )}
                            </div>
                        </div>

                        <div
                            className={`text-3xl sm:text-4xl font-black mb-3 text-display drop-shadow ${getDirectionColor(marketFeeling?.market_direction)}`}
                        >
                            {marketFeeling?.sentiment_label || 'Analyzing...'}
                        </div>

                        {marketFeeling?.market_direction && (
                            <div className="flex items-center gap-2 mb-4">
                                <Badge
                                    variant="soft"
                                    colorScheme={
                                        marketFeeling.market_direction === 'BULLISH'
                                            ? 'success'
                                            : marketFeeling.market_direction === 'BEARISH'
                                              ? 'danger'
                                              : 'neutral'
                                    }
                                    size="sm"
                                >
                                    {marketFeeling.market_direction}
                                </Badge>
                            </div>
                        )}

                        {marketFeeling?.confidence_score !== null &&
                            marketFeeling?.confidence_score !== undefined && (
                                <ConfidenceBar
                                    label="Confidence"
                                    value={marketFeeling.confidence_score}
                                    colorScheme={getConfidenceColorScheme(
                                        marketFeeling.confidence_score,
                                    )}
                                    textStyle="hero"
                                    className="mb-4"
                                />
                            )}

                        {marketFeeling?.why_explanation && (
                            <p className="text-sm text-electric-blue-100 leading-relaxed mb-4 italic">
                                "{marketFeeling.why_explanation}"
                            </p>
                        )}

                        {marketFeeling?.primary_concern && (
                            <div className="flex flex-wrap gap-2 mb-4">
                                <span className="text-[10px] text-electric-blue-300 uppercase tracking-wider">
                                    Primary Concern:
                                </span>
                                <span className="text-xs px-2 py-1 bg-white/5 rounded-lg text-electric-blue-100 border border-white/10">
                                    {marketFeeling.primary_concern}
                                </span>
                            </div>
                        )}

                        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-white/10">
                            <span className="text-[10px] text-electric-blue-300">
                                {marketFeeling?.created_at
                                    ? `Last analyzed: ${formatTimeAgo(marketFeeling.created_at)}`
                                    : 'Waiting for analysis...'}
                            </span>
                            {marketFeeling?.model_used && (
                                <span className="text-[10px] text-electric-blue-400/50">
                                    • {marketFeeling.model_used}
                                </span>
                            )}
                        </div>
                    </Card>
                </div>
            </div>
        </HeroBackground>
    );
}

function SectorPerformanceGrid({ correlationData }: { correlationData: CorrelationData[] }) {
    const tickerReturns = React.useMemo(() => {
        const returns: Record<string, { positive: boolean; ticker: string }[]> = {};

        // Group tickers by category based on naming conventions
        const categories: Record<string, string[]> = {
            'US Sectors': [
                'XLK',
                'SMH',
                'XLE',
                'XLF',
                'XLV',
                'XLY',
                'XLI',
                'XLB',
                'XLU',
                'XLRE',
                'XLC',
            ],
            'US Broad': ['QQQ', 'VIG', 'IWM', 'SPY'],
            'Intl Dev': ['EFA', 'EWJ', 'EWG', 'EWL', 'EWP', 'IFAD', 'BWX'],
            'Emerging Markets': ['EEM', 'MCHI', 'EWZ', 'EIDO', 'EPI'],
            Commodities: ['GLD', 'SLV', 'CPER', 'PDBC', 'USO'],
            Bonds: ['TLT', 'IEF', 'LQD', 'EMB', 'BNDX', 'IAGG'],
            'Real Assets': ['VNQ', 'ICF'],
            Crypto: ['BTCUSD', 'ETHUSD'],
            Volatility: ['VIXY', 'VIXM'],
            Dollar: ['UUP'],
        };

        for (const [category, categoryTickers] of Object.entries(categories)) {
            returns[category] = [];
            for (const ticker of categoryTickers) {
                // Find return for this ticker
                const corrEntry = correlationData.find((c) => c.ticker_a === ticker);
                const return90d = corrEntry?.returns_a_90d ?? 0;
                returns[category].push({ positive: return90d >= 0, ticker });
            }
        }

        return returns;
    }, [correlationData]);

    return (
        <section>
            <SectionHeading gradient="electric">
                Sector Performance (90-Day Trailing Returns)
            </SectionHeading>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Object.entries(tickerReturns).map(([category, items]) => (
                    <Card key={category} padding="sm">
                        <h3 className="text-sm font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-4">
                            {category}
                        </h3>
                        <div className="space-y-2">
                            {items.map(({ ticker, positive }) => (
                                <div key={ticker} className="flex items-center justify-between">
                                    <span className="font-mono text-sm text-zinc-700 dark:text-zinc-300">
                                        {ticker}
                                    </span>
                                    <span
                                        className={`text-sm font-semibold ${positive ? 'text-neon-green-500' : 'text-alert-red-400'}`}
                                    >
                                        {positive ? '↑' : '↓'}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </Card>
                ))}
            </div>
        </section>
    );
}

function EmptyCorrelationState() {
    return (
        <EmptyState
            emoji="📊"
            title="Correlation Matrix Pending"
            subtitle="The correlation matrix runs weekly on Sundays at 16:00 ET. Check back after the next scheduled run for uncorrelated asset pairs."
        />
    );
}
