import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { formatEasternDateTime } from '~/utils/date';
import type {
    ActionMixSummary,
    BotBehaviorsSummary,
    ExitReasonItem,
    LatestDecisionSnapshot,
    TickerFocusItem,
    ToolUsageItem,
} from '../utils/recipe-insights';

export interface BotBehaviorsBlockProps {
    recipeId: string;
    behaviors: BotBehaviorsSummary;
}

function sourceBadgeLabel(source: BotBehaviorsSummary['source']): string {
    if (source === 'live') return 'LIVE BEHAVIOR';
    if (source === 'backtest') return 'BACKTEST PREVIEW';
    return 'AWAITING RUNS';
}

function sourceBadgeColor(source: BotBehaviorsSummary['source']): 'success' | 'accent' | 'neutral' {
    if (source === 'live') return 'success';
    if (source === 'backtest') return 'accent';
    return 'neutral';
}

function formatDecisionStamp(timestamp: string | null, mode: 'live_turn' | 'backtest'): string {
    if (!timestamp) return 'Latest turn';
    if (mode === 'backtest') return timestamp;
    const formatted = formatEasternDateTime(timestamp);
    return formatted !== 'Unknown' ? formatted : timestamp;
}

function tickerBadgeColor(item: TickerFocusItem): 'success' | 'danger' | 'neutral' {
    if (item.closedCount === 0) return 'neutral';
    return item.netPnl >= 0 ? 'success' : 'danger';
}

function ActionMixPanel({ actionMix }: { actionMix: ActionMixSummary }) {
    const totalSignals = actionMix.buyCount + actionMix.exitCount + actionMix.sellCount;
    const holdRatePct =
        actionMix.totalTurns > 0
            ? Math.round((actionMix.holdCount / actionMix.totalTurns) * 100)
            : 0;

    return (
        <div className="voxel-trough bg-voxel-trough p-4 h-full flex flex-col justify-between gap-3 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-2 min-w-0">
                <span className="text-sm font-bold text-voxel-ink">
                    Action Mix &amp; Selectivity
                </span>
                <span className="text-xs font-normal font-mono text-voxel-muted whitespace-nowrap">
                    {actionMix.totalTurns} turns
                </span>
            </div>

            {actionMix.totalTurns === 0 ? (
                <p className="text-xs font-normal text-voxel-muted">
                    No completed turns yet. Run a backtest or enable Live (30m) to observe signal
                    frequency.
                </p>
            ) : (
                <div className="flex flex-col gap-3 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                        <Badge colorScheme="success" variant="soft" size="xs">
                            BUY {actionMix.buyCount}
                        </Badge>
                        <Badge colorScheme="warning" variant="soft" size="xs">
                            EXIT {actionMix.exitCount + actionMix.sellCount}
                        </Badge>
                        <Badge colorScheme="neutral" variant="soft" size="xs">
                            HOLD {actionMix.holdCount}
                        </Badge>
                    </div>
                    <div className="flex flex-col gap-1">
                        <div className="flex flex-wrap items-baseline justify-between gap-2 text-xs font-normal text-voxel-muted">
                            <span>Hold selectivity</span>
                            <span className="font-mono tabular-nums">{holdRatePct}%</span>
                        </div>
                        <div className="w-full h-2 bg-voxel-canvas border border-voxel-bevel-lo">
                            <div
                                className="h-full bg-accent"
                                style={{ width: `${holdRatePct}%` }}
                            />
                        </div>
                    </div>
                    <span className="text-xs font-normal text-voxel-muted">
                        {totalSignals} total signals emitted
                        {actionMix.skippedCount > 0
                            ? ` · ${actionMix.skippedCount} skipped by risk/cash rules`
                            : ''}
                    </span>
                </div>
            )}
        </div>
    );
}

function TickerFocusPanel({
    topTickers,
    exitReasons,
}: {
    topTickers: TickerFocusItem[];
    exitReasons: ExitReasonItem[];
}) {
    const empty = topTickers.length === 0 && exitReasons.length === 0;
    return (
        <div className="voxel-trough bg-voxel-trough p-4 h-full flex flex-col justify-between gap-3 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-2 min-w-0">
                <span className="text-sm font-bold text-voxel-ink">Ticker Focus &amp; Exits</span>
                <span className="text-xs font-normal text-voxel-muted whitespace-nowrap">
                    Top symbols
                </span>
            </div>

            {empty ? (
                <p className="text-xs font-normal text-voxel-muted">
                    Ticker concentration and exit-reason patterns appear once the bot evaluates or
                    closes trades.
                </p>
            ) : (
                <div className="flex flex-col gap-3 min-w-0">
                    {topTickers.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                            {topTickers.map((item) => (
                                <Badge
                                    key={item.ticker}
                                    variant="soft"
                                    colorScheme={tickerBadgeColor(item)}
                                    size="xs"
                                >
                                    {item.ticker} (
                                    {item.closedCount > 0
                                        ? `${item.wins}/${item.closedCount}W`
                                        : `${item.signalCount}x`}
                                    )
                                </Badge>
                            ))}
                        </div>
                    ) : null}

                    {exitReasons.length > 0 ? (
                        <div className="flex flex-col gap-1.5">
                            {exitReasons.map((item) => (
                                <div
                                    key={item.reason}
                                    className="flex flex-wrap items-baseline justify-between gap-2 text-xs font-normal text-voxel-muted"
                                >
                                    <span className="truncate min-w-0">{item.reason}</span>
                                    <span className="font-mono tabular-nums whitespace-nowrap">
                                        {item.count} ({item.wins}W)
                                    </span>
                                </div>
                            ))}
                        </div>
                    ) : null}
                </div>
            )}
        </div>
    );
}

function ToolFootprintPanel({ toolUsage }: { toolUsage: ToolUsageItem[] }) {
    return (
        <div className="voxel-trough bg-voxel-trough p-4 h-full flex flex-col justify-between gap-3 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-2 min-w-0">
                <span className="text-sm font-bold text-voxel-ink">Tool Footprint</span>
                <span className="text-xs font-normal text-voxel-muted whitespace-nowrap">
                    {toolUsage.length} tools
                </span>
            </div>

            {toolUsage.length === 0 ? (
                <p className="text-xs font-normal text-voxel-muted">
                    No external tools configured or called yet.
                </p>
            ) : (
                <div className="flex flex-col gap-2 min-w-0">
                    {toolUsage.map((tool) => (
                        <div key={tool.name} className="flex flex-col gap-1 min-w-0">
                            <div className="flex flex-wrap items-baseline justify-between gap-2 text-xs font-normal text-voxel-muted">
                                <span className="text-voxel-ink truncate min-w-0">
                                    {tool.label}
                                </span>
                                <span className="font-mono tabular-nums whitespace-nowrap">
                                    {tool.count > 0 ? `${tool.count}x` : 'Configured'}
                                </span>
                            </div>
                            <div className="w-full h-1.5 bg-voxel-canvas border border-voxel-bevel-lo">
                                <div
                                    className="h-full bg-info"
                                    style={{
                                        width: `${Math.max(tool.count > 0 ? 10 : 0, tool.pct)}%`,
                                    }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function LatestDecisionPanel({
    recipeId,
    latestDecision,
}: {
    recipeId: string;
    latestDecision: LatestDecisionSnapshot | null;
}) {
    return (
        <div className="voxel-trough bg-voxel-trough p-4 h-full flex flex-col justify-between gap-3 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-2 min-w-0">
                <span className="text-sm font-bold text-voxel-ink">Latest Decision Snapshot</span>
                {latestDecision ? (
                    <span className="text-xs font-normal font-mono text-voxel-muted whitespace-nowrap">
                        {formatDecisionStamp(latestDecision.timestamp, latestDecision.mode)}
                    </span>
                ) : null}
            </div>

            {latestDecision ? (
                <>
                    <div className="flex flex-wrap items-center gap-2">
                        {latestDecision.signals.length > 0 ? (
                            (() => {
                                const seen = new Map<string, number>();
                                return latestDecision.signals.map((sig) => {
                                    const base = `${sig.action}-${sig.ticker}`;
                                    const count = (seen.get(base) ?? 0) + 1;
                                    seen.set(base, count);
                                    return (
                                        <Badge
                                            key={`${base}#${count}`}
                                            colorScheme={
                                                sig.action === 'BUY' ? 'success' : 'warning'
                                            }
                                            size="xs"
                                        >
                                            {sig.action} {sig.ticker}
                                        </Badge>
                                    );
                                });
                            })()
                        ) : (
                            <Badge variant="soft" colorScheme="neutral" size="xs">
                                HOLD
                            </Badge>
                        )}
                    </div>
                    <p className="text-xs font-normal text-voxel-muted break-words line-clamp-3">
                        {latestDecision.excerpt}
                    </p>
                    <div className="mt-auto">
                        {latestDecision.mode === 'live_turn' ? (
                            <Link
                                to="/recipes/live/$recipeId"
                                params={{ recipeId }}
                                className="text-xs font-normal text-accent underline underline-offset-4 hover:text-accent-hover"
                            >
                                Inspect full trace →
                            </Link>
                        ) : (
                            <Link
                                to="/recipes/backtest/$jobId"
                                params={{ jobId: latestDecision.jobId }}
                                className="text-xs font-normal text-accent underline underline-offset-4 hover:text-accent-hover"
                            >
                                Inspect backtest trace →
                            </Link>
                        )}
                    </div>
                </>
            ) : (
                <p className="text-xs font-normal text-voxel-muted">
                    Once a turn completes, the latest signal rationale and trace link appear here.
                </p>
            )}
        </div>
    );
}

/**
 * Deterministic behavioral telemetry & insights block for `/recipes/$recipeId`.
 * Renders four equal-height recessed `.voxel-trough` panels inside one `.voxel-card`.
 */
export function BotBehaviorsBlock({ recipeId, behaviors }: BotBehaviorsBlockProps) {
    const { actionMix, topTickers, exitReasons, toolUsage, latestDecision, source } = behaviors;

    return (
        <Card
            padding="md"
            data-testid="bot-behaviors-block"
            className="flex flex-col gap-4 min-w-0"
        >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-voxel-bevel-hi pb-3 min-w-0">
                <div className="flex flex-col gap-1 min-w-0">
                    <SectionHeading>Behaviors &amp; Insights</SectionHeading>
                    <span className="text-xs font-normal text-voxel-muted">
                        Signal cadence, ticker concentration, exit profile, and tool habits across
                        recent runs.
                    </span>
                </div>
                <Badge variant="soft" colorScheme={sourceBadgeColor(source)} size="xs">
                    {sourceBadgeLabel(source)}
                </Badge>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-4 items-stretch min-w-0">
                <ActionMixPanel actionMix={actionMix} />
                <TickerFocusPanel topTickers={topTickers} exitReasons={exitReasons} />
                <ToolFootprintPanel toolUsage={toolUsage} />
                <LatestDecisionPanel recipeId={recipeId} latestDecision={latestDecision} />
            </div>
        </Card>
    );
}
