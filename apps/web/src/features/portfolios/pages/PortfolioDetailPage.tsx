import type {
    Portfolio,
    PortfolioPerformance,
    PositionWithReasoning,
    TradeWithReasoning,
} from '@llm-market-bench/database';
import {
    Badge,
    Card,
    MetricTile,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { usePostHog } from '@posthog/react';
import { useSuspenseQuery } from '@tanstack/react-query';
import * as React from 'react';
import type { BenchmarkDataPoint } from '../api/fetch-portfolios';
import { BenchmarkSelector } from '../components/BenchmarkSelector';
import { PerformanceChart } from '../components/PerformanceChart';
import { PositionsTable } from '../components/PositionsTable';
import { TradesTable } from '../components/TradesTable';
import { portfolioQueries } from '../queries/options';

interface PortfolioDetailData {
    portfolio: Portfolio;
    positions: PositionWithReasoning[];
    history: PortfolioPerformance[];
    trades: TradeWithReasoning[];
}

interface PortfolioDetailPageProps {
    initialData: PortfolioDetailData;
    fetchFn: (portfolioId: string) => Promise<PortfolioDetailData>;
    benchmarkFetchFn: (
        tickers: string[],
        startDate: string,
        endDate: string,
    ) => Promise<Record<string, BenchmarkDataPoint[]>>;
}

export function PortfolioDetailPage({
    initialData,
    fetchFn,
    benchmarkFetchFn,
}: PortfolioDetailPageProps) {
    const posthog = usePostHog();
    const [selectedBenchmark, setSelectedBenchmark] = React.useState<string>('');

    const { data } = useSuspenseQuery({
        ...portfolioQueries.detail({
            id: initialData.portfolio.id,
            fetchFn: () => fetchFn(initialData.portfolio.id),
        }),
        initialData,
    });

    const { portfolio, positions, history, trades } = data;

    const hasHistory = history && history.length > 0;
    const startDate = hasHistory ? history[0].date : '';
    const endDate = hasHistory ? history[history.length - 1].date : '';

    const { data: benchmarkData } = useSuspenseQuery(
        portfolioQueries.benchmarks.history({
            tickers: selectedBenchmark ? [selectedBenchmark] : [],
            startDate,
            endDate,
            fetchFn: () =>
                benchmarkFetchFn(selectedBenchmark ? [selectedBenchmark] : [], startDate, endDate),
        }),
    );

    React.useEffect(() => {
        posthog.capture('portfolio_viewed', {
            portfolio_id: portfolio.id,
            owner_id: portfolio.owner_id,
        });
    }, [portfolio.id, portfolio.owner_id, posthog]);

    if (!portfolio) {
        return <div>Portfolio not found</div>;
    }

    return (
        <div className="min-h-screen">
            <PageLayout className="px-4 sm:px-6 md:px-12 py-8 md:py-12" withPadding={false}>
                <header className="mb-8 md:mb-12 flex flex-col md:flex-row md:items-end justify-between gap-4 md:gap-6">
                    <div>
                        <SectionHeading gradient="electric">
                            {portfolio.owner_id.replace(/-/g, ' ')}
                        </SectionHeading>
                        <p className="text-zinc-500 text-sm md:text-lg">
                            Portfolio analysis and performance timeline.
                        </p>
                    </div>
                    <Card padding="md" className="flex gap-4 md:gap-8">
                        <MetricTile
                            icon="💰"
                            label="Total Equity"
                            value={`$${Number(portfolio.total_equity || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                        />
                        <MetricTile
                            icon="💵"
                            label="Cash"
                            value={`$${Number(portfolio.cash_balance).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                        />
                    </Card>
                </header>

                <div className="flex flex-col space-y-12">
                    {/* Performance Chart */}
                    <section>
                        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
                            <BenchmarkSelector
                                selected={selectedBenchmark}
                                onChange={setSelectedBenchmark}
                            />
                        </div>
                        <PerformanceChart
                            data={history || []}
                            benchmarkData={benchmarkData}
                            selectedBenchmark={selectedBenchmark}
                            showPercentage={!!selectedBenchmark}
                        />
                        {(!history || history.length === 0) && (
                            <Card
                                variant="outlined"
                                padding="md"
                                className="text-center text-zinc-500"
                            >
                                No performance history available yet. Performance is recorded daily.
                            </Card>
                        )}
                    </section>

                    {/* Positions Table */}
                    <section>
                        <SectionHeading gradient="electric">Current Positions</SectionHeading>
                        <PositionsTable positions={positions} />
                    </section>

                    {/* Recent Trades Table */}
                    <section>
                        <div className="flex items-center justify-between mb-6">
                            <SectionHeading gradient="success">Recent Trades</SectionHeading>
                            <Badge variant="soft" size="sm" colorScheme="neutral">
                                Audit Trail
                            </Badge>
                        </div>
                        <TradesTable trades={trades} />
                    </section>
                </div>
            </PageLayout>
        </div>
    );
}
