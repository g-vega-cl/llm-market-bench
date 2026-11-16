import { Badge, SectionHeading } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import type { RecipeSummaryItem, RecipeUserQuotaStatus } from '../types';

interface RecipeGuideAndQuotaBlockProps {
    quotaStatus?: RecipeUserQuotaStatus | null;
}

export function RecipeGuideAndQuotaBlock({ quotaStatus }: RecipeGuideAndQuotaBlockProps) {
    const btLeft = quotaStatus
        ? Math.max(0, quotaStatus.dailyBacktestLimit - quotaStatus.backtestsLast24h)
        : 2;
    const liveLeft = quotaStatus
        ? Math.max(0, quotaStatus.dailyLiveTurnLimit - quotaStatus.liveTurnsLast24h)
        : 3;

    return (
        <div className="flex flex-col gap-3 min-w-0">
            <div
                data-testid="recipe-quota-strip"
                className="voxel-trough bg-boxel-trough p-3 flex flex-wrap items-center justify-between gap-2 text-xs font-normal text-boxel-muted min-w-0"
            >
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 min-w-0">
                    <Badge variant="soft" colorScheme="accent" size="xs">
                        {quotaStatus?.tier === 'beta_starter' || !quotaStatus
                            ? 'FREE BETA STARTER'
                            : quotaStatus.tier.toUpperCase()}
                    </Badge>
                    <span className="flex flex-wrap items-baseline gap-1 min-w-0">
                        <span className="whitespace-nowrap">
                            Backtests: {btLeft}/{quotaStatus?.dailyBacktestLimit ?? 2} left today
                        </span>
                        <span className="whitespace-nowrap">
                            (max {quotaStatus?.maxConcurrentBacktests ?? 1} active)
                        </span>
                    </span>
                    <span className="whitespace-nowrap font-mono tabular-nums text-boxel-ink">
                        • Live Turns: {liveLeft}/{quotaStatus?.dailyLiveTurnLimit ?? 3} left today
                    </span>
                    <span className="whitespace-nowrap font-mono tabular-nums text-boxel-ink">
                        • Scheduled Live: {quotaStatus?.activeLiveRecipes ?? 0}/
                        {quotaStatus?.maxLiveRecipes ?? 1}
                    </span>
                </div>
                <span className="whitespace-nowrap font-mono tabular-nums text-boxel-muted">
                    Global Backtest Queue: {quotaStatus?.globalPendingBacktests ?? 0}/
                    {quotaStatus?.globalQueueCap ?? 20}
                </span>
            </div>

            <div className="voxel-trough bg-boxel-trough p-4 grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-4 min-w-0">
                <div className="flex flex-col gap-1 min-w-0">
                    <span className="text-sm font-bold text-boxel-ink">
                        How 2-Week PIT Backtests Work (strata-auto-go)
                    </span>
                    <span className="text-xs font-normal text-boxel-muted leading-relaxed">
                        Simulates a random 10-trading-day window (30 slots at 09:30 / 12:30 / 15:30
                        ET since Feb 9, 2026) one job at a time globally. Tools strictly enforce
                        &lt;= slot_time data (zero web_search or lookahead), Long-Only sizing (max 4
                        positions × 25% equity), and 5 bps slippage with open trades settled at end
                        of window.
                    </span>
                </div>
                <div className="flex flex-col gap-1 min-w-0">
                    <span className="text-sm font-bold text-boxel-ink">
                        How Live Paper Execution Works (auto-go)
                    </span>
                    <span className="text-xs font-normal text-boxel-muted leading-relaxed">
                        Runs independently on clvg.uk auto-go against your strategy’s isolated
                        $10,000 paper ledger, so live turns never stall behind queued backtests. Use
                        Run Live Now to test one slot immediately, or enable Scheduled Live (3x/day
                        ET) on up to 1 saved strategy to log automatic alerts.
                    </span>
                </div>
            </div>
        </div>
    );
}

export function BacktestMethodologyBlock() {
    return (
        <div className="voxel-trough bg-boxel-trough p-4 flex flex-col gap-3 min-w-0">
            <SectionHeading gradient="electric">How To Read This Backtest</SectionHeading>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-3 min-w-0">
                <div className="border border-boxel-bevel-lo bg-boxel-surface p-3 flex flex-col gap-1 min-w-0">
                    <span className="text-sm font-bold text-boxel-ink">
                        Point-in-Time Intraday Slots
                    </span>
                    <span className="text-xs font-normal text-boxel-muted leading-relaxed">
                        Each tile is one ET market checkpoint (09:30, 12:30, 15:30 ET). Click any
                        settled tile to inspect the exact hydrated prompt, tool calls, internal
                        reasoning, and output. A HOLD ([]) session still captures all research tool
                        rounds.
                    </span>
                </div>
                <div className="border border-boxel-bevel-lo bg-boxel-surface p-3 flex flex-col gap-1 min-w-0">
                    <span className="text-sm font-bold text-boxel-ink">
                        Open Positions vs Closed Trades
                    </span>
                    <span className="text-xs font-normal text-boxel-muted leading-relaxed">
                        Active BUY fills stay in Current Portfolio (and show as OPEN rows in
                        Executed Trades) until an explicit EXIT signal (SIGNAL_EXIT) or final
                        liquidation at slot 30 (END_OF_WINDOW).
                    </span>
                </div>
                <div className="border border-boxel-bevel-lo bg-boxel-surface p-3 flex flex-col gap-1 min-w-0">
                    <span className="text-sm font-bold text-boxel-ink">
                        Net Slippage vs Midpoint
                    </span>
                    <span className="text-xs font-normal text-boxel-muted leading-relaxed">
                        Spread &amp; Slippage Net deducts 5 bps (0.05%) on every entry and exit.
                        Toggle Midpoint to inspect raw price movement before execution friction.
                    </span>
                </div>
            </div>
        </div>
    );
}

export function SavedRecipesStrip({
    recipes,
    activeRecipeId,
}: {
    recipes: RecipeSummaryItem[];
    activeRecipeId?: string;
}) {
    if (recipes.length === 0) return null;
    return (
        <div className="flex flex-wrap items-center gap-2 voxel-trough bg-boxel-trough p-3">
            <span className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                My Strategies:
            </span>
            {recipes.slice(0, 6).map((item) => {
                const isActive = activeRecipeId === item.id;
                return (
                    <Link
                        key={item.id}
                        to="/recipes"
                        search={{ recipeId: item.id }}
                        className={`voxel-btn inline-flex items-center gap-2 px-2 py-1 text-xs font-normal border rounded-none max-w-full min-w-0 ${
                            isActive
                                ? 'border-accent bg-accent text-boxel-trough'
                                : 'border-boxel-bevel-hi bg-boxel-surface text-boxel-ink hover:bg-boxel-elevated'
                        }`}
                    >
                        <span className="truncate min-w-0">{item.name}</span>
                        {item.is_live && (
                            <Badge variant="soft" colorScheme="success" size="xs">
                                LIVE 3x/d
                            </Badge>
                        )}
                    </Link>
                );
            })}
        </div>
    );
}
