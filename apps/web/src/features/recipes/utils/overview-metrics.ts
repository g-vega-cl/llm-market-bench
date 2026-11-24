import type { BacktestResultData, LivePortfolioSnapshot, RecipeJobRecord } from '../types';

export type InsightsSource = 'live' | 'backtest' | 'none';

export interface OverviewMetricsSummary {
    mode: InsightsSource;
    totalEquity: number;
    cash: number;
    netReturnPct: number | null;
    winRatePct: number | null;
    closedTradesCount: number;
    winningTradesCount: number;
    openPositionsCount: number;
    equityCurve: { time: string; equity: number }[];
    latestBacktestJobId: string | null;
}

export function extractBacktestResult(job: RecipeJobRecord | undefined): BacktestResultData | null {
    if (!job?.result_json) return null;
    if ('mode' in job.result_json && job.result_json.mode === 'live_turn') return null;
    return job.result_json as BacktestResultData;
}

export function findLatestCompletedBacktest(
    backtests: RecipeJobRecord[],
): { job: RecipeJobRecord; result: BacktestResultData } | null {
    for (const job of backtests) {
        if (job.status !== 'completed') continue;
        const result = extractBacktestResult(job);
        if (result) return { job, result };
    }
    return null;
}

function buildLiveOverviewMetrics(
    portfolio: LivePortfolioSnapshot,
    latestBacktestId: string | null,
): OverviewMetricsSummary {
    const curve = portfolio.equity_curve ?? [];
    const baseline = curve[0]?.equity && curve[0].equity > 0 ? curve[0].equity : 10_000;
    const hasReturnAnchor =
        curve.length > 0 || portfolio.trades.length > 0 || portfolio.open_positions.length > 0;
    const netReturnPct = hasReturnAnchor
        ? Number((((portfolio.total_equity - baseline) / baseline) * 100).toFixed(2))
        : null;
    const closedCount = portfolio.trades.length;
    const winningCount = portfolio.trades.filter((t) => t.pnl_net > 0).length;

    return {
        mode: 'live',
        totalEquity: portfolio.total_equity,
        cash: portfolio.cash,
        netReturnPct,
        winRatePct:
            closedCount > 0 ? Number(((winningCount / closedCount) * 100).toFixed(1)) : null,
        closedTradesCount: closedCount,
        winningTradesCount: winningCount,
        openPositionsCount: portfolio.open_positions.length,
        equityCurve: curve,
        latestBacktestJobId: latestBacktestId,
    };
}

function buildBacktestOverviewMetrics(
    jobId: string,
    res: BacktestResultData,
): OverviewMetricsSummary {
    const starting = res.starting_capital ?? 10_000;
    return {
        mode: 'backtest',
        totalEquity: res.total_equity ?? res.ending_capital_net ?? starting,
        cash: res.cash ?? starting,
        netReturnPct: res.total_return_pct_net,
        winRatePct: res.win_rate_pct,
        closedTradesCount: res.total_trades,
        winningTradesCount: res.winning_trades ?? 0,
        openPositionsCount: res.open_positions?.length ?? 0,
        equityCurve: res.equity_curve ?? [],
        latestBacktestJobId: jobId,
    };
}

export function hasLiveOverviewActivity(args: {
    portfolio: LivePortfolioSnapshot;
    liveRuns: RecipeJobRecord[];
}): boolean {
    const curve = args.portfolio.equity_curve ?? [];
    return (
        args.liveRuns.some((r) => r.status === 'completed') ||
        args.portfolio.trades.length > 0 ||
        args.portfolio.open_positions.length > 0 ||
        curve.length > 0
    );
}

/**
 * Computes top-level KPIs for the Bot Overview, prioritizing live paper state
 * and falling back to the latest completed backtest before live turns begin.
 */
export function deriveOverviewMetrics(args: {
    portfolio: LivePortfolioSnapshot;
    liveRuns: RecipeJobRecord[];
    backtests: RecipeJobRecord[];
}): OverviewMetricsSummary {
    const hasLive = hasLiveOverviewActivity(args);

    const latestBacktest = findLatestCompletedBacktest(args.backtests);

    if (hasLive) {
        return buildLiveOverviewMetrics(args.portfolio, latestBacktest?.job.id ?? null);
    }

    if (latestBacktest) {
        return buildBacktestOverviewMetrics(latestBacktest.job.id, latestBacktest.result);
    }

    return {
        mode: 'none',
        totalEquity: args.portfolio.total_equity,
        cash: args.portfolio.cash,
        netReturnPct: null,
        winRatePct: null,
        closedTradesCount: 0,
        winningTradesCount: 0,
        openPositionsCount: 0,
        equityCurve: [],
        latestBacktestJobId: null,
    };
}
