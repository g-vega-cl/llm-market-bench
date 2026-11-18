import { Button } from '@llm-market-bench/ui-design-system';

interface StudioActionBarProps {
    isTogglingLive: boolean;
    isCurrentlyScheduledLive: boolean;
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
