import type * as React from 'react';
import { cn } from '../lib/cn';

/**
 * SectionHeading pattern.
 *
 * A section title with a gradient decorator bar and gradient text.
 * Used across 5 feature sections as a visual section divider.
 */

export interface SectionHeadingProps {
    gradient?: 'electric' | 'success' | 'catalyst' | 'ai';
    children: React.ReactNode;
    className?: string;
}

const decoratorMap: Record<string, string> = {
    electric: 'bg-accent',
    success: 'bg-success',
    catalyst: 'bg-warning',
    ai: 'bg-info',
};

export function SectionHeading({
    gradient = 'electric',
    children,
    className,
}: SectionHeadingProps) {
    return (
        <h2
            className={cn(
                'text-2xl font-black text-boxel-ink flex items-center gap-3 text-display uppercase tracking-tight',
                className,
            )}
        >
            <span
                className={cn(
                    'w-3 h-6 rounded-none voxel-badge shrink-0',
                    decoratorMap[gradient] ?? decoratorMap.electric,
                )}
            />
            <span>{children}</span>
        </h2>
    );
}
