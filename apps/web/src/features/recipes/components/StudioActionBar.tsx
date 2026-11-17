import { Button } from '@llm-market-bench/ui-design-system';

interface StudioActionBarProps {
    isBusy: boolean;
    isTogglingLive: boolean;
    isCurrentlyScheduledLive: boolean;
    isRunningLiveTurn: boolean;
    isRunningBacktest: boolean;
    backtestButtonLabel: string;
    unreadAlerts: number;
    onOpenWaitlist: () => void;
    onOpenAlerts: () => void;
    onToggleScheduledLive: () => void;
    onRunLive: () => void;
    onBacktest: () => void;
}

/** Waitlist, alerts, live scheduling, and the two run actions for the studio. */
export function StudioActionBar({
    isBusy,
    isTogglingLive,
    isCurrentlyScheduledLive,
    isRunningLiveTurn,
    isRunningBacktest,
    backtestButtonLabel,
    unreadAlerts,
    onOpenWaitlist,
    onOpenAlerts,
    onToggleScheduledLive,
    onRunLive,
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
                disabled={isBusy}
                isLoading={isTogglingLive}
            >
                {isCurrentlyScheduledLive ? 'Scheduled Live: ON (3x/d)' : 'Schedule Live (3x/d)'}
            </Button>
            <Button size="sm" variant="outline" onClick={onRunLive} disabled={isBusy}>
                {isRunningLiveTurn ? 'Running Live...' : '▶ Run Live'}
            </Button>
            <Button
                size="sm"
                variant="solid"
                onClick={onBacktest}
                disabled={isBusy}
                isLoading={isRunningBacktest}
            >
                {backtestButtonLabel}
            </Button>
        </div>
    );
}
