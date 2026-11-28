import { Badge, Button, SectionHeading } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import type {
    BacktestError,
    BacktestResultData,
    RecipeJobRecord,
    RecipeSummaryItem,
    RecipeUserQuotaStatus,
} from '../types';
import { isQuotaLimitMessage } from '../utils/live-studio-helpers';
import { isTurboActive } from '../utils/market-hours';
import { US_DATA_COVERAGE_COPY } from './DataCoverageNote';

export function resolveBacktestButtonLabel(
    isStarting: boolean,
    quotaStatus?: RecipeUserQuotaStatus | null,
): string {
    if (isStarting) return 'Starting Backtest...';
    if (quotaStatus && quotaStatus.activeBacktests >= quotaStatus.maxConcurrentBacktests) {
        return `Backtest (${quotaStatus.activeBacktests} Active)`;
    }
    // Tokens are the spend meter; show the price of the click before it happens.
    if (typeof quotaStatus?.tokenBalance === 'number') {
        if (quotaStatus.tokenBalance <= 0) return 'Backtest (0 tokens left)';
        return '▶ Backtest (1 token)';
    }
    if (quotaStatus && quotaStatus.backtestsLast24h >= quotaStatus.dailyBacktestLimit) {
        return `Backtest (0/${quotaStatus.dailyBacktestLimit} Left)`;
    }
    return '▶ Backtest (Random 2W)';
}

export function RecipeExecutionAlert({
    message,
    kind,
    backtestJobId,
    onRequestCapacity,
}: {
    message: string;
    kind: 'quota' | 'navigation' | 'execution';
    backtestJobId?: string;
    onRequestCapacity: () => void;
}) {
    return (
        <div
            role="alert"
            className="border border-danger bg-voxel-surface p-3 flex flex-wrap items-center justify-between gap-2 text-xs font-normal text-danger rounded-none min-w-0"
        >
            <span className="min-w-0 break-words">{message}</span>
            <div className="flex flex-wrap items-center gap-2 shrink-0 max-w-full min-w-0">
                {backtestJobId && (
                    <Link
                        to="/recipes/backtest/$jobId"
                        params={{ jobId: backtestJobId }}
                        className="voxel-btn inline-flex items-center px-3 py-1.5 text-sm font-bold border border-voxel-bevel-hi bg-voxel-elevated text-voxel-ink rounded-none"
                    >
                        Open Backtest Run →
                    </Link>
                )}
                {kind === 'quota' && (
                    <Button size="sm" variant="outline" onClick={onRequestCapacity}>
                        Request Capacity
                    </Button>
                )}
            </div>
        </div>
    );
}

export function StudioAlertSlot({
    backtestError,
    scheduleError,
    onRequestCapacity,
}: {
    backtestError: BacktestError | null;
    scheduleError: string | null;
    onRequestCapacity: () => void;
}) {
    if (backtestError) {
        return (
            <RecipeExecutionAlert
                message={backtestError.message}
                kind={backtestError.kind}
                backtestJobId={backtestError.backtestJobId}
                onRequestCapacity={onRequestCapacity}
            />
        );
    }
    if (scheduleError) {
        return (
            <RecipeExecutionAlert
                message={scheduleError}
                kind={isQuotaLimitMessage(scheduleError) ? 'quota' : 'execution'}
                onRequestCapacity={onRequestCapacity}
            />
        );
    }
    return null;
}

interface RecipeQuotaStripProps {
    quotaStatus?: RecipeUserQuotaStatus | null;
    onRequestCapacity?: () => void;
}

/** Compact 1-line quota summary strip for the dashboard and studio. */
export function RecipeQuotaStrip({ quotaStatus, onRequestCapacity }: RecipeQuotaStripProps) {
    return (
        <div
            data-testid="recipe-quota-strip"
            className="voxel-trough bg-voxel-trough p-3 flex flex-wrap items-center justify-between gap-2 text-xs font-normal text-voxel-muted min-w-0"
        >
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 min-w-0">
                <Badge variant="soft" colorScheme="accent" size="xs">
                    {quotaStatus?.tier === 'beta_starter' || !quotaStatus
                        ? 'FREE BETA STARTER'
                        : quotaStatus.tier.toUpperCase()}
                </Badge>
                <span className="flex flex-wrap items-baseline gap-1 min-w-0">
                    <span
                        data-testid="token-balance"
                        className="whitespace-nowrap font-mono tabular-nums text-voxel-ink"
                    >
                        Tokens: {quotaStatus?.tokenBalance ?? 0} of {quotaStatus?.tokenGrant ?? 15}
                    </span>
                    <span className="whitespace-nowrap">
                        ({quotaStatus?.tokenRefillLabel ?? 'refills weekly'})
                    </span>
                </span>
                <span className="whitespace-nowrap font-mono tabular-nums text-voxel-ink">
                    • Live bots: {quotaStatus?.activeLiveRecipes ?? 0}/
                    {quotaStatus?.maxLiveRecipes ?? 3}
                </span>
            </div>
            <div className="flex flex-wrap items-center gap-3 min-w-0">
                <span className="whitespace-nowrap font-mono tabular-nums text-voxel-muted">
                    Global Backtest Queue: {quotaStatus?.globalPendingBacktests ?? 0}/
                    {quotaStatus?.globalQueueCap ?? 20} (all users)
                </span>
                {onRequestCapacity && (
                    <Button size="sm" variant="outline" onClick={onRequestCapacity}>
                        Request more capacity
                    </Button>
                )}
            </div>
        </div>
    );
}

interface RecipeGuideAndQuotaBlockProps {
    quotaStatus?: RecipeUserQuotaStatus | null;
}

export function RecipeGuideAndQuotaBlock({ quotaStatus }: RecipeGuideAndQuotaBlockProps) {
    return (
        <div className="flex flex-col gap-3 min-w-0">
            <RecipeQuotaStrip quotaStatus={quotaStatus} />

            <div className="voxel-trough bg-voxel-trough p-4 grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-4 min-w-0">
                <div className="flex flex-col gap-1 min-w-0">
                    <span className="text-sm font-bold text-voxel-ink">
                        How 2-Week PIT Backtests Work (strata-auto-go)
                    </span>
                    <span className="text-xs font-normal text-voxel-muted leading-relaxed">
                        Simulates a random 10-trading-day window (30 slots at 09:30 / 12:30 / 15:30
                        ET since Feb 9, 2026) one job at a time globally. Tools strictly enforce
                        &lt;= slot_time data (zero web_search or lookahead), Long-Only sizing (max 4
                        positions × 25% equity), and 5 bps slippage with open trades settled at end
                        of window.
                    </span>
                </div>
                <div className="flex flex-col gap-1 min-w-0">
                    <span className="text-sm font-bold text-voxel-ink">
                        How Live Paper Execution Works (auto-go)
                    </span>
                    <span className="text-xs font-normal text-voxel-muted leading-relaxed">
                        Runs independently on clvg.uk auto-go against your strategy’s isolated
                        $10,000 paper ledger, so live turns never stall behind queued backtests.
                        Enable Live (30m) on up to 3 saved strategies to run every 30 minutes during
                        US market hours (09:30–16:00 ET), plus 1 free daily Turbo boost for 5-minute
                        runs over 1 hour.
                    </span>
                </div>
            </div>
        </div>
    );
}

export function BacktestMethodologyBlock() {
    return (
        <div className="voxel-trough bg-voxel-trough p-4 flex flex-col gap-3 min-w-0">
            <SectionHeading>How To Read This Backtest</SectionHeading>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-3 min-w-0">
                <div className="border border-voxel-bevel-lo bg-voxel-surface p-3 flex flex-col gap-1 min-w-0">
                    <span className="text-sm font-bold text-voxel-ink">
                        Point-in-Time Intraday Slots
                    </span>
                    <span className="text-xs font-normal text-voxel-muted leading-relaxed">
                        Each tile is one ET market checkpoint (09:30, 12:30, 15:30 ET). Click any
                        settled tile to inspect the exact hydrated prompt, tool calls, internal
                        reasoning, and output. A HOLD ([]) session still captures all research tool
                        rounds.
                    </span>
                </div>
                <div className="border border-voxel-bevel-lo bg-voxel-surface p-3 flex flex-col gap-1 min-w-0">
                    <span className="text-sm font-bold text-voxel-ink">
                        Open Positions vs Closed Trades
                    </span>
                    <span className="text-xs font-normal text-voxel-muted leading-relaxed">
                        Active BUY fills stay in Current Portfolio (and show as OPEN rows in
                        Executed Trades) until an explicit EXIT signal (SIGNAL_EXIT) or final
                        liquidation at slot 30 (END_OF_WINDOW).
                    </span>
                </div>
                <div className="border border-voxel-bevel-lo bg-voxel-surface p-3 flex flex-col gap-1 min-w-0">
                    <span className="text-sm font-bold text-voxel-ink">
                        Net Slippage vs Midpoint
                    </span>
                    <span className="text-xs font-normal text-voxel-muted leading-relaxed">
                        Spread &amp; Slippage Net deducts 5 bps (0.05%) on every entry and exit.
                        Toggle Midpoint to inspect raw price movement before execution friction.
                    </span>
                </div>
                <div
                    data-testid="backtest-data-coverage"
                    className="border border-voxel-bevel-lo bg-voxel-surface p-3 flex flex-col gap-1 min-w-0"
                >
                    <span className="text-sm font-bold text-voxel-ink">Data Coverage</span>
                    <span className="text-xs font-normal text-voxel-muted leading-relaxed">
                        {US_DATA_COVERAGE_COPY}
                    </span>
                </div>
            </div>
        </div>
    );
}

export function SavedRecipesStrip({
    recipes,
    activeRecipeId,
    onRemove,
    removingId,
    errorMessage,
}: {
    recipes: RecipeSummaryItem[];
    activeRecipeId?: string;
    onRemove?: (recipe: RecipeSummaryItem) => void;
    /** Strategy currently being removed: only that control renders a pending state. */
    removingId?: string | null;
    errorMessage?: string | null;
}) {
    if (recipes.length === 0) return null;
    return (
        <div className="flex flex-col gap-2 voxel-trough bg-voxel-trough p-3 min-w-0">
            <span className="text-sm font-bold text-voxel-muted uppercase tracking-wider">
                My Strategies:
            </span>
            <div className="flex flex-wrap items-center gap-2 min-w-0">
                {recipes.map((item) => {
                    const isActive = activeRecipeId === item.id;
                    return (
                        <div
                            key={item.id}
                            className="inline-flex items-center gap-1 min-w-0 max-w-full"
                        >
                            <Link
                                to="/recipes"
                                search={{ recipeId: item.id }}
                                className={`voxel-btn inline-flex items-center gap-2 px-2 py-1 text-xs font-normal border rounded-none max-w-full min-w-0 ${
                                    isActive
                                        ? 'border-accent bg-accent text-voxel-trough'
                                        : 'border-voxel-bevel-hi bg-voxel-surface text-voxel-ink hover:bg-voxel-elevated'
                                }`}
                            >
                                <span className="truncate min-w-0">{item.name}</span>
                                {item.is_live && (
                                    <Badge
                                        variant={isActive ? 'solid' : 'soft'}
                                        colorScheme={
                                            isActive
                                                ? 'neutral'
                                                : isTurboActive(item.turbo_expires_at)
                                                  ? 'accent'
                                                  : 'success'
                                        }
                                        size="xs"
                                        suppressHydrationWarning
                                    >
                                        {isTurboActive(item.turbo_expires_at)
                                            ? 'TURBO 5m'
                                            : 'LIVE 30m'}
                                    </Badge>
                                )}
                            </Link>
                            {item.is_live && (
                                <Link
                                    to="/recipes/live/$recipeId/runs"
                                    params={{ recipeId: item.id }}
                                    className="voxel-btn inline-flex items-center gap-1 px-2 py-1 text-xs font-normal border border-success/50 bg-voxel-surface text-success hover:bg-voxel-elevated rounded-none whitespace-nowrap"
                                >
                                    Live Status →
                                </Link>
                            )}
                            {onRemove && (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    colorScheme="danger"
                                    aria-label={`Remove ${item.name} from My Strategies`}
                                    isLoading={removingId === item.id}
                                    disabled={Boolean(removingId)}
                                    onClick={() => onRemove(item)}
                                >
                                    Remove
                                </Button>
                            )}
                        </div>
                    );
                })}
            </div>
            {errorMessage && (
                <span role="alert" className="text-xs font-normal text-danger">
                    {errorMessage}
                </span>
            )}
        </div>
    );
}

export function RecentBacktestsStrip({ recentBacktests }: { recentBacktests: RecipeJobRecord[] }) {
    if (recentBacktests.length === 0) return null;
    return (
        <div className="flex flex-wrap items-center gap-2 voxel-trough bg-voxel-trough p-3">
            <span className="text-sm font-bold text-voxel-muted uppercase tracking-wider">
                Recent Backtests:
            </span>
            {recentBacktests.slice(0, 5).map((run) => {
                const bt =
                    run.result_json &&
                    (!('mode' in run.result_json) || run.result_json.mode !== 'live_turn')
                        ? (run.result_json as BacktestResultData)
                        : null;
                const label =
                    run.status === 'completed' && bt && typeof bt.total_return_pct_net === 'number'
                        ? `${bt.total_return_pct_net >= 0 ? '+' : ''}${bt.total_return_pct_net.toFixed(2)}%`
                        : `${run.status.toUpperCase()} (${run.progress_pct}%)`;
                return (
                    <Link
                        key={run.id}
                        to="/recipes/backtest/$jobId"
                        params={{ jobId: run.id }}
                        className="voxel-btn inline-flex items-center gap-2 px-2 py-1 text-xs font-mono border border-voxel-bevel-hi bg-voxel-surface text-voxel-ink hover:bg-voxel-elevated rounded-none"
                    >
                        <span>{run.id.slice(0, 8)}</span>
                        <span className="text-accent">{label}</span>
                    </Link>
                );
            })}
        </div>
    );
}
