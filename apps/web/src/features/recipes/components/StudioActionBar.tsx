import { Button } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { TurboButton } from './TurboButton';

interface StudioActionBarProps {
    isTogglingLive: boolean;
    isCurrentlyScheduledLive: boolean;
    liveRecipeId?: string;
    turboExpiresAt?: string | null;
    turboUsedToday?: boolean;
    isActivatingTurbo?: boolean;
    isRunningBacktest: boolean;
    backtestButtonLabel: string;
    unreadAlerts: number;
    onOpenWaitlist: () => void;
    onOpenAlerts: () => void;
    onToggleScheduledLive: () => void;
    onActivateTurbo?: () => void;
    onBacktest: () => void;
}

/** Waitlist, alerts, live scheduling, Turbo boost, and backtest actions for the studio. */
export function StudioActionBar({
    isTogglingLive,
    isCurrentlyScheduledLive,
    liveRecipeId,
    turboExpiresAt,
    turboUsedToday,
    isActivatingTurbo,
    isRunningBacktest,
    backtestButtonLabel,
    unreadAlerts,
    onOpenWaitlist,
    onOpenAlerts,
    onToggleScheduledLive,
    onActivateTurbo,
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
                disabled={isTogglingLive || isRunningBacktest || isActivatingTurbo}
                isLoading={isTogglingLive}
            >
                {isCurrentlyScheduledLive ? 'Live: ON (30m)' : 'Enable Live (30m)'}
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
            {isCurrentlyScheduledLive && onActivateTurbo && (
                <TurboButton
                    turboExpiresAt={turboExpiresAt}
                    turboUsedToday={turboUsedToday}
                    isActivating={isActivatingTurbo}
                    disabled={isTogglingLive || isRunningBacktest}
                    onActivate={onActivateTurbo}
                />
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
