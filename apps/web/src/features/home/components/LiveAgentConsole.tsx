import { Badge, Card, ConfidenceBar, SectionHeading } from '@llm-market-bench/ui-design-system';
import * as React from 'react';
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
}: {
    isMarketOpen: boolean;
    countdownSeconds: number;
    marketDirection: LiveAgentState['marketDirection'];
    action: LiveAgentState['action'];
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
                                isMarketOpen ? 'bg-success animate-pulse' : 'bg-boxel-muted'
                            }`}
                        />
                        {isMarketOpen ? 'LIVE SESSION' : 'MARKET CLOSED'}
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

function ConsoleQueueCard({
    userQuestion,
    setUserQuestion,
    queueSubmitted,
    onSubmit,
}: {
    userQuestion: string;
    setUserQuestion: (val: string) => void;
    queueSubmitted: boolean;
    onSubmit: (e: React.FormEvent) => void;
}) {
    return (
        <div className="voxel-trough p-3 flex flex-col gap-2 border border-accent/20">
            <div className="flex flex-wrap items-center justify-between gap-1">
                <span className="text-xs font-black uppercase tracking-wider text-accent">
                    Audience Interactive Queue
                </span>
                <span className="text-xs font-mono text-boxel-muted">Coming Soon</span>
            </div>
            <p className="text-xs text-boxel-muted leading-normal">
                Submit questions or thesis hypotheses to inject into the model&apos;s next 5-minute
                thinking turn.
            </p>

            {queueSubmitted ? (
                <div className="text-xs font-mono text-success font-bold py-1">
                    Question queued. Injected during the next open market evaluation turn.
                </div>
            ) : (
                <form onSubmit={onSubmit} className="flex flex-wrap gap-2 mt-1">
                    <input
                        type="text"
                        value={userQuestion}
                        onChange={(e) => setUserQuestion(e.target.value)}
                        placeholder="Ask a question for the model's next turn..."
                        className="voxel-input flex-1 min-w-48 px-3 py-1.5 text-xs bg-boxel-canvas text-boxel-ink border border-boxel-bevel-hi focus:outline-none focus:border-accent"
                    />
                    <button
                        type="submit"
                        className="voxel-btn bg-accent text-accent-ink px-3 py-1.5 text-xs font-black uppercase tracking-widest hover:opacity-90"
                    >
                        Queue
                    </button>
                </form>
            )}
        </div>
    );
}

export function LiveAgentConsole({
    bars,
    trades = [],
    agentState,
    isMarketOpen = true,
}: LiveAgentConsoleProps) {
    const [userQuestion, setUserQuestion] = React.useState('');
    const [queueSubmitted, setQueueSubmitted] = React.useState(false);
    const [countdownSeconds, setCountdownSeconds] = React.useState(285);

    React.useEffect(() => {
        if (!isMarketOpen) return;
        const timer = setInterval(() => {
            setCountdownSeconds((prev) => (prev > 0 ? prev - 1 : 300));
        }, 1000);
        return () => clearInterval(timer);
    }, [isMarketOpen]);

    const handleQueueSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!userQuestion.trim()) return;
        setQueueSubmitted(true);
        setUserQuestion('');
    };

    return (
        <Card
            data-testid="live-agent-console"
            padding="md"
            className="flex-1 basis-96 min-w-0 flex flex-col gap-4"
        >
            <ConsoleHeaderRibbon
                isMarketOpen={isMarketOpen}
                countdownSeconds={countdownSeconds}
                marketDirection={agentState.marketDirection}
                action={agentState.action}
            />

            <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
                {agentState.sentimentLabel && (
                    <div className="text-base font-black text-boxel-ink tracking-tight">
                        {agentState.sentimentLabel}
                    </div>
                )}
                <div className="flex items-center gap-2 text-boxel-muted">
                    {agentState.modelUsed && <span>Model: {agentState.modelUsed}</span>}
                    {agentState.lastUpdated && <span>• Turn: {agentState.lastUpdated}</span>}
                </div>
            </div>

            <ConfidenceBar
                label="Agent Conviction"
                value={agentState.conviction}
                colorScheme={
                    agentState.conviction >= 70
                        ? 'success'
                        : agentState.conviction >= 45
                          ? 'warning'
                          : 'danger'
                }
                textStyle="hero"
                className="w-full"
            />

            <SPYCandlestickChart bars={bars} trades={trades} height={250} />

            <div className="voxel-trough p-3.5 flex flex-col gap-2">
                <div className="flex items-center justify-between text-xs font-black tracking-wider uppercase text-boxel-muted border-b border-boxel-bevel-hi/50 pb-1.5">
                    <span>Intraday Thought Trace</span>
                    <span className="text-accent">{agentState.action} DECISION</span>
                </div>
                <div className="text-sm leading-relaxed text-boxel-ink">
                    &quot;{agentState.thought}&quot;
                </div>
            </div>

            <ConsoleTechnicalsRow
                technicals={agentState.technicals}
                memoriesConsulted={agentState.memoriesConsulted}
            />

            <ConsoleQueueCard
                userQuestion={userQuestion}
                setUserQuestion={setUserQuestion}
                queueSubmitted={queueSubmitted}
                onSubmit={handleQueueSubmit}
            />
        </Card>
    );
}
