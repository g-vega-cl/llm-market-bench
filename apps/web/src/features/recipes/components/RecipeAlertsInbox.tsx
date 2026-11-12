import { Badge, Button } from '@llm-market-bench/ui-design-system';
import type { RecipeAlert } from '../types';

interface RecipeAlertsInboxProps {
    alerts: RecipeAlert[];
    onMarkRead?: (alertId: string) => void;
    onClose?: () => void;
}

export function RecipeAlertsInbox({ alerts, onMarkRead, onClose }: RecipeAlertsInboxProps) {
    return (
        <div className="flex flex-col gap-4 border border-border bg-boxel-surface p-4 rounded-none voxel-card">
            <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                    <span className="font-display text-lg font-bold text-foreground">
                        Trade Signals Inbox
                    </span>
                    <Badge variant="outline" size="sm">
                        {alerts.filter((a) => !a.is_read).length} Unread
                    </Badge>
                </div>
                {onClose && (
                    <button
                        type="button"
                        onClick={onClose}
                        className="text-xs font-bold text-muted-foreground hover:text-foreground"
                    >
                        ✕
                    </button>
                )}
            </div>

            {alerts.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-6 text-center">
                    <span className="text-sm font-bold text-muted-foreground">
                        No Live Trade Signals Yet
                    </span>
                    <span className="text-xs font-normal text-muted-foreground">
                        When your live recipes match news catalysts and technical gates, trade
                        signals appear here in real time.
                    </span>
                </div>
            ) : (
                <div className="flex flex-col gap-2">
                    {alerts.map((alert) => (
                        <div
                            key={alert.id}
                            className={`flex flex-col gap-2 border p-3 rounded-none ${
                                alert.is_read
                                    ? 'border-border bg-boxel-canvas text-muted-foreground'
                                    : 'border-primary/50 bg-boxel-surface text-foreground voxel-card'
                            }`}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Badge
                                        colorScheme={alert.action === 'BUY' ? 'success' : 'danger'}
                                        size="sm"
                                    >
                                        {alert.action} {alert.ticker}
                                    </Badge>
                                    <span className="text-xs font-bold">{alert.recipe_name}</span>
                                    <span className="font-mono text-xs text-muted-foreground">
                                        ({alert.timeframe})
                                    </span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="font-mono text-xs text-muted-foreground">
                                        {alert.created_at.replace('T', ' ').slice(0, 16)}
                                    </span>
                                    {!alert.is_read && onMarkRead && (
                                        <Button
                                            size="sm"
                                            variant="ghost"
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
                                    <b className="font-mono tabular-nums text-foreground">
                                        ${alert.entry_price.toFixed(2)}
                                    </b>
                                </span>
                                {alert.target_price && (
                                    <span>
                                        Target:{' '}
                                        <b className="font-mono tabular-nums text-emerald-400">
                                            ${alert.target_price.toFixed(2)}
                                        </b>
                                    </span>
                                )}
                                {alert.stop_loss && (
                                    <span>
                                        Stop:{' '}
                                        <b className="font-mono tabular-nums text-red-400">
                                            ${alert.stop_loss.toFixed(2)}
                                        </b>
                                    </span>
                                )}
                            </div>

                            <div className="voxel-trough p-2 font-mono text-xs text-muted-foreground">
                                {alert.reason}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
