import type * as React from 'react';
import { cn } from '../lib/cn';
import { Button } from '../primitives/Button';

/**
 * EmptyState pattern.
 *
 * Used when a page or list has no data to display.
 */

export interface EmptyStateProps {
    emoji?: string;
    title: string;
    subtitle?: string;
    actions?: Array<{
        label: string;
        href?: string;
        onClick?: () => void;
        variant?: React.ComponentProps<typeof Button>['variant'];
    }>;
    className?: string;
}

export function EmptyState({ emoji, title, subtitle, actions, className }: EmptyStateProps) {
    return (
        <div
            className={cn(
                'flex flex-col items-center justify-center py-12 text-center gap-4',
                className,
            )}
        >
            {emoji && (
                <div className="w-12 h-12 voxel-trough rounded-none flex items-center justify-center">
                    <span className="text-lg">{emoji}</span>
                </div>
            )}
            <div className="flex flex-col items-center gap-1.5 max-w-md">
                <h2 className="text-lg font-bold text-boxel-ink tracking-tight uppercase">
                    {title}
                </h2>
                {subtitle && (
                    <p className="text-xs font-normal text-boxel-muted leading-relaxed">
                        {subtitle}
                    </p>
                )}
            </div>
            {actions && actions.length > 0 && (
                <div className="flex gap-4 flex-wrap justify-center pt-2">
                    {actions.map((action, i) =>
                        action.href ? (
                            <a key={action.href} href={action.href}>
                                <Button type="button" variant={i === 0 ? 'solid' : 'outline'}>
                                    {action.label}
                                </Button>
                            </a>
                        ) : (
                            <Button
                                type="button"
                                key={action.label}
                                variant={i === 0 ? 'solid' : 'outline'}
                                onClick={action.onClick}
                            >
                                {action.label}
                            </Button>
                        ),
                    )}
                </div>
            )}
        </div>
    );
}
