import * as React from 'react';
import { cn } from '../lib/cn';

/**
 * Voxel Skeleton placeholder primitive.
 *
 * Preserves expected feed, card, and row geometry during cold client loads
 * using sharp Matcha & Cedar recessed trough blocks. Zero rounded corners,
 * zero hardcoded pixel widths, and reduced-motion compliant pulse.
 */

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
    /** Structural shape: single text line, rectangular block, or multi-line card slot. */
    variant?: 'text' | 'block' | 'card';
    /** Number of placeholder lines to render when variant is 'card' or 'text'. */
    lines?: number;
}

const LINE_WIDTHS = ['w-2/3', 'w-full', 'w-4/5', 'w-5/6'] as const;

function renderSkeletonLines(lineCount: number) {
    const lineSpecs = Array.from({ length: lineCount }, (_, pos) => ({
        id: `skeleton-line-${pos + 1}`,
        widthClass: LINE_WIDTHS[pos % LINE_WIDTHS.length],
    }));

    return lineSpecs.map((spec) => (
        <div
            key={spec.id}
            data-slot="skeleton-line"
            className={cn(
                'h-3 rounded-none bg-boxel-elevated animate-pulse motion-reduce:animate-none',
                spec.widthClass,
            )}
        />
    ));
}

export const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
    ({ variant = 'block', lines = 3, className, ...props }, ref) => {
        if (variant === 'card') {
            const lineCount = Math.max(1, lines);
            return (
                <div
                    ref={ref}
                    aria-hidden="true"
                    data-slot="skeleton"
                    className={cn(
                        'voxel-trough rounded-none bg-boxel-trough p-4 flex flex-col gap-3',
                        className,
                    )}
                    {...props}
                >
                    {renderSkeletonLines(lineCount)}
                </div>
            );
        }

        if (variant === 'text') {
            const lineCount = Math.max(1, lines);
            if (lineCount === 1) {
                return (
                    <div
                        ref={ref}
                        aria-hidden="true"
                        data-slot="skeleton"
                        className={cn(
                            'h-3 w-full rounded-none bg-boxel-elevated animate-pulse motion-reduce:animate-none',
                            className,
                        )}
                        {...props}
                    />
                );
            }
            return (
                <div
                    ref={ref}
                    aria-hidden="true"
                    data-slot="skeleton"
                    className={cn('flex flex-col gap-2 w-full', className)}
                    {...props}
                >
                    {renderSkeletonLines(lineCount)}
                </div>
            );
        }

        return (
            <div
                ref={ref}
                aria-hidden="true"
                data-slot="skeleton"
                className={cn(
                    'voxel-trough rounded-none bg-boxel-trough animate-pulse motion-reduce:animate-none h-24 w-full',
                    className,
                )}
                {...props}
            />
        );
    },
);

Skeleton.displayName = 'Skeleton';
