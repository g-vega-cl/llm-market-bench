import type * as React from 'react';
import { cn } from '../lib/cn';

/**
 * MetricTile pattern.
 *
 * A small stat card with an icon/emoji, label, and value.
 * Used for detail cards inside trade activity, portfolio views, etc.
 */

export interface MetricTileProps {
    icon?: React.ReactNode;
    label: string;
    value: React.ReactNode;
    className?: string;
}

export function MetricTile({ icon, label, value, className }: MetricTileProps) {
    return (
        <div
            className={cn(
                'voxel-trough rounded-none p-3 hover:bg-boxel-elevated transition-colors flex flex-col justify-between gap-1',
                className,
            )}
        >
            <div className="flex items-center gap-1.5">
                {icon && <span className="text-sm">{icon}</span>}
                <span className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                    {label}
                </span>
            </div>
            <div className="text-sm font-bold text-boxel-ink text-display tabular-nums">
                {value}
            </div>
        </div>
    );
}
