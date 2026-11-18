import { Button } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';

interface StudioActionBarProps {
    isTogglingLive: boolean;
    isCurrentlyScheduledLive: boolean;
    liveRecipeId?: string;
    isRunningBacktest: boolean;
    backtestButtonLabel: string;
    unreadAlerts: number;
    onOpenWaitlist: () => void;
    onOpenAlerts: () => void;
    onToggleScheduledLive: () => void;
    onBacktest: () => void;
}

/** Waitlist, alerts, live scheduling, and the backtest action for the studio. */
export function StudioActionBar({
    isTogglingLive,
    isCurrentlyScheduledLive,
    liveRecipeId,
    isRunningBacktest,
    backtestButtonLabel,
    unreadAlerts,
    onOpenWaitlist,
    onOpenAlerts,
    onToggleScheduledLive,
    onBacktest,
}: StudioActionBarProps) {
    return (
        <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" variant="outline" onClick={onOpenWaitlist}>
                ★ Waitlist
            </Button>
            <Button size="sm" variant="outline" onClick={onOpenAlerts}>
                Alerts ({unreadAlerts})
            </Button>
            <Button
                size="sm"
                variant={isCurrentlyScheduledLive ? 'solid' : 'outline'}
                colorScheme={isCurrentlyScheduledLive ? 'success' : 'neutral'}
                onClick={onToggleScheduledLive}
                disabled={isTogglingLive || isRunningBacktest}
                isLoading={isTogglingLive}
            >
                {isCurrentlyScheduledLive ? 'Live: ON (3x/d)' : 'Enable Live (3x/d)'}
            </Button>
            {isCurrentlyScheduledLive && liveRecipeId && (
                <Link
                    to="/recipes/live/$recipeId"
                    params={{ recipeId: liveRecipeId }}
                    className="voxel-btn inline-flex items-center justify-center gap-1 px-3 py-1.5 text-sm font-bold border border-success/50 bg-voxel-surface text-success hover:bg-voxel-elevated rounded-none whitespace-nowrap"
                >
                    Live Status →
                </Link>
            )}
            <Button
                size="sm"
                variant="solid"
                onClick={onBacktest}
                disabled={isRunningBacktest}
                isLoading={isRunningBacktest}
            >
                {backtestButtonLabel}
            </Button>
        </div>
    );
}
