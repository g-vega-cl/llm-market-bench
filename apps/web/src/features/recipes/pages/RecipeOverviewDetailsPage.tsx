import { type AtmospherePhase, Card } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useMemo } from 'react';
import {
    type BenchmarkDataPoint,
    getBenchmarkHistoryFn,
    usePortfolioBenchmark,
} from '~/features/portfolios';
import { BotBehaviorsBlock } from '../components/BotBehaviorsBlock';
import { BotSceneShell } from '../components/BotSceneShell';
import { ClosedTradesSection } from '../components/ClosedTradesSection';
import { OverviewBottomSection } from '../components/OverviewBottomSection';
import { PerformanceOverviewBlock } from '../components/PerformanceOverviewBlock';
import { RecipePortfolioBlock } from '../components/RecipePortfolioBlock';
import type { RecipeOverviewData, RecipeSummaryItem, RecipeUserQuotaStatus } from '../types';
import { toLiveEquitySnapshots } from '../utils/live-studio-helpers';
import { deriveOverviewMetrics } from '../utils/overview-metrics';
import { computeBotBehaviors } from '../utils/recipe-insights';
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
 * Overview detail page (`/recipes/$recipeId/performance`).
 *
 * The three panels that used to sit under the hub card: Performance & Equity,
 * Behaviors & Insights, and Positions / Trades / Strategy DNA. The hub card is not
 * rendered here — the back link and sub-nav in `BotSceneShell` carry the context.
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

    const behaviors = useMemo(
        () =>
            computeBotBehaviors({
                strategy: data.strategy,
                liveRuns: data.recentLiveRuns,
                trades: data.portfolio.trades,
                backtests: data.recentBacktests,
            }),
        [data.strategy, data.recentLiveRuns, data.portfolio.trades, data.recentBacktests],
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

    return (
        <BotSceneShell
            recipeId={data.recipeId}
            recipeName={data.strategy.name}
            activeTab="overview"
            parent="overview"
            isOwner={data.isOwner}
            isLive={actions.isLive}
            initialAtmosphere={initialAtmosphere}
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

            <BotBehaviorsBlock recipeId={data.recipeId} behaviors={behaviors} />

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
                    trailingAction={
                        <Link
                            to="/recipes/live/$recipeId/runs"
                            params={{ recipeId: data.recipeId }}
                            className="text-xs font-normal text-accent underline underline-offset-4 hover:text-accent-hover whitespace-nowrap"
                        >
                            View all trades &amp; traces →
                        </Link>
                    }
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
    );
}
