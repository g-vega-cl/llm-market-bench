import {
    Badge,
    Button,
    Card,
    MetricTile,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import {
    type BenchmarkDataPoint,
    BenchmarkSelector,
    PerformanceChart,
} from '~/features/portfolios';
import type { LiveEquitySnapshot } from '../utils/live-studio-helpers';
import type { OverviewMetricsSummary } from '../utils/overview-metrics';

export interface PerformanceOverviewBlockProps {
    metrics: OverviewMetricsSummary;
    equitySnapshots: LiveEquitySnapshot[];
    benchmarkData: Record<string, BenchmarkDataPoint[]> | undefined;
    selectedBenchmark: string;
    settledBenchmark: string | undefined;
    pendingBenchmark: string | undefined;
    benchmarkError: string | undefined;
    hasMultiDayHistory: boolean;
    isOwner: boolean;
    isLive: boolean;
    isRunningBacktest: boolean;
    isTogglingLive: boolean;
    onBenchmarkChange: (ticker: string) => void;
    onBacktest: () => void;
    onToggleLive: () => void;
}

function formatDollar(value: number): string {
    return `$${value.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    })}`;
}

export function formatSignedPct(value: number | null): string {
    if (value === null || !Number.isFinite(value)) return '—';
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function returnToneClass(value: number | null): string {
    if (value === null) return 'text-voxel-muted';
    return value >= 0 ? 'text-success' : 'text-danger';
}

function modeBadgeColor(mode: OverviewMetricsSummary['mode']): 'success' | 'accent' | 'neutral' {
    if (mode === 'live') return 'success';
    if (mode === 'backtest') return 'accent';
    return 'neutral';
}

function modeBadgeLabel(mode: OverviewMetricsSummary['mode']): string {
    if (mode === 'live') return 'LIVE PAPER';
    if (mode === 'backtest') return 'LATEST BACKTEST';
    return 'NO RUNS YET';
}

function OverviewKpiStrip({ metrics }: { metrics: OverviewMetricsSummary }) {
    const winRateLabel =
        metrics.winRatePct !== null
            ? `${metrics.winRatePct}% (${metrics.winningTradesCount}/${metrics.closedTradesCount})`
            : '—';

    return (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,11rem),1fr))] gap-4 items-stretch">
            <MetricTile
                label="Total Equity"
                value={
                    <span className="font-mono tabular-nums">
                        {formatDollar(metrics.totalEquity)}
                    </span>
                }
            />
            <MetricTile
                label="Net Return"
                value={
                    <span
                        className={`font-mono tabular-nums ${returnToneClass(metrics.netReturnPct)}`}
                    >
                        {formatSignedPct(metrics.netReturnPct)}
                    </span>
                }
            />
            <MetricTile
                label="Cash Available"
                value={<span className="font-mono tabular-nums">{formatDollar(metrics.cash)}</span>}
            />
            <MetricTile
                label="Win Rate"
                value={<span className="font-mono tabular-nums">{winRateLabel}</span>}
            />
            <MetricTile
                label="Open Positions"
                value={
                    <span className="font-mono tabular-nums">{metrics.openPositionsCount} / 4</span>
                }
            />
        </div>
    );
}

export function PerformanceOverviewBlock({
    metrics,
    equitySnapshots,
    benchmarkData,
    selectedBenchmark,
    settledBenchmark,
    pendingBenchmark,
    benchmarkError,
    hasMultiDayHistory,
    isOwner,
    isLive,
    isRunningBacktest,
    isTogglingLive,
    onBenchmarkChange,
    onBacktest,
    onToggleLive,
}: PerformanceOverviewBlockProps) {
    return (
        <Card
            padding="md"
            data-testid="bot-performance-block"
            className="flex flex-col gap-4 min-w-0"
        >
            <div className="flex flex-wrap items-center justify-between gap-4 border-b-2 border-voxel-bevel-hi pb-3 min-w-0">
                <div className="flex flex-wrap items-center gap-2 min-w-0">
                    <SectionHeading>Performance &amp; Equity</SectionHeading>
                    <Badge variant="soft" colorScheme={modeBadgeColor(metrics.mode)} size="xs">
                        {modeBadgeLabel(metrics.mode)}
                    </Badge>
                </div>
                {hasMultiDayHistory ? (
                    <BenchmarkSelector selected={selectedBenchmark} onChange={onBenchmarkChange} />
                ) : null}
            </div>

            <OverviewKpiStrip metrics={metrics} />

            {metrics.mode === 'backtest' && metrics.latestBacktestJobId ? (
                <div className="voxel-trough bg-voxel-trough p-3 flex flex-wrap items-center justify-between gap-2 min-w-0">
                    <span className="text-xs font-normal text-voxel-muted">
                        Showing latest 2-week backtest preview until Live (30m) turns begin.
                    </span>
                    <Link
                        to="/recipes/backtest/$jobId"
                        params={{ jobId: metrics.latestBacktestJobId }}
                        className="text-xs font-normal text-accent underline underline-offset-4 hover:text-accent-hover whitespace-nowrap"
                    >
                        Open full backtest →
                    </Link>
                </div>
            ) : null}

            {equitySnapshots.length > 0 ? (
                <div className="flex flex-col gap-2 min-w-0">
                    <PerformanceChart
                        data={equitySnapshots}
                        benchmarkData={benchmarkData}
                        selectedBenchmark={settledBenchmark}
                        pendingBenchmark={pendingBenchmark}
                        benchmarkError={benchmarkError}
                        showPercentage={Boolean(settledBenchmark)}
                    />
                    {!hasMultiDayHistory ? (
                        <p className="text-xs font-normal text-voxel-muted">
                            Benchmark comparison begins once 2+ trading days of equity history are
                            recorded.
                        </p>
                    ) : null}
                </div>
            ) : (
                <div className="voxel-trough bg-voxel-trough p-5 flex flex-wrap items-center justify-between gap-4 min-w-0">
                    <div className="flex flex-col gap-1 min-w-0">
                        <span className="text-sm font-bold text-voxel-ink">
                            No performance curve yet
                        </span>
                        <span className="text-xs font-normal text-voxel-muted">
                            Run a 2-week paper backtest or enable Live (30m) to record equity
                            checkpoints and benchmark comparisons.
                        </span>
                    </div>
                    {isOwner ? (
                        <div className="flex flex-wrap items-center gap-2 shrink-0">
                            <Button
                                size="sm"
                                variant="solid"
                                colorScheme="accent"
                                onClick={onBacktest}
                                isLoading={isRunningBacktest}
                            >
                                Run 2W Backtest
                            </Button>
                            {!isLive ? (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={onToggleLive}
                                    isLoading={isTogglingLive}
                                >
                                    Enable Live (30m)
                                </Button>
                            ) : null}
                        </div>
                    ) : null}
                </div>
            )}
        </Card>
    );
}
