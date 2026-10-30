import { Badge, Card, ConfidenceBar, SectionHeading } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
import { type AgentQueueItem, fetchAgentQueueStatus } from '../api/fetch-agent-queue';
import { useLiveTapeStream } from '../hooks/useLiveTapeStream';
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
    technicals?: {
        vwap: number;
        rsi_14: number;
        trend: string;
    };
    memoriesConsulted?: string[];
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
    const directionBadgeScheme =
        marketDirection === 'BULLISH'
            ? 'success'
            : marketDirection === 'BEARISH'
              ? 'danger'
              : 'accent';

    const actionBadgeScheme =
        action === 'BUY' ? 'success' : action === 'SELL' ? 'danger' : 'neutral';

    return (
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b-2 border-boxel-bevel-hi">
            <div>
                <SectionHeading className="text-lg">24/7 Autonomous SPY Trader</SectionHeading>
                <div className="flex items-center gap-2 text-xs font-mono text-boxel-muted mt-0.5">
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
                {onRefresh && (
                    <button
                        type="button"
                        onClick={onRefresh}
                        disabled={isPolling}
                        className="voxel-btn text-[10px] font-mono uppercase px-2.5 py-1 text-boxel-ink hover:text-accent disabled:opacity-50 flex items-center gap-1"
                        title="Refresh intraday tape from server"
                    >
                        <span>{isPolling ? 'Refreshing...' : 'Refresh Tape'}</span>
                    </button>
                )}
                <Badge colorScheme={directionBadgeScheme} variant="solid" size="sm" showDot>
                    {marketDirection}
                </Badge>
                <Badge colorScheme={actionBadgeScheme} variant="outline" size="sm">
                    {action}
                </Badge>
            </div>
        </div>
    );
}

function ConsoleTechnicalsRow({
    technicals,
    memoriesConsulted,
}: {
    technicals?: LiveAgentState['technicals'];
    memoriesConsulted?: string[];
}) {
    return (
        <div className="flex flex-wrap gap-2 text-xs font-mono">
            {technicals && (
                <>
                    <div className="voxel-trough px-2.5 py-1.5 flex items-center gap-1.5">
                        <span className="text-boxel-muted">VWAP:</span>
                        <span className="font-bold text-boxel-ink">
                            ${technicals.vwap.toFixed(2)}
                        </span>
                    </div>
                    <div className="voxel-trough px-2.5 py-1.5 flex items-center gap-1.5">
                        <span className="text-boxel-muted">RSI:</span>
                        <span className="font-bold text-boxel-ink">
                            {technicals.rsi_14.toFixed(1)}
                        </span>
                    </div>
                    <div className="voxel-trough px-2.5 py-1.5 flex items-center gap-1.5">
                        <span className="text-boxel-muted">Trend:</span>
                        <span
                            className={`font-bold ${
                                technicals.trend === 'BULLISH'
                                    ? 'text-success'
                                    : technicals.trend === 'BEARISH'
                                      ? 'text-danger'
                                      : 'text-accent'
                            }`}
                        >
                            {technicals.trend}
                        </span>
                    </div>
                </>
            )}

            {memoriesConsulted?.map((mem) => (
                <div
                    key={mem}
                    className="voxel-trough px-2.5 py-1.5 flex items-center gap-1 text-boxel-muted"
                >
                    <span>Ref:</span>
                    <span className="text-boxel-ink font-bold">{mem}</span>
                </div>
            ))}
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
        agentState: streamedAgentState,
        isStreaming,
        isRefreshing,
        refreshTape,
    } = useLiveTapeStream({
        initialBars: bars,
        initialAgentState: agentState,
        isMarketOpen,
        onRefreshTape,
    });

    const currentAgentState = streamedAgentState ?? agentState;
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
            setCountdownSeconds((prev) => (prev > 0 ? prev - 1 : 300));
        }, 1000);
        return () => clearInterval(timer);
    }, [isMarketOpen]);

    return (
        <Card
            data-testid="live-agent-console"
            padding="md"
            className="flex-1 basis-96 min-w-0 flex flex-col gap-4"
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

            <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
                {currentAgentState.sentimentLabel && (
                    <div className="text-base font-black text-boxel-ink tracking-tight">
                        {currentAgentState.sentimentLabel}
                    </div>
                )}
                <div className="flex items-center gap-2 text-boxel-muted">
                    {currentAgentState.modelUsed && (
                        <span>Model: {currentAgentState.modelUsed}</span>
                    )}
                    {currentAgentState.lastUpdated && (
                        <span>• Turn: {currentAgentState.lastUpdated}</span>
                    )}
                </div>
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

            <SPYCandlestickChart bars={currentBars} trades={trades} height={320} />

            <div className="voxel-trough p-3.5 flex flex-col gap-2">
                <div className="flex items-center justify-between text-xs font-black tracking-wider uppercase text-boxel-muted border-b border-boxel-bevel-hi/50 pb-1.5">
                    <span>Intraday Thought Trace</span>
                    <span className="text-accent">{currentAgentState.action} DECISION</span>
                </div>
                <div className="text-sm leading-relaxed text-boxel-ink">
                    &quot;{currentAgentState.thought}&quot;
                </div>
            </div>

            <ConsoleTechnicalsRow
                technicals={currentAgentState.technicals}
                memoriesConsulted={currentAgentState.memoriesConsulted}
            />

            <ConsoleQueueCard
                user={currentUser}
                pendingCount={pendingCount}
                latestAnswered={latestAnswered}
                onQuestionQueued={() => {
                    setPendingCount((prev) => prev + 1);
                }}
            />
        </Card>
    );
}
