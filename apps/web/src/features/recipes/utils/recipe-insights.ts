import {
    type BacktestResultData,
    type CompletedTradeRecord,
    CURATED_TOOLS,
    type LiveRunResult,
    type PushStrategy,
    type RecipeJobRecord,
} from '../types';
import {
    deriveOverviewMetrics,
    extractBacktestResult,
    findLatestCompletedBacktest,
    hasLiveOverviewActivity,
    type InsightsSource,
    type OverviewMetricsSummary,
} from './overview-metrics';

export {
    deriveOverviewMetrics,
    extractBacktestResult,
    findLatestCompletedBacktest,
    type InsightsSource,
    type OverviewMetricsSummary,
};

export interface ActionMixSummary {
    buyCount: number;
    exitCount: number;
    sellCount: number;
    holdCount: number;
    totalTurns: number;
    skippedCount: number;
}

export interface TickerFocusItem {
    ticker: string;
    signalCount: number;
    closedCount: number;
    wins: number;
    netPnl: number;
}

export interface ExitReasonItem {
    reason: string;
    count: number;
    wins: number;
}

export interface ToolUsageItem {
    name: string;
    label: string;
    count: number;
    pct: number;
}

export interface LatestDecisionSnapshot {
    jobId: string;
    mode: 'live_turn' | 'backtest';
    timestamp: string | null;
    signals: { action: string; ticker: string }[];
    excerpt: string;
}

export interface BotBehaviorsSummary {
    source: InsightsSource;
    actionMix: ActionMixSummary;
    topTickers: TickerFocusItem[];
    exitReasons: ExitReasonItem[];
    toolUsage: ToolUsageItem[];
    latestDecision: LatestDecisionSnapshot | null;
}

const TOOL_LABEL_MAP = new Map(CURATED_TOOLS.map((tool) => [tool.name, tool.label]));

export function extractLiveRunResult(job: RecipeJobRecord | undefined): LiveRunResult | null {
    if (!job?.result_json) return null;
    if ('mode' in job.result_json && job.result_json.mode === 'live_turn') {
        return job.result_json as LiveRunResult;
    }
    return null;
}

function summarizeOutputExcerpt(raw: string | undefined): string {
    const cleaned = (raw ?? '').replace(/\s+/g, ' ').trim();
    if (!cleaned) return 'No model narrative recorded for this turn.';
    return cleaned.length > 220 ? `${cleaned.slice(0, 217)}…` : cleaned;
}

function accumulateTurnSignals(
    signals: { action: string; ticker: string }[],
    actionMix: ActionMixSummary,
    tickerMap: Map<string, TickerFocusItem>,
) {
    if (signals.length === 0) {
        actionMix.holdCount += 1;
        return;
    }
    for (const sig of signals) {
        const action = String(sig.action || '').toUpperCase();
        if (action === 'BUY') actionMix.buyCount += 1;
        else if (action === 'EXIT') actionMix.exitCount += 1;
        else if (action === 'SELL') actionMix.sellCount += 1;

        const ticker = String(sig.ticker || '')
            .trim()
            .toUpperCase();
        if (!ticker) continue;
        const prev = tickerMap.get(ticker) ?? {
            ticker,
            signalCount: 0,
            closedCount: 0,
            wins: 0,
            netPnl: 0,
        };
        prev.signalCount += 1;
        tickerMap.set(ticker, prev);
    }
}

function accumulateTrades(
    trades: CompletedTradeRecord[],
    tickerMap: Map<string, TickerFocusItem>,
    exitReasonMap: Map<string, ExitReasonItem>,
) {
    for (const trade of trades) {
        const ticker = String(trade.ticker || '')
            .trim()
            .toUpperCase();
        if (ticker) {
            const prev = tickerMap.get(ticker) ?? {
                ticker,
                signalCount: 0,
                closedCount: 0,
                wins: 0,
                netPnl: 0,
            };
            prev.closedCount += 1;
            if (trade.pnl_net > 0) prev.wins += 1;
            prev.netPnl += Number(trade.pnl_net || 0);
            tickerMap.set(ticker, prev);
        }

        const reason = String(trade.exit_reason || 'EXIT').trim() || 'EXIT';
        const prevReason = exitReasonMap.get(reason) ?? { reason, count: 0, wins: 0 };
        prevReason.count += 1;
        if (trade.pnl_net > 0) prevReason.wins += 1;
        exitReasonMap.set(reason, prevReason);
    }
}

function tallyToolCalls(toolCounts: Map<string, number>, toolNames: string[]) {
    for (const rawName of toolNames) {
        const name = String(rawName || '').trim();
        if (!name) continue;
        toolCounts.set(name, (toolCounts.get(name) ?? 0) + 1);
    }
}

function buildToolUsageList(toolCounts: Map<string, number>, totalTurns: number): ToolUsageItem[] {
    const denom = Math.max(1, totalTurns);
    return Array.from(toolCounts.entries())
        .map(([name, count]) => ({
            name,
            label: TOOL_LABEL_MAP.get(name) ?? name,
            count,
            pct: Math.min(100, Math.round((count / denom) * 100)),
        }))
        .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
        .slice(0, 5);
}

interface BehaviorAccumulator {
    actionMix: ActionMixSummary;
    tickerMap: Map<string, TickerFocusItem>;
    exitReasonMap: Map<string, ExitReasonItem>;
    toolCounts: Map<string, number>;
    latestDecision: LatestDecisionSnapshot | null;
}

function createAccumulator(): BehaviorAccumulator {
    return {
        actionMix: {
            buyCount: 0,
            exitCount: 0,
            sellCount: 0,
            holdCount: 0,
            totalTurns: 0,
            skippedCount: 0,
        },
        tickerMap: new Map(),
        exitReasonMap: new Map(),
        toolCounts: new Map(),
        latestDecision: null,
    };
}

function populateFromLiveRuns(
    acc: BehaviorAccumulator,
    completedLive: Array<{ job: RecipeJobRecord; result: LiveRunResult }>,
    trades: CompletedTradeRecord[],
) {
    acc.actionMix.totalTurns = completedLive.length;
    for (const { result } of completedLive) {
        accumulateTurnSignals(result.signals ?? [], acc.actionMix, acc.tickerMap);
        for (const stage of result.stages ?? []) {
            tallyToolCalls(acc.toolCounts, stage.tool_calls ?? []);
        }
    }
    accumulateTrades(trades, acc.tickerMap, acc.exitReasonMap);

    const newest = completedLive[0];
    if (!newest) return;
    acc.latestDecision = {
        jobId: newest.job.id,
        mode: 'live_turn',
        timestamp:
            newest.result.as_of_utc ?? newest.job.completed_at ?? newest.job.created_at ?? null,
        signals: newest.result.signals ?? [],
        excerpt: summarizeOutputExcerpt(
            newest.result.final_output || newest.result.stages?.[0]?.output,
        ),
    };
}

function populateFromBacktest(
    acc: BehaviorAccumulator,
    latestBacktest: { job: RecipeJobRecord; result: BacktestResultData },
) {
    const steps = latestBacktest.result.day_steps ?? [];
    acc.actionMix.totalTurns = steps.length;
    acc.actionMix.skippedCount = latestBacktest.result.skipped_trades?.length ?? 0;
    for (const step of steps) {
        accumulateTurnSignals(step.signals ?? [], acc.actionMix, acc.tickerMap);
        tallyToolCalls(acc.toolCounts, step.tool_calls ?? []);
    }
    accumulateTrades(latestBacktest.result.trades ?? [], acc.tickerMap, acc.exitReasonMap);

    const lastStep = steps[steps.length - 1];
    if (!lastStep) return;
    acc.latestDecision = {
        jobId: latestBacktest.job.id,
        mode: 'backtest',
        timestamp: lastStep.day ?? latestBacktest.job.completed_at ?? null,
        signals: lastStep.signals ?? [],
        excerpt: summarizeOutputExcerpt(lastStep.full_output || lastStep.output_excerpt),
    };
}

/**
 * Computes deterministic behavioral insights from a bot's live runs/ledger,
 * falling back to its latest completed backtest when no live runs exist yet.
 */
export function computeBotBehaviors(args: {
    strategy: PushStrategy;
    liveRuns: RecipeJobRecord[];
    trades: CompletedTradeRecord[];
    backtests: RecipeJobRecord[];
}): BotBehaviorsSummary {
    const completedLive = args.liveRuns
        .map((job) => ({ job, result: extractLiveRunResult(job) }))
        .filter((item): item is { job: RecipeJobRecord; result: LiveRunResult } =>
            Boolean(item.job.status === 'completed' && item.result),
        );

    const latestBacktest = findLatestCompletedBacktest(args.backtests);
    const hasLive = hasLiveOverviewActivity({
        portfolio: {
            cash: 0,
            total_equity: 0,
            open_positions: [],
            trades: args.trades,
        },
        liveRuns: args.liveRuns,
    });
    const source: InsightsSource = hasLive ? 'live' : latestBacktest ? 'backtest' : 'none';

    const acc = createAccumulator();
    if (source === 'live') {
        populateFromLiveRuns(acc, completedLive, args.trades);
    } else if (source === 'backtest' && latestBacktest) {
        populateFromBacktest(acc, latestBacktest);
    } else {
        for (const tool of args.strategy.stages[0]?.selected_tools ?? []) {
            acc.toolCounts.set(tool, 0);
        }
    }

    const topTickers = Array.from(acc.tickerMap.values())
        .sort(
            (a, b) =>
                b.closedCount + b.signalCount - (a.closedCount + a.signalCount) ||
                a.ticker.localeCompare(b.ticker),
        )
        .slice(0, 4);

    const exitReasons = Array.from(acc.exitReasonMap.values())
        .sort((a, b) => b.count - a.count || a.reason.localeCompare(b.reason))
        .slice(0, 4);

    return {
        source,
        actionMix: acc.actionMix,
        topTickers,
        exitReasons,
        toolUsage: buildToolUsageList(acc.toolCounts, acc.actionMix.totalTurns),
        latestDecision: acc.latestDecision,
    };
}
