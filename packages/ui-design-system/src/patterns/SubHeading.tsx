import type * as React from 'react';
import { cn } from '../lib/cn';

/**
 * SubHeading pattern.
 *
 * A secondary heading used for sections within a page.
 * Supports an optional divider line and a right-side element (e.g., Badge or count).
 */

export interface SubHeadingProps {
    children: React.ReactNode;
    className?: string;
    rightElement?: React.ReactNode;
    withDivider?: boolean;
    uppercase?: boolean;
}

export function SubHeading({
    children,
    className,
    rightElement,
    withDivider = false,
    uppercase = false,
}: SubHeadingProps) {
    return (
        <div className={cn('flex items-center gap-3 mb-6', className)}>
            <h2
                className={cn(
                    'font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight',
                    uppercase ? 'text-sm uppercase tracking-wider' : 'text-xl',
                )}
            >
                {children}
            </h2>
            {withDivider && (
                <div className="flex-1 border-t border-zinc-200 dark:border-zinc-800" />
            )}
            {rightElement}
        </div>
    );
}
