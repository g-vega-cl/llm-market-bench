import type { Portfolio } from '@llm-market-bench/database';
import {
    Badge,
    Button,
    Card,
    MetricTile,
    PageLayout,
    SectionHeading,
    SubHeading,
} from '@llm-market-bench/ui-design-system';
import { keepPreviousData, useQuery, useSuspenseQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import * as React from 'react';
import type { BenchmarkDataPoint, PortfolioPerformanceItem } from '../api/fetch-portfolios';
import { BenchmarkSelector } from '../components/BenchmarkSelector';
import { PortfolioComparisonChart } from '../components/PortfolioComparisonChart';
import { getPortfolioTrack, hasVerifier } from '../lib/config';
import { portfolioQueries } from '../queries/options';

type PortfolioWithActive = Portfolio & { is_active: boolean; is_autoresearch: boolean };

interface PortfoliosPageProps {
    initialData: PortfolioWithActive[];
    fetchFn: () => Promise<PortfolioWithActive[]>;
    comparisonFetchFn: () => Promise<{
        portfolios: PortfolioPerformanceItem[];
        startDate: string;
        endDate: string;
        benchmarkData: Record<string, BenchmarkDataPoint[]>;
    }>;
}

function PortfolioCard({
    portfolio,
    deprecated = false,
}: {
    portfolio: PortfolioWithActive;
    deprecated?: boolean;
}) {
    const track = getPortfolioTrack(portfolio.owner_id);

    return (
        <Link
            key={portfolio.id}
            to="/portfolios/$portfolioId"
            params={{ portfolioId: portfolio.id }}
            className="block group h-full"
        >
            <Card
                padding="md"
                variant="glass"
                isHoverable={!deprecated}
                className={`h-full flex flex-col ${deprecated ? 'opacity-60 hover:opacity-80' : ''}`}
            >
                <div className="flex justify-between items-start mb-4">
                    <h3
                        className={`text-xl font-bold capitalize ${
                            deprecated ? 'text-zinc-500' : 'text-zinc-900 dark:text-white'
                        }`}
                    >
                        {portfolio.owner_id.replace(/-/g, ' ')}
                    </h3>
                    <Badge
                        variant="glass"
                        size="sm"
                        colorScheme={deprecated ? 'neutral' : 'success'}
                        showDot={!deprecated}
                    >
                        {deprecated ? 'Retired' : 'Active'}
                    </Badge>
                </div>

                <div className="flex flex-wrap gap-2 mb-4">
                    {portfolio.is_autoresearch && !deprecated && (
                        <Badge variant="glass" size="xs" colorScheme="info" showDot>
                            Auto-Research
                        </Badge>
                    )}
                    {track && !deprecated && (
                        <Badge variant="soft" size="xs" colorScheme="accent">
                            Track: {track.trackLabel}
                        </Badge>
                    )}
                    {!hasVerifier(portfolio.owner_id) && !deprecated && (
                        <Badge variant="glass" size="xs" colorScheme="warning">
                            No Verifier
                        </Badge>
                    )}
                </div>

                <div className="space-y-4 mt-auto">
                    <MetricTile
                        icon="💰"
                        label="Total Equity"
                        value={`$${Number(portfolio.total_equity || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                    />

                    <div className="grid grid-cols-2 gap-4 pt-4 border-t border-zinc-100 dark:border-zinc-800">
                        <MetricTile
                            icon="💵"
                            label="Cash"
                            value={`$${Number(portfolio.cash_balance).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                        />
                        <MetricTile
                            icon="📊"
                            label="Buying Power"
                            value={`$${Number(portfolio.buying_power || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                        />
                    </div>
                </div>
            </Card>
        </Link>
    );
}

export function PortfoliosPage({ initialData, fetchFn, comparisonFetchFn }: PortfoliosPageProps) {
    const { data } = useSuspenseQuery({
        ...portfolioQueries.list({ fetchFn }),
        initialData,
    });

    const [selectedBenchmark, setSelectedBenchmark] = React.useState<string>('SPY');
    const [timeframe, setTimeframe] = React.useState<'7d' | '30d' | '90d' | 'all'>('90d');
    const [_isPending, startTransition] = React.useTransition();

    const { data: comparisonData } = useQuery({
        ...portfolioQueries.comparison({
            fetchFn: () => comparisonFetchFn(),
        }),
        placeholderData: keepPreviousData,
    });

    const processedComparisonData = React.useMemo(() => {
        if (!comparisonData?.portfolios) return { portfolios: [], benchmarkData: {} };

        const now = new Date();
        const cutoffDate = (() => {
            if (timeframe === 'all') return new Date(0);
            const days = timeframe === '7d' ? 7 : timeframe === '30d' ? 30 : 90;
            return new Date(
                Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - days),
            );
        })();

        // Slice portfolios and re-normalize relative to first date in sliced window
        const portfolios = comparisonData.portfolios.map((portfolio) => {
            const filteredPerf = portfolio.performance.filter(
                (p) => new Date(p.date) >= cutoffDate,
            );
            if (filteredPerf.length === 0) {
                return {
                    portfolioId: portfolio.portfolioId,
                    ownerId: portfolio.ownerId,
                    performance: [],
                };
            }

            const firstEquity = filteredPerf[0].totalEquity;
            const performance = filteredPerf.map((p) => ({
                date: p.date,
                totalEquity: p.totalEquity,
                value: firstEquity > 0 ? ((p.totalEquity - firstEquity) / firstEquity) * 100 : 0,
            }));

            return {
                portfolioId: portfolio.portfolioId,
                ownerId: portfolio.ownerId,
                performance,
            };
        });

        // Slice benchmark price history
        const benchmarkData: Record<string, BenchmarkDataPoint[]> = {};
        if (comparisonData.benchmarkData) {
            for (const [ticker, points] of Object.entries(comparisonData.benchmarkData)) {
                const filteredPoints = points.filter((p) => new Date(p.date) >= cutoffDate);
                benchmarkData[ticker] = filteredPoints;
            }
        }

        return { portfolios, benchmarkData };
    }, [comparisonData, timeframe]);

    const active = data?.filter((p) => p.is_active !== false) ?? [];
    const deprecated = data?.filter((p) => p.is_active === false) ?? [];

    const hasComparison = processedComparisonData.portfolios?.some((p) => p.performance.length > 0);

    return (
        <div className="min-h-screen">
            <PageLayout>
                <header className="mb-12">
                    <SectionHeading gradient="electric">Agent Portfolios</SectionHeading>
                    <p className="text-zinc-500 dark:text-zinc-400 text-lg leading-relaxed mt-2">
                        Live performance and current holdings of our AI trading agents.
                    </p>
                </header>

                {/* Active agents */}
                <section className="mb-16">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {active.map((portfolio) => (
                            <PortfolioCard key={portfolio.id} portfolio={portfolio} />
                        ))}
                    </div>
                </section>

                {/* Performance Comparison Chart */}
                {hasComparison && (
                    <section className="mb-16">
                        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6 w-full">
                            <div>
                                <SectionHeading gradient="success">
                                    Performance Comparison
                                </SectionHeading>
                                <p className="text-sm text-zinc-500 mt-1">
                                    Normalized percentage returns over{' '}
                                    {timeframe === 'all'
                                        ? 'all available days'
                                        : `the last ${timeframe}`}
                                </p>
                            </div>
                            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
                                <div className="flex gap-1 p-1 bg-white/80 dark:bg-zinc-900/80 rounded-xl border border-zinc-200/50 dark:border-zinc-800/80 shadow-sm">
                                    {(['7d', '30d', '90d', 'all'] as const).map((tf) => (
                                        <Button
                                            key={tf}
                                            variant={timeframe === tf ? 'solid' : 'ghost'}
                                            colorScheme={timeframe === tf ? 'success' : 'neutral'}
                                            onClick={() => {
                                                startTransition(() => {
                                                    setTimeframe(tf);
                                                });
                                            }}
                                            className="px-3 py-1 rounded-lg text-xs font-bold transition-all duration-150"
                                        >
                                            {tf.toUpperCase()}
                                        </Button>
                                    ))}
                                </div>
                                <BenchmarkSelector
                                    selected={selectedBenchmark}
                                    onChange={(ticker) => {
                                        startTransition(() => {
                                            setSelectedBenchmark(ticker);
                                        });
                                    }}
                                />
                            </div>
                        </div>
                        <PortfolioComparisonChart
                            data={processedComparisonData.portfolios}
                            benchmarkData={processedComparisonData.benchmarkData}
                            selectedBenchmark={selectedBenchmark}
                        />
                    </section>
                )}

                {/* Deprecated / retired agents */}
                {deprecated.length > 0 && (
                    <section>
                        <SubHeading
                            uppercase
                            withDivider
                            rightElement={
                                <Badge variant="soft" size="sm" colorScheme="neutral">
                                    No longer trading
                                </Badge>
                            }
                        >
                            Retired Agents
                        </SubHeading>
                        <p className="text-sm text-zinc-400 mb-6">
                            These portfolios are preserved for historical reference. They no longer
                            receive new trade decisions but their full audit trail remains
                            accessible.
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {deprecated.map((portfolio) => (
                                <PortfolioCard
                                    key={portfolio.id}
                                    portfolio={portfolio}
                                    deprecated
                                />
                            ))}
                        </div>
                    </section>
                )}
            </PageLayout>
        </div>
    );
}
