import { Card, ConfidenceBar, SectionHeading } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { formatEasternTime } from '~/utils/date';
import { type AgentQueueItem, fetchAgentQueueStatus } from '../api/fetch-agent-queue';
import type { LiveTraderPortfolioSummary } from '../api/fetch-intraday-tape';
import { useLiveTapeStream } from '../hooks/useLiveTapeStream';
import { ConsolePortfolioStrip } from './ConsolePortfolioStrip';
import { ConsoleQueueCard } from './ConsoleQueueCard';
import {
    type CandlestickBar,
    type ChartTradeMarker,
    SPYCandlestickChart,
} from './SPYCandlestickChart';

export interface LiveAgentState {
    action: 'BUY' | 'SELL' | 'HOLD';
    conviction: number;
    thought: string;
    marketDirection: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
    sentimentLabel?: string;
    modelUsed?: string;
    lastUpdated?: string;
    timestamp?: string;
    technicals?: {
        vwap: number;
        rsi_14: number;
        trend: string;
    };
    memoriesConsulted?: string[];
    portfolio?: LiveTraderPortfolioSummary;
}

export interface LiveAgentConsoleProps {
    bars: CandlestickBar[];
    trades?: ChartTradeMarker[];
    agentState: LiveAgentState;
    isMarketOpen?: boolean;
    currentUser?: { id: string; email?: string } | null;
    onRefreshTape?: () => void;
}

function formatCountdown(totalSec: number) {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

const DIRECTION_COLOR_MAP: Record<
    LiveAgentState['marketDirection'],
    { text: string; dot: string }
> = {
    BULLISH: { text: 'text-success', dot: 'bg-success' },
    BEARISH: { text: 'text-danger', dot: 'bg-danger' },
    NEUTRAL: { text: 'text-boxel-ink', dot: 'bg-boxel-muted' },
};

const ACTION_COLOR_MAP: Record<LiveAgentState['action'], string> = {
    BUY: 'text-success',
    SELL: 'text-danger',
    HOLD: 'text-boxel-muted',
};

function ConsoleHeaderRibbon({
    isMarketOpen,
    countdownSeconds,
    marketDirection,
    action,
    isStreaming = false,
    isPolling = false,
    onRefresh,
}: {
    isMarketOpen: boolean;
    countdownSeconds: number;
    marketDirection: LiveAgentState['marketDirection'];
    action: LiveAgentState['action'];
    isStreaming?: boolean;
    isPolling?: boolean;
    onRefresh?: () => void;
}) {
    const directionStyle = DIRECTION_COLOR_MAP[marketDirection] ?? DIRECTION_COLOR_MAP.NEUTRAL;
    const actionColor = ACTION_COLOR_MAP[action] ?? ACTION_COLOR_MAP.HOLD;

    return (
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b-2 border-boxel-bevel-hi">
            <div className="flex flex-col gap-1">
                <SectionHeading className="text-lg">24/7 Autonomous SPY Trader</SectionHeading>
                <div className="flex items-center gap-2 text-xs font-mono text-boxel-muted">
                    <span className="flex items-center gap-1.5">
                        <span
                            className={`h-2 w-2 rounded-none ${
                                isMarketOpen
                                    ? isStreaming
                                        ? 'bg-success animate-pulse'
                                        : 'bg-success'
                                    : 'bg-boxel-muted'
                            }`}
                        />
                        {isMarketOpen
                            ? isStreaming
                                ? 'LIVE SESSION (STREAMING)'
                                : 'LIVE SESSION'
                            : 'MARKET CLOSED'}
                    </span>
                    <span>•</span>
                    <span>
                        {isMarketOpen
                            ? `Next evaluation in ${formatCountdown(countdownSeconds)}`
                            : 'Next Session 09:30 ET'}
                    </span>
                </div>
            </div>

            <div className="flex items-center gap-2">
                <div
                    data-testid="console-telemetry-trough"
                    className="voxel-trough px-2.5 py-1 text-xs font-mono flex items-center gap-2"
                >
                    <span className="flex items-center gap-1.5">
                        <span
                            className={`h-1.5 w-1.5 shrink-0 rounded-none ${directionStyle.dot}`}
                        />
                        <span className="text-boxel-muted">BIAS:</span>
                        <span className={`font-bold ${directionStyle.text}`}>
                            {marketDirection}
                        </span>
                    </span>
                    <span className="text-boxel-bevel-hi">/</span>
                    <span className="flex items-center gap-1">
                        <span className="text-boxel-muted">ACT:</span>
                        <span className={`font-bold ${actionColor}`}>{action}</span>
                    </span>
                </div>

                {onRefresh && (
                    <button
                        type="button"
                        onClick={onRefresh}
                        disabled={isPolling}
                        className="voxel-btn text-xs font-normal font-mono uppercase px-2.5 py-1 text-boxel-ink hover:text-accent disabled:opacity-50 flex items-center gap-1"
                        title="Refresh intraday tape from server"
                    >
                        <span>{isPolling ? 'Refreshing...' : 'Refresh Tape'}</span>
                    </button>
                )}
            </div>
        </div>
    );
}

export function LiveAgentConsole({
    bars,
    trades = [],
    agentState,
    isMarketOpen = true,
    currentUser,
    onRefreshTape,
}: LiveAgentConsoleProps) {
    const {
        bars: currentBars,
        trades: currentTrades,
        agentState: streamedAgentState,
        isStreaming,
        isRefreshing,
        refreshTape,
    } = useLiveTapeStream({
        initialBars: bars,
        initialTrades: trades,
        initialAgentState: agentState,
        isMarketOpen,
        onRefreshTape,
    });

    const currentAgentState = streamedAgentState ?? agentState;
    const rawTurnTimestamp =
        currentAgentState.lastUpdated ??
        (currentAgentState.timestamp ? formatEasternTime(currentAgentState.timestamp) : null);
    const turnTimestamp =
        rawTurnTimestamp && rawTurnTimestamp !== 'Unknown' ? rawTurnTimestamp : null;
    const [pendingCount, setPendingCount] = React.useState(0);
    const [latestAnswered, setLatestAnswered] = React.useState<AgentQueueItem | null>(null);
    const [countdownSeconds, setCountdownSeconds] = React.useState(285);

    const handleQueueStatusUpdate = React.useCallback(
        (status: { pendingCount: number; latestAnswered: AgentQueueItem | null }) => {
            setPendingCount(status.pendingCount);
            setLatestAnswered(status.latestAnswered);
        },
        [],
    );

    const handleManualRefresh = React.useCallback(async () => {
        await Promise.all([
            refreshTape(),
            fetchAgentQueueStatus()
                .then(handleQueueStatusUpdate)
                .catch(() => {}),
        ]);
    }, [refreshTape, handleQueueStatusUpdate]);

    React.useEffect(() => {
        fetchAgentQueueStatus()
            .then(handleQueueStatusUpdate)
            .catch(() => {});
    }, [handleQueueStatusUpdate]);

    React.useEffect(() => {
        if (!isMarketOpen) return;
        const timer = setInterval(() => {
            setCountdownSeconds((prev) => {
                if (prev <= 1) {
                    handleManualRefresh();
                    return 300;
                }
                return prev - 1;
            });
        }, 1000);
        return () => clearInterval(timer);
    }, [isMarketOpen, handleManualRefresh]);

    return (
        <Card
            data-testid="live-agent-console"
            padding="md"
            className="h-full min-w-0 flex flex-col gap-4"
        >
            <ConsoleHeaderRibbon
                isMarketOpen={isMarketOpen}
                countdownSeconds={countdownSeconds}
                marketDirection={currentAgentState.marketDirection}
                action={currentAgentState.action}
                isStreaming={isStreaming}
                isPolling={isRefreshing}
                onRefresh={handleManualRefresh}
            />

            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-xs font-mono">
                {currentAgentState.sentimentLabel && (
                    <div className="text-sm font-bold text-boxel-ink tracking-tight">
                        {currentAgentState.sentimentLabel}
                    </div>
                )}
                {currentAgentState.modelUsed && (
                    <span className="whitespace-nowrap text-boxel-muted">
                        Model: {currentAgentState.modelUsed}
                    </span>
                )}
            </div>

            <ConfidenceBar
                label="Agent Conviction"
                value={currentAgentState.conviction}
                colorScheme={
                    currentAgentState.conviction >= 70
                        ? 'success'
                        : currentAgentState.conviction >= 45
                          ? 'warning'
                          : 'danger'
                }
                textStyle="hero"
                className="w-full"
            />

            <ConsolePortfolioStrip portfolio={currentAgentState.portfolio} />

            <SPYCandlestickChart bars={currentBars} trades={currentTrades ?? trades} height={320} />

            <div className="voxel-trough p-3.5 flex flex-col gap-2">
                <div className="text-sm font-bold uppercase tracking-wider text-boxel-muted">
                    Intraday Thought Trace
                </div>
                <div
                    data-testid="thought-trace-meta"
                    className="flex flex-wrap items-baseline gap-x-2 gap-y-1 font-mono text-xs"
                >
                    {turnTimestamp && (
                        <span className="whitespace-nowrap text-boxel-muted">{turnTimestamp}</span>
                    )}
                    <span className="whitespace-nowrap font-bold text-accent">
                        {currentAgentState.action} DECISION
                    </span>
                </div>
                <div className="text-xs font-normal leading-relaxed text-boxel-ink break-words">
                    &quot;{currentAgentState.thought}&quot;
                </div>
            </div>

            <ConsoleQueueCard
                user={currentUser}
                pendingCount={pendingCount}
                latestAnswered={latestAnswered}
                onQuestionQueued={() => {
                    setPendingCount((prev) => prev + 1);
                }}
            />

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-boxel-bevel-hi/50 text-xs font-normal font-mono text-boxel-muted">
                <div className="flex flex-wrap items-center gap-1.5 min-w-0">
                    <span>Autonomous intraday paper execution.</span>
                    {currentAgentState.memoriesConsulted &&
                        currentAgentState.memoriesConsulted.length > 0 && (
                            <span className="text-boxel-muted/80">
                                (Grounded in {currentAgentState.memoriesConsulted.length} memory{' '}
                                {currentAgentState.memoriesConsulted.length === 1
                                    ? 'reference'
                                    : 'references'}
                                )
                            </span>
                        )}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                    <a href="/memories" className="text-accent hover:underline">
                        Memory Vault →
                    </a>
                    <a
                        href="/lab"
                        className="text-boxel-muted hover:text-boxel-ink hover:underline"
                    >
                        Lab →
                    </a>
                </div>
            </div>
        </Card>
    );
}
