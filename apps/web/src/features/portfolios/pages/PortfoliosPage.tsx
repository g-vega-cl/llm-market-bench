import type { Portfolio } from '@llm-market-bench/database';
import {
    Badge,
    Card,
    MetricTile,
    PageLayout,
    SectionHeading,
    SubHeading,
} from '@llm-market-bench/ui-design-system';
import { useSuspenseQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import * as React from 'react';
import type { BenchmarkDataPoint, PortfolioPerformanceItem } from '../api/fetch-portfolios';
import { BenchmarkSelector } from '../components/BenchmarkSelector';
import { PortfolioComparisonChart } from '../components/PortfolioComparisonChart';
import { hasVerifier } from '../lib/config';
import { portfolioQueries } from '../queries/options';

type PortfolioWithActive = Portfolio & { is_active: boolean; is_autoresearch: boolean };

interface PortfoliosPageProps {
    initialData: PortfolioWithActive[];
    fetchFn: () => Promise<PortfolioWithActive[]>;
    comparisonFetchFn: (
        benchmark: string,
        maxDays: number,
    ) => Promise<{
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
    return (
        <Link
            key={portfolio.id}
            to="/portfolios/$portfolioId"
            params={{ portfolioId: portfolio.id }}
            className="block group"
        >
            <Card
                padding="md"
                variant="default"
                className={
                    deprecated
                        ? 'opacity-60 hover:opacity-80'
                        : 'shadow-md hover:shadow-md group-hover:border-zinc-300'
                }
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
                        variant="soft"
                        size="sm"
                        colorScheme={deprecated ? 'neutral' : 'success'}
                    >
                        {deprecated ? 'Retired' : 'Active'}
                    </Badge>
                </div>

                <div className="flex flex-wrap gap-2 mb-4">
                    {portfolio.is_autoresearch && !deprecated && (
                        <Badge variant="soft" size="xs" colorScheme="info">
                            Auto-Research
                        </Badge>
                    )}
                    {!hasVerifier(portfolio.owner_id) && !deprecated && (
                        <Badge variant="soft" size="xs" colorScheme="warning">
                            No Verifier
                        </Badge>
                    )}
                </div>

                <div className="space-y-4">
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
    const [comparisonInitialData, setComparisonInitialData] = React.useState<
        | {
              portfolios: PortfolioPerformanceItem[];
              startDate: string;
              endDate: string;
              benchmarkData: Record<string, BenchmarkDataPoint[]>;
          }
        | undefined
    >(undefined);

    React.useEffect(() => {
        comparisonFetchFn(selectedBenchmark, 90)
            .then(setComparisonInitialData)
            .catch(console.error);
    }, [selectedBenchmark, comparisonFetchFn]);

    const { data: comparisonData } = useSuspenseQuery({
        ...portfolioQueries.comparison({
            benchmark: selectedBenchmark,
            fetchFn: () => comparisonFetchFn(selectedBenchmark, 90),
        }),
        initialData: comparisonInitialData,
    });

    const active = data?.filter((p) => p.is_active !== false) ?? [];
    const deprecated = data?.filter((p) => p.is_active === false) ?? [];

    const hasComparison = comparisonData?.portfolios && comparisonData.portfolios.length > 0;

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
                        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6 w-full">
                            <div>
                                <SectionHeading gradient="success">
                                    Performance Comparison
                                </SectionHeading>
                                <p className="text-sm text-zinc-500 mt-1">
                                    Normalized percentage returns over the last 90 days
                                </p>
                            </div>
                            <BenchmarkSelector
                                selected={selectedBenchmark}
                                onChange={setSelectedBenchmark}
                            />
                        </div>
                        <PortfolioComparisonChart
                            key={selectedBenchmark}
                            data={comparisonData?.portfolios || []}
                            benchmarkData={comparisonData?.benchmarkData}
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
