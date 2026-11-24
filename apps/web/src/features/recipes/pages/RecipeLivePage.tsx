import { Badge, Card, PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useEffect, useMemo, useState } from 'react';
import {
    type BenchmarkDataPoint,
    BenchmarkSelector,
    getBenchmarkHistoryFn,
    PerformanceChart,
    usePortfolioBenchmark,
} from '~/features/portfolios';
import { activateRecipeTurboFn } from '../api/recipes-quota-api';
import { LiveRunTracesCard } from '../components/LiveRunTracesCard';
import { RecipePortfolioBlock } from '../components/RecipePortfolioBlock';
import { TurboButton } from '../components/TurboButton';
import type { LivePortfolioSnapshot, LiveStatusMeta, RecipeJobRecord } from '../types';
import { toLiveEquitySnapshots } from '../utils/live-studio-helpers';
import { formatTurboRemainingLabel, getNextLiveSlotLabel } from '../utils/market-hours';

type BenchmarkFetchFn = (
    tickers: string[],
    startDate: string,
    endDate: string,
) => Promise<Record<string, BenchmarkDataPoint[]>>;

const defaultBenchmarkFetchFn: BenchmarkFetchFn = (tickers, startDate, endDate) =>
    getBenchmarkHistoryFn({ data: { tickers, startDate, endDate } });

interface RecipeLivePageProps {
    recipeId: string;
    initialData: {
        portfolio: LivePortfolioSnapshot;
        recentLiveRuns: RecipeJobRecord[];
        liveMeta?: LiveStatusMeta;
    } | null;
    benchmarkFetchFn?: BenchmarkFetchFn;
}

interface LiveStatusHeaderProps {
    recipeId: string;
    isLiveEnabled: boolean;
    turboRemaining: string | null;
    nextSlotLabel: string;
    liveMeta?: LiveStatusMeta;
    turboExpiresAt: string | null;
    turboUsedToday: boolean;
    isActivatingTurbo: boolean;
    now: Date;
    onActivateTurbo: () => void;
}

function LiveStatusHeader({
    recipeId,
    isLiveEnabled,
    turboRemaining,
    nextSlotLabel,
    liveMeta,
    turboExpiresAt,
    turboUsedToday,
    isActivatingTurbo,
    now,
    onActivateTurbo,
}: LiveStatusHeaderProps) {
    return (
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-voxel-bevel-hi pb-4">
            <div className="flex items-center gap-3">
                <Link
                    to="/build"
                    search={{ recipeId }}
                    className="voxel-btn inline-flex items-center gap-2 px-3 py-1.5 text-sm font-bold border border-voxel-bevel-hi bg-voxel-surface text-voxel-ink hover:bg-voxel-elevated rounded-none"
                >
                    ← Edit Bot
                </Link>
                <div>
                    <h1 className="type-heading text-voxel-ink">Live Status</h1>
                    <span className="type-body text-voxel-muted">
                        Recipe ID: {recipeId.slice(0, 8)}
                    </span>
                </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
                {!isLiveEnabled ? (
                    <Badge variant="soft" colorScheme="neutral" size="sm">
                        Live: PAUSED
                    </Badge>
                ) : turboRemaining ? (
                    <Badge variant="solid" colorScheme="accent" size="sm" suppressHydrationWarning>
                        Turbo: {turboRemaining} (5m)
                    </Badge>
                ) : (
                    <Badge variant="soft" colorScheme="success" size="sm">
                        Live: ON (30m)
                    </Badge>
                )}
                <span className="type-body text-voxel-muted" suppressHydrationWarning>
                    {!isLiveEnabled
                        ? 'Next run: Paused'
                        : `Next run: ${turboRemaining ? 'within 5m (Turbo)' : nextSlotLabel}`}
                </span>
                {liveMeta?.isOwner && liveMeta?.isLive && (
                    <TurboButton
                        turboExpiresAt={turboExpiresAt}
                        turboUsedToday={turboUsedToday}
                        isActivating={isActivatingTurbo}
                        now={now}
                        onActivate={onActivateTurbo}
                    />
                )}
            </div>
        </div>
    );
}

interface LiveEquityBenchmarkSectionProps {
    equityCurve: { time: string; equity: number }[] | undefined;
    benchmarkFetchFn: BenchmarkFetchFn;
}

function LiveEquityBenchmarkSection({
    equityCurve,
    benchmarkFetchFn,
}: LiveEquityBenchmarkSectionProps) {
    const equitySnapshots = useMemo(() => toLiveEquitySnapshots(equityCurve), [equityCurve]);
    const rawStartDate = equitySnapshots[0]?.date.slice(0, 10) ?? '';
    const rawEndDate = equitySnapshots[equitySnapshots.length - 1]?.date.slice(0, 10) ?? '';
    const hasMultiDayHistory = Boolean(rawStartDate && rawEndDate && rawStartDate !== rawEndDate);

    const {
        selectedBenchmark,
        onBenchmarkChange,
        benchmarkData,
        settledBenchmark,
        pendingBenchmark,
        benchmarkError,
    } = usePortfolioBenchmark({
        startDate: hasMultiDayHistory ? rawStartDate : '',
        endDate: hasMultiDayHistory ? rawEndDate : '',
        benchmarkFetchFn,
        initialBenchmark: 'SPY',
    });

    return (
        <section className="flex flex-col gap-4 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-4 w-full">
                <SectionHeading>Portfolio Equity &amp; Benchmark</SectionHeading>
                {hasMultiDayHistory && (
                    <BenchmarkSelector selected={selectedBenchmark} onChange={onBenchmarkChange} />
                )}
            </div>
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
                    {!hasMultiDayHistory && (
                        <p className="text-xs font-normal text-voxel-muted">
                            Benchmark comparison begins on Day 2 once 2+ trading days of history are
                            recorded.
                        </p>
                    )}
                </div>
            ) : (
                <Card
                    variant="outlined"
                    padding="md"
                    className="text-center text-voxel-muted text-xs font-normal"
                >
                    No equity history available yet. Equity checkpoints are recorded after each live
                    turn.
                </Card>
            )}
        </section>
    );
}

export function RecipeLivePage({
    recipeId,
    initialData,
    benchmarkFetchFn = defaultBenchmarkFetchFn,
}: RecipeLivePageProps) {
    const [runPage, setRunPage] = useState(0);
    const [turboExpiresAt, setTurboExpiresAt] = useState<string | null>(
        () => initialData?.liveMeta?.turboExpiresAt ?? null,
    );
    const [turboUsedToday, setTurboUsedToday] = useState<boolean>(
        () => initialData?.liveMeta?.turboUsedToday ?? false,
    );
    const [isActivatingTurbo, setIsActivatingTurbo] = useState(false);
    const [turboError, setTurboError] = useState<string | null>(null);
    const [now, setNow] = useState<Date>(() => new Date());

    useEffect(() => {
        const timer = setInterval(() => setNow(new Date()), 15_000);
        return () => clearInterval(timer);
    }, []);

    const recentLiveRuns = initialData?.recentLiveRuns ?? [];
    const portfolio = initialData?.portfolio ?? null;
    const liveMeta = initialData?.liveMeta;
    const isLiveEnabled = liveMeta ? liveMeta.isLive : true;

    const totalRuns = recentLiveRuns.length;
    // Clamp: the list is fixed for the life of the page, but a stale index must
    // never address a job that is not there.
    const runPageIndex = totalRuns > 0 ? Math.min(runPage, totalRuns - 1) : 0;

    const hasPortfolio = portfolio !== null;
    const hasRuns = totalRuns > 0;

    const nextSlotLabel = getNextLiveSlotLabel(now);
    const turboRemaining = isLiveEnabled ? formatTurboRemainingLabel(turboExpiresAt, now) : null;

    const handleActivateTurbo = async () => {
        if (isActivatingTurbo) return;
        setIsActivatingTurbo(true);
        setTurboError(null);
        try {
            const res = await activateRecipeTurboFn({ data: { recipeId } });
            setTurboExpiresAt(res.turboExpiresAt);
            setTurboUsedToday(true);
        } catch (err) {
            setTurboError(err instanceof Error ? err.message : 'Failed activating Turbo mode');
        } finally {
            setIsActivatingTurbo(false);
        }
    };

    return (
        <PageLayout>
            <div className="flex flex-col gap-6">
                <LiveStatusHeader
                    recipeId={recipeId}
                    isLiveEnabled={isLiveEnabled}
                    turboRemaining={turboRemaining}
                    nextSlotLabel={nextSlotLabel}
                    liveMeta={liveMeta}
                    turboExpiresAt={turboExpiresAt}
                    turboUsedToday={turboUsedToday}
                    isActivatingTurbo={isActivatingTurbo}
                    now={now}
                    onActivateTurbo={handleActivateTurbo}
                />

                {turboError && (
                    <div
                        role="alert"
                        className="border border-danger bg-voxel-surface p-3 text-xs font-normal text-danger rounded-none"
                    >
                        {turboError}
                    </div>
                )}

                {hasPortfolio && (
                    <RecipePortfolioBlock
                        title="Live Paper Portfolio"
                        cash={portfolio.cash}
                        totalEquity={portfolio.total_equity}
                        openPositions={portfolio.open_positions}
                    />
                )}

                {hasPortfolio && (
                    <LiveEquityBenchmarkSection
                        equityCurve={portfolio.equity_curve}
                        benchmarkFetchFn={benchmarkFetchFn}
                    />
                )}

                {hasRuns && (
                    <LiveRunTracesCard
                        runs={recentLiveRuns}
                        pageIndex={runPageIndex}
                        onOlder={() => setRunPage(Math.min(runPageIndex + 1, totalRuns - 1))}
                        onNewer={() => setRunPage(Math.max(runPageIndex - 1, 0))}
                    />
                )}

                {!hasPortfolio && !hasRuns && (
                    <div className="voxel-trough bg-voxel-trough p-6 text-center">
                        <span className="text-xs font-normal text-voxel-muted">
                            No live runs yet. The first scheduled run will execute at the next
                            30-minute market-hours ET slot (09:30–16:00 ET).
                        </span>
                    </div>
                )}
            </div>
        </PageLayout>
    );
}
