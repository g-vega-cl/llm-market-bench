import { type AtmospherePhase, Card } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useMemo } from 'react';
import {
    type BenchmarkDataPoint,
    getBenchmarkHistoryFn,
    usePortfolioBenchmark,
} from '~/features/portfolios';
import { BotSceneShell } from '../components/BotSceneShell';
import { ClosedTradesSection } from '../components/ClosedTradesSection';
import { LiveSwitchConfirmation } from '../components/LiveSwitchConfirmation';
import { OverviewBottomSection } from '../components/OverviewBottomSection';
import { PerformanceOverviewBlock } from '../components/PerformanceOverviewBlock';
import { StudioAlertSlot } from '../components/RecipeGuideAndQuotaBlock';
import { RecipePortfolioBlock } from '../components/RecipePortfolioBlock';
import { WaitlistPledgeModal } from '../components/WaitlistPledgeModal';
import type { RecipeOverviewData, RecipeSummaryItem, RecipeUserQuotaStatus } from '../types';
import { toLiveEquitySnapshots } from '../utils/live-studio-helpers';
import { deriveOverviewMetrics } from '../utils/overview-metrics';
import { useBotHeaderActions } from '../utils/use-bot-header-actions';

type BenchmarkFetchFn = (
    tickers: string[],
    startDate: string,
    endDate: string,
) => Promise<Record<string, BenchmarkDataPoint[]>>;

const defaultBenchmarkFetchFn: BenchmarkFetchFn = (tickers, startDate, endDate) =>
    getBenchmarkHistoryFn({ data: { tickers, startDate, endDate } });

export interface RecipeOverviewDetailsPageProps {
    data: RecipeOverviewData;
    initialAtmosphere?: AtmospherePhase;
    initialQuota?: RecipeUserQuotaStatus | null;
    initialUserRecipes?: RecipeSummaryItem[];
    benchmarkFetchFn?: BenchmarkFetchFn;
}

/**
 * Performance tab (`/recipes/$recipeId/performance`).
 *
 * Equity against a benchmark, the open book and the closed trades. Behaviour moved
 * to its own tab (`/behavior`) and run traces live under Live Runs, so this page
 * answers one question: is the bot making money, and where is the money now.
 */
export function RecipeOverviewDetailsPage({
    data,
    initialAtmosphere,
    initialQuota = null,
    initialUserRecipes = [],
    benchmarkFetchFn = defaultBenchmarkFetchFn,
}: RecipeOverviewDetailsPageProps) {
    const actions = useBotHeaderActions({
        recipeId: data.recipeId,
        recipeName: data.strategy.name,
        cadence: data.strategy.cadence,
        initialIsLive: data.isLive,
        initialQuota,
        initialUserRecipes,
    });

    const metrics = useMemo(
        () =>
            deriveOverviewMetrics({
                portfolio: data.portfolio,
                liveRuns: data.recentLiveRuns,
                backtests: data.recentBacktests,
            }),
        [data.portfolio, data.recentLiveRuns, data.recentBacktests],
    );

    const equitySnapshots = useMemo(
        () => toLiveEquitySnapshots(metrics.equityCurve),
        [metrics.equityCurve],
    );
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

    const conflictingLiveRecipe =
        actions.liveControl.state.kind === 'confirming' ||
        actions.liveControl.state.kind === 'switching'
            ? actions.liveControl.state.conflicting
            : null;

    // The panels below own the Enable Live and Run Backtest buttons, so the
    // confirmation and error surfaces the hub card renders have to live here too.
    const ownerAlerts = (
        <>
            {conflictingLiveRecipe ? (
                <LiveSwitchConfirmation
                    conflictingRecipe={conflictingLiveRecipe}
                    targetRecipeName={data.strategy.name}
                    isSwitching={actions.liveControl.state.kind === 'switching'}
                    onConfirm={actions.handleConfirmSwitch}
                    onCancel={actions.liveControl.cancelSwitch}
                />
            ) : null}
            <StudioAlertSlot
                backtestError={actions.backtestError}
                scheduleError={actions.liveControl.scheduleError}
                onRequestCapacity={() => actions.setShowPledgeModal(true)}
            />
            {actions.forkError ? (
                <div
                    role="alert"
                    className="border border-danger bg-voxel-surface p-3 text-xs font-normal text-danger rounded-none"
                >
                    {actions.forkError}
                </div>
            ) : null}
        </>
    );

    return (
        <>
            <BotSceneShell
                recipeId={data.recipeId}
                recipeName={data.strategy.name}
                activeTab="performance"
                sectionTitle="Performance & positions"
                isOwner={data.isOwner}
                isLive={actions.isLive}
                initialAtmosphere={initialAtmosphere}
                alerts={ownerAlerts}
            >
                <PerformanceOverviewBlock
                    metrics={metrics}
                    equitySnapshots={equitySnapshots}
                    benchmarkData={benchmarkData}
                    selectedBenchmark={selectedBenchmark}
                    settledBenchmark={settledBenchmark}
                    pendingBenchmark={pendingBenchmark}
                    benchmarkError={benchmarkError}
                    hasMultiDayHistory={hasMultiDayHistory}
                    isOwner={data.isOwner}
                    isLive={actions.isLive}
                    isRunningBacktest={actions.isRunningBacktest}
                    isTogglingLive={actions.liveControl.isBusy}
                    onBenchmarkChange={onBenchmarkChange}
                    onBacktest={actions.handleBacktest}
                    onToggleLive={actions.handleToggleLive}
                />

                <Card
                    padding="md"
                    data-testid="bot-positions-dna-block"
                    className="flex flex-col gap-6 min-w-0"
                >
                    <RecipePortfolioBlock
                        title="Open Positions"
                        cash={data.portfolio.cash}
                        totalEquity={data.portfolio.total_equity}
                        openPositions={data.portfolio.open_positions}
                        embedded
                    />

                    <ClosedTradesSection
                        title="Recent Closed Trades"
                        trades={data.portfolio.trades}
                        limit={5}
                        emptyMessage="No closed live trades yet. Executed exits appear here with net P&L and catalyst notes."
                    />

                    <OverviewBottomSection
                        recipeId={data.recipeId}
                        strategy={data.strategy}
                        backtests={data.recentBacktests}
                        isOwner={data.isOwner}
                        onFork={actions.handleFork}
                    />
                </Card>
            </BotSceneShell>

            <WaitlistPledgeModal
                isOpen={actions.showPledgeModal}
                onClose={() => actions.setShowPledgeModal(false)}
                onSubmit={actions.handlePledgeSubmit}
            />
        </>
    );
}
