import type {
    Portfolio,
    PortfolioPerformance,
    PositionWithReasoning,
    TradeWithReasoning,
} from '@llm-market-bench/database';
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
    positions: any[];
    history: any[];
    trades: any[];
}

interface PortfolioDetailPageProps {
    initialData: PortfolioDetailData;
    fetchFn: (portfolioId: string) => Promise<PortfolioDetailData>;
    benchmarkFetchFn: (
        tickers: string[],
        startDate: string,
        endDate: string,
    ) => Promise<Record<string, any[]>>;
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
        <div className="flex flex-col min-h-screen px-4 sm:px-6 md:px-12 py-8 md:py-12">
            <div className="flex flex-col w-full">
                <header className="mb-8 md:mb-12 flex flex-col md:flex-row md:items-end justify-between gap-4 md:gap-6">
                    <div>
                        <h1 className="text-2xl md:text-4xl font-bold text-zinc-900 mb-2 tracking-tight capitalize">
                            {portfolio.owner_id.replace(/-/g, ' ')}
                        </h1>
                        <p className="text-zinc-500 text-sm md:text-lg">
                            Portfolio analysis and performance timeline.
                        </p>
                    </div>
                    <div className="bg-zinc-50 border border-zinc-200 rounded-lg p-3 md:p-4 flex gap-4 md:gap-8">
                        <div>
                            <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">
                                Total Equity
                            </div>
                            <div className="text-xl md:text-2xl font-bold text-zinc-900">
                                $
                                {Number(portfolio.total_equity || 0).toLocaleString(undefined, {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                })}
                            </div>
                        </div>
                        <div>
                            <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">
                                Cash
                            </div>
                            <div className="text-xl md:text-2xl font-bold text-zinc-900">
                                $
                                {Number(portfolio.cash_balance).toLocaleString(undefined, {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2,
                                })}
                            </div>
                        </div>
                    </div>
                </header>

                <div className="flex flex-col space-y-12">
                    {/* Performance Chart */}
                    <section>
                        <div className="flex items-center justify-between mb-4">
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
                            <div className="mt-4 p-8 border border-dashed border-zinc-300 rounded-xl text-center text-zinc-500">
                                No performance history available yet. Performance is recorded daily.
                            </div>
                        )}
                    </section>

                    {/* Positions Table */}
                    <section>
                        <h3 className="text-xl font-bold text-zinc-900 mb-6">Current Positions</h3>
                        <PositionsTable positions={positions as any} />
                    </section>

                    {/* Recent Trades Table */}
                    <section>
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-xl font-bold text-zinc-900">Recent Trades</h3>
                            <span className="text-sm text-zinc-500 bg-zinc-100 px-3 py-1 rounded-full font-medium">
                                Audit Trail
                            </span>
                        </div>
                        <TradesTable trades={trades as any} />
                    </section>
                </div>
            </div>
        </div>
    );
}
