import type { Portfolio } from '@llm-market-bench/database';
import {
    Badge,
    Button,
    Card,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { keepPreviousData, useQuery, useSuspenseQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import * as React from 'react';
import { isQuerySettled } from '~/lib/query-client';
import { formatEasternDateTime } from '~/utils/date';
import type { BenchmarkDataPoint, PortfolioPerformanceItem } from '../api/fetch-portfolios';
import { BenchmarkSelector } from '../components/BenchmarkSelector';
import { PortfolioComparisonChart } from '../components/PortfolioComparisonChart';
import { getPortfolioTrack, hasVerifier, isSystemPortfolio } from '../lib/config';
import { portfolioQueries } from '../queries/options';

type PortfolioWithActive = Portfolio & {
    is_active: boolean;
    is_autoresearch: boolean;
    is_system?: boolean;
};

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

const SYSTEM_PORTFOLIO_SUBTITLES: Record<string, string> = {
    'sys-future-forces': 'Multi-Horizon Thematic Forces & Catalysts (2–24 Months)',
    'sys-smid-quality-compounder': 'Quality & Momentum Small-to-Large Compounder (Zero-Ceiling)',
    'sys-pead-drift': 'Post-Earnings Drift Systematic Momentum (SUE + Jev)',
    'sys-max-pain': 'Daily Options Max Pain 0DTE Pinning (Ni et al. + Jev)',
    'sys-sentiment-fader': 'Contrarian Options Sentiment & Put/Call Ratio Fader',
    'sys-sector-ls-consensus': 'Consensus Sector Long/Short Dispersion',
    'sys-sector-ls-30d': '30-Day Consensus Sector Long/Short Dispersion',
    'sys-sector-ls-90d': '90-Day Consensus Sector Long/Short Dispersion',
    'sys-sector-uncorr-20d': '20-Day Uncorrelated Sector Momentum (Low-Beta Barbell)',
    'sys-sector-uncorr-7d': '7-Day Uncorrelated Sector Momentum (Weekly Rotation)',
    'sys-sector-naive-momentum': '20-Day Unconstrained Momentum (Top 2 Winners)',
    'sys-sector-mean-reversion': '7-Day Sector Mean Reversion (Oversold Bounce)',
};

export function getSystemPortfolioSubtitle(ownerId: string): string | undefined {
    if (SYSTEM_PORTFOLIO_SUBTITLES[ownerId]) {
        return SYSTEM_PORTFOLIO_SUBTITLES[ownerId];
    }
    if (ownerId.startsWith('sys-daily-tlt-close-')) {
        return 'Daily 20+ Year Treasury Bond Trader (3:50 PM Exit)';
    }
    if (ownerId.startsWith('sys-daily-spy-close-')) {
        return 'Daily S&P 500 Close Trader (3:50 PM Exit)';
    }
    if (ownerId.startsWith('sys-daily-spy-')) {
        return 'Daily S&P 500 Intraday Trader (Profit Target Exit)';
    }
    return undefined;
}

function PortfolioLastUpdated({ timestamp }: { timestamp?: string | null }) {
    if (!timestamp) return null;
    return (
        <div className="pt-2 border-t border-boxel-bevel-hi/50 flex items-center justify-between text-xs text-boxel-muted">
            <span>Last updated</span>
            <span className="font-mono text-boxel-muted">{formatEasternDateTime(timestamp)}</span>
        </div>
    );
}

function PortfolioBadges({
    portfolio,
    isSystem,
    track,
}: {
    portfolio: PortfolioWithActive;
    isSystem: boolean;
    track: ReturnType<typeof getPortfolioTrack>;
}) {
    return (
        <div className="flex flex-wrap gap-1.5">
            {isSystem && (
                <Badge variant="soft" size="xs" colorScheme="warning" showDot>
                    System
                </Badge>
            )}
            {portfolio.is_autoresearch && (
                <Badge variant="soft" size="xs" colorScheme="info" showDot>
                    Auto-Research
                </Badge>
            )}
            {track && (
                <Badge variant="soft" size="xs" colorScheme="accent">
                    Track: {track.trackLabel}
                </Badge>
            )}
            {!isSystem && !hasVerifier(portfolio.owner_id) && (
                <Badge variant="outline" size="xs" colorScheme="warning">
                    No Verifier
                </Badge>
            )}
        </div>
    );
}

function PortfolioCard({
    portfolio,
    todayPct,
}: {
    portfolio: PortfolioWithActive;
    todayPct?: number;
}) {
    const track = getPortfolioTrack(portfolio.owner_id);
    const isSystem = portfolio.is_system ?? isSystemPortfolio(portfolio.owner_id);
    const subtitle = getSystemPortfolioSubtitle(portfolio.owner_id);
    const totalEquity = Number(portfolio.total_equity ?? portfolio.cash_balance ?? 0);
    const buyingPower = Number(portfolio.buying_power ?? portfolio.cash_balance ?? 0);
    const cashBalance = Number(portfolio.cash_balance ?? 0);

    return (
        <Link
            key={portfolio.id}
            to="/portfolios/$portfolioId"
            params={{ portfolioId: portfolio.id }}
            className="block group h-full min-w-0"
        >
            <Card padding="md" isHoverable className="h-full flex flex-col gap-3">
                <div className="flex justify-between items-start gap-2">
                    <h3 className="text-sm font-bold capitalize text-boxel-ink group-hover:text-accent transition-colors">
                        {portfolio.owner_id.replace(/-/g, ' ')}
                    </h3>
                    <div className="flex items-center gap-1.5 shrink-0">
                        {todayPct !== undefined && (
                            <Badge
                                variant="solid"
                                size="sm"
                                colorScheme={todayPct >= 0 ? 'success' : 'danger'}
                            >
                                {todayPct >= 0 ? '+' : ''}
                                {todayPct.toFixed(2)}%
                            </Badge>
                        )}
                    </div>
                </div>

                {subtitle && <p className="text-xs font-normal text-boxel-muted">{subtitle}</p>}

                <PortfolioBadges portfolio={portfolio} isSystem={isSystem} track={track} />

                <div className="flex flex-col gap-3 mt-auto">
                    <div className="voxel-trough p-3 flex items-baseline justify-between gap-2">
                        <span className="text-xs font-normal uppercase tracking-wider text-boxel-muted">
                            Total Equity
                        </span>
                        <span className="text-sm font-bold font-mono text-boxel-ink tabular-nums">
                            $
                            {totalEquity.toLocaleString('en-US', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                            })}
                        </span>
                    </div>

                    <div className="voxel-trough px-3 py-2 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                        <div className="flex items-center gap-1.5">
                            <span className="text-boxel-muted uppercase font-sans font-normal">
                                Cash
                            </span>
                            <span className="text-boxel-ink font-bold tabular-nums">
                                $
                                {cashBalance.toLocaleString('en-US', {
                                    maximumFractionDigits: 0,
                                })}
                            </span>
                        </div>
                        <span className="text-boxel-bevel-hi">|</span>
                        <div className="flex items-center gap-1.5">
                            <span className="text-boxel-muted uppercase font-sans font-normal">
                                Buying Power
                            </span>
                            <span className="text-boxel-ink font-bold tabular-nums">
                                $
                                {buyingPower.toLocaleString('en-US', {
                                    maximumFractionDigits: 0,
                                })}
                            </span>
                        </div>
                    </div>

                    <PortfolioLastUpdated timestamp={portfolio.last_updated_at} />
                </div>
            </Card>
        </Link>
    );
}

export function PortfoliosPage({ initialData, fetchFn, comparisonFetchFn }: PortfoliosPageProps) {
    const listQuery = useSuspenseQuery({
        ...portfolioQueries.list({ fetchFn }),
        initialData,
    });
    const { data } = listQuery;

    const [selectedBenchmark, setSelectedBenchmark] = React.useState<string>('SPY');
    const [timeframe, setTimeframe] = React.useState<'7d' | '30d' | '90d' | 'all'>('90d');
    const [isPending, startTransition] = React.useTransition();

    const comparisonQuery = useQuery({
        ...portfolioQueries.comparison({
            fetchFn: () => comparisonFetchFn(),
        }),
        placeholderData: keepPreviousData,
    });
    const { data: comparisonData } = comparisonQuery;

    const isQueriesSettled = isQuerySettled([listQuery, comparisonQuery]);
    const isChartSettled = isQueriesSettled && !isPending;

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

        const getReturnPct = (p: { performance: { value: number }[] }) => {
            if (!p.performance || p.performance.length === 0) return -Infinity;
            const val = p.performance[p.performance.length - 1]?.value;
            return typeof val === 'number' && !Number.isNaN(val) ? val : -Infinity;
        };

        portfolios.sort((a, b) => {
            const aVal = getReturnPct(a);
            const bVal = getReturnPct(b);
            if (bVal !== aVal) return bVal - aVal;
            return a.ownerId.localeCompare(b.ownerId);
        });

        const benchmarkData: Record<string, BenchmarkDataPoint[]> = {};
        if (comparisonData.benchmarkData) {
            for (const [ticker, points] of Object.entries(comparisonData.benchmarkData)) {
                const filteredPoints = points.filter((p) => new Date(p.date) >= cutoffDate);
                benchmarkData[ticker] = filteredPoints;
            }
        }

        return { portfolios, benchmarkData };
    }, [comparisonData, timeframe]);

    const todayPctMap = React.useMemo(() => {
        const map = new Map<string, number>();
        if (!comparisonData?.portfolios) return map;
        for (const p of comparisonData.portfolios) {
            if (p.performance.length >= 2) {
                const len = p.performance.length;
                const last = p.performance[len - 1].totalEquity;
                const prev = p.performance[len - 2].totalEquity;
                const pct = prev > 0 ? ((last - prev) / prev) * 100 : 0;
                map.set(p.portfolioId, pct);
            }
        }
        return map;
    }, [comparisonData]);

    const active = data?.filter((p) => p.is_active !== false) ?? [];
    const activeLlm = active.filter((p) => !(p.is_system ?? isSystemPortfolio(p.owner_id)));
    const activeSystematic = active.filter((p) => p.is_system ?? isSystemPortfolio(p.owner_id));

    const hasComparison = processedComparisonData.portfolios?.some((p) => p.performance.length > 0);

    return (
        <div className="min-h-screen bg-boxel-canvas text-boxel-ink">
            <PageLayout maxWidth="xl" className="flex flex-col gap-8">
                <header className="pb-4 border-b-2 border-boxel-bevel-hi flex flex-col gap-1">
                    <SectionHeading gradient="electric">Agent Portfolios</SectionHeading>
                    <p className="text-boxel-muted text-sm">
                        Live equity curves, active LLM agents, and systematic strategies.
                    </p>
                </header>

                {/* Block 1: Performance Comparison Chart */}
                <section data-testid="portfolios-block-chart" className="flex flex-col gap-4">
                    <div className="flex flex-wrap items-center justify-between gap-4 w-full">
                        <div className="flex flex-col gap-1">
                            <SectionHeading gradient="success">
                                Performance Comparison
                            </SectionHeading>
                            <p className="text-xs text-boxel-muted">
                                Normalized percentage returns over{' '}
                                {timeframe === 'all'
                                    ? 'all available days'
                                    : `the last ${timeframe}`}
                            </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-3">
                            <div className="voxel-trough flex gap-1 p-1">
                                {(['7d', '30d', '90d', 'all'] as const).map((tf) => (
                                    <Button
                                        key={tf}
                                        variant={timeframe === tf ? 'solid' : 'ghost'}
                                        colorScheme={timeframe === tf ? 'accent' : 'neutral'}
                                        onClick={() => {
                                            startTransition(() => {
                                                setTimeframe(tf);
                                            });
                                        }}
                                        className="px-3 py-1 text-xs font-bold"
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
                    {hasComparison ? (
                        <PortfolioComparisonChart
                            data={processedComparisonData.portfolios}
                            benchmarkData={processedComparisonData.benchmarkData}
                            selectedBenchmark={selectedBenchmark}
                            timeframe={timeframe}
                            isSettled={isChartSettled}
                        />
                    ) : (
                        <div className="voxel-trough py-48 flex items-center justify-center text-xs text-boxel-muted border border-boxel-bevel-hi/40">
                            Loading performance comparison...
                        </div>
                    )}
                </section>

                {/* Block 2: Active LLM Agents */}
                <section data-testid="portfolios-block-llm" className="flex flex-col gap-4">
                    <div className="flex items-center justify-between gap-2 pb-2 border-b-2 border-boxel-bevel-hi">
                        <SectionHeading gradient="electric">Active LLM Agents</SectionHeading>
                        <Badge colorScheme="accent" variant="solid" size="xs">
                            {activeLlm.length} Models
                        </Badge>
                    </div>
                    {activeLlm.length > 0 ? (
                        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-6 items-stretch">
                            {activeLlm.map((portfolio) => (
                                <PortfolioCard
                                    key={portfolio.id}
                                    portfolio={portfolio}
                                    todayPct={
                                        isQueriesSettled ? todayPctMap.get(portfolio.id) : undefined
                                    }
                                />
                            ))}
                        </div>
                    ) : (
                        <div className="voxel-trough py-12 flex items-center justify-center text-xs text-boxel-muted border border-boxel-bevel-hi/40">
                            No active models currently available.
                        </div>
                    )}
                </section>

                {/* Block 3: Systematic Strategies */}
                {activeSystematic.length > 0 && (
                    <section
                        data-testid="portfolios-block-systematic"
                        className="flex flex-col gap-4"
                    >
                        <div className="flex items-center justify-between gap-2 pb-2 border-b-2 border-boxel-bevel-hi">
                            <SectionHeading gradient="catalyst">
                                Systematic Strategies
                            </SectionHeading>
                            <Badge colorScheme="warning" variant="soft" size="xs">
                                {activeSystematic.length} Rules
                            </Badge>
                        </div>
                        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-6 items-stretch">
                            {activeSystematic.map((portfolio) => (
                                <PortfolioCard
                                    key={portfolio.id}
                                    portfolio={portfolio}
                                    todayPct={
                                        isQueriesSettled ? todayPctMap.get(portfolio.id) : undefined
                                    }
                                />
                            ))}
                        </div>
                    </section>
                )}
            </PageLayout>
        </div>
    );
}
