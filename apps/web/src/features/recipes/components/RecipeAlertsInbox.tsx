import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import type { RecipeAlert } from '../types';

interface RecipeAlertsInboxProps {
    alerts: RecipeAlert[];
    onMarkRead?: (alertId: string) => void;
    onClose?: () => void;
}

const ACTION_COLOR_SCHEME: Record<RecipeAlert['action'], 'success' | 'warning' | 'danger'> = {
    BUY: 'success',
    EXIT: 'warning',
    SELL: 'danger',
    HOLD: 'danger',
};

function RecipeAlertCard({
    alert,
    onMarkRead,
}: {
    alert: RecipeAlert;
    onMarkRead?: (alertId: string) => void;
}) {
    return (
        <div
            className={`flex flex-col gap-2 border p-3 rounded-none ${
                alert.is_read
                    ? 'border-voxel-bevel-hi bg-voxel-canvas text-voxel-muted'
                    : 'border-accent/50 bg-voxel-surface text-voxel-ink voxel-card'
            }`}
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Badge colorScheme={ACTION_COLOR_SCHEME[alert.action]} size="sm">
                        {alert.action} {alert.ticker}
                    </Badge>
                    {alert.recipe_id ? (
                        <Link
                            to="/recipes/live/$recipeId/runs"
                            params={{ recipeId: alert.recipe_id }}
                            className="text-sm font-bold text-voxel-ink hover:text-accent underline"
                        >
                            {alert.recipe_name}
                        </Link>
                    ) : (
                        <span className="text-sm font-bold">{alert.recipe_name}</span>
                    )}
                    <span className="font-mono text-xs text-voxel-muted">({alert.timeframe})</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-voxel-muted">
                        {alert.created_at.replace('T', ' ').slice(0, 16)}
                    </span>
                    {!alert.is_read && onMarkRead && (
                        <Button
                            size="sm"
                            variant="outline"
                            colorScheme="neutral"
                            onClick={() => onMarkRead(alert.id)}
                        >
                            Mark Read
                        </Button>
                    )}
                </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs">
                <span>
                    Entry:{' '}
                    <b className="font-mono tabular-nums text-voxel-ink">
                        ${alert.entry_price.toFixed(2)}
                    </b>
                </span>
                {alert.target_price && (
                    <span>
                        Target:{' '}
                        <b className="font-mono tabular-nums text-success">
                            ${alert.target_price.toFixed(2)}
                        </b>
                    </span>
                )}
                {alert.stop_loss && (
                    <span>
                        Stop:{' '}
                        <b className="font-mono tabular-nums text-danger">
                            ${alert.stop_loss.toFixed(2)}
                        </b>
                    </span>
                )}
            </div>

            <div className="voxel-trough p-2 font-mono text-xs text-voxel-muted">
                {alert.reason}
            </div>
        </div>
    );
}

export function RecipeAlertsInbox({ alerts, onMarkRead, onClose }: RecipeAlertsInboxProps) {
    return (
        <div className="flex flex-col gap-4 border border-voxel-bevel-hi bg-voxel-surface p-4 rounded-none voxel-card">
            <div className="flex items-center justify-between border-b border-voxel-bevel-hi pb-3">
                <div className="flex items-center gap-2">
                    <span className="font-display text-sm font-bold text-voxel-ink">
                        Trade Signals Inbox
                    </span>
                    <Badge variant="soft" size="sm">
                        {alerts.filter((a) => !a.is_read).length} Unread
                    </Badge>
                </div>
                {onClose && (
                    <Button
                        type="button"
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                        onClick={onClose}
                    >
                        ✕
                    </Button>
                )}
            </div>

            {alerts.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-6 text-center">
                    <span className="text-sm font-bold text-voxel-muted">
                        No Live Trade Signals Yet
                    </span>
                    <span className="text-xs font-normal text-voxel-muted">
                        When your live recipes match news catalysts and technical gates, trade
                        signals appear here in real time.
                    </span>
                </div>
            ) : (
                <div className="flex flex-col gap-2">
                    {alerts.map((alert) => (
                        <RecipeAlertCard key={alert.id} alert={alert} onMarkRead={onMarkRead} />
                    ))}
                </div>
            )}
        </div>
    );
}
