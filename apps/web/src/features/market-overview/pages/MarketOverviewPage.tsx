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
        refetchOnMount: 'always',
    });

    const [activeTab, setActiveTab] = React.useState<'current' | 'history'>('current');
    const [selectedPair, setSelectedPair] = React.useState<{
        tickerA: string;
        tickerB: string;
    } | null>(null);
    const [timeframe, setTimeframe] = React.useState<'7d' | '30d' | '60d' | '90d'>('90d');

    const mappedCorrelationData = React.useMemo(() => {
        return (data?.correlationData || []).map((d) => {
            if (timeframe === '7d') {
                return {
                    ...d,
                    pearson_corr: d.pearson_corr_7d ?? null,
                    spearman_corr: d.spearman_corr_7d ?? null,
                    returns_a_90d: d.returns_a_7d ?? null,
                    returns_b_90d: d.returns_b_7d ?? null,
                };
            }
            if (timeframe === '30d') {
                return {
                    ...d,
                    pearson_corr: d.pearson_corr_30d ?? null,
                    spearman_corr: d.spearman_corr_30d ?? null,
                    returns_a_90d: d.returns_a_30d ?? null,
                    returns_b_90d: d.returns_b_30d ?? null,
                };
            }
            if (timeframe === '60d') {
                return {
                    ...d,
                    pearson_corr: d.pearson_corr_60d ?? null,
                    spearman_corr: d.spearman_corr_60d ?? null,
                    returns_a_90d: d.returns_a_60d ?? null,
                    returns_b_90d: d.returns_b_60d ?? null,
                };
            }
            return d;
        });
    }, [data.correlationData, timeframe]);

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
                        <div className="space-y-16 animate-slide-up">
                            {/* Timeframe Selector Button Group */}
                            <div className="flex flex-col items-center gap-4">
                                <div className="flex gap-1 p-1 bg-white/80 dark:bg-zinc-900/80 rounded-xl border border-zinc-200/50 dark:border-zinc-800/80 shadow-sm">
                                    {(['7d', '30d', '60d', '90d'] as const).map((tf) => (
                                        <Button
                                            key={tf}
                                            variant={timeframe === tf ? 'solid' : 'ghost'}
                                            colorScheme={timeframe === tf ? 'accent' : 'neutral'}
                                            onClick={() => setTimeframe(tf)}
                                            className="px-4 py-1.5 rounded-lg text-xs font-bold transition-all duration-150"
                                        >
                                            {tf.toUpperCase()}
                                        </Button>
                                    ))}
                                </div>
                                {timeframe === '7d' && (
                                    <div className="max-w-3xl p-4 bg-amber-500/10 border border-amber-500/20 rounded-2xl flex items-start gap-3 text-amber-600 dark:text-amber-400 animate-slide-up">
                                        <span className="text-lg">⚠️</span>
                                        <div className="text-left text-xs leading-relaxed">
                                            <span className="font-bold block mb-0.5">
                                                7-Day Correlation Disclaimer:
                                            </span>
                                            Pearson and Spearman correlations calculated over 7 days
                                            (approx. 5 trading days) are highly sensitive to
                                            short-term price movements and can exhibit significant
                                            noise and volatility. Use with caution for structural
                                            diversification decisions.
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="space-y-24">
                                <CorrelationHeatmap
                                    correlationData={mappedCorrelationData}
                                    tickers={data.correlationRun.tickers}
                                />
                                <UncorrelatedPairs
                                    correlationData={mappedCorrelationData}
                                    onSelectPair={handleSelectPairForHistory}
                                    timeframe={timeframe}
                                />
                                <SectorPerformanceGrid
                                    correlationData={mappedCorrelationData}
                                    timeframe={timeframe}
                                />
                            </div>
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

    const formatEasternTime = (dateStr: string | null | undefined): string => {
        if (!dateStr) return 'Unknown';
        const date = new Date(dateStr);
        return `${date.toLocaleDateString('en-US', {
            timeZone: 'America/New_York',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
        })} ET`;
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
                        <Badge variant="outline" colorScheme="neutral">
                            {now.toLocaleDateString('en-US', {
                                timeZone: 'America/New_York',
                                weekday: 'long',
                                month: 'long',
                                day: 'numeric',
                                year: 'numeric',
                            })}
                        </Badge>
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
                                    ? `Last analyzed: ${formatEasternTime(marketFeeling.created_at)}`
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

function SectorPerformanceGrid({
    correlationData,
    timeframe = '90d',
}: {
    correlationData: CorrelationData[];
    timeframe?: '7d' | '30d' | '60d' | '90d';
}) {
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
            'Emerging Markets': ['EEM', 'MCHI', 'EWZ', 'EIDO', 'EPI', 'EWY'],
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

    const displayTimeframeName =
        timeframe === '7d'
            ? '7-Day'
            : timeframe === '30d'
              ? '30-Day'
              : timeframe === '60d'
                ? '60-Day'
                : '90-Day';

    return (
        <section>
            <SectionHeading gradient="electric">
                Sector Performance ({displayTimeframeName} Trailing Returns)
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
