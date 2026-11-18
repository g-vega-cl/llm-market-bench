import type * as React from 'react';
import { cn } from '../lib/cn';

/**
 * SectionHeading pattern.
 *
 * A section title with a single accent decorator bar.
 * Variant budget: one decorator color (`bg-accent`).
 */

export interface SectionHeadingProps {
    children: React.ReactNode;
    className?: string;
}

export function SectionHeading({ children, className }: SectionHeadingProps) {
    return (
        <h2
            className={cn(
                'text-lg font-bold text-voxel-ink flex items-center gap-2.5 text-display uppercase tracking-tight',
                className,
            )}
        >
            <span className="w-3 h-6 rounded-none voxel-badge shrink-0 bg-accent" />
            <span>{children}</span>
        </h2>
    );
}
