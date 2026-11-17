import type * as React from 'react';
import { cn } from '../lib/cn';
import { Skeleton } from '../primitives/Skeleton';

/**
 * LoadingBoundary pattern.
 *
 * Wraps content and renders a layout-preserving Voxel skeleton placeholder
 * (or a caller-supplied layout-matched `fallback`) while `isLoading` is true.
 */

export interface LoadingBoundaryProps {
    isLoading: boolean;
    loadingText?: string;
    fallback?: React.ReactNode;
    children: React.ReactNode;
    className?: string;
}

export function LoadingBoundary({
    isLoading,
    loadingText,
    fallback,
    children,
    className,
}: LoadingBoundaryProps) {
    if (isLoading) {
        return (
            <div
                role="status"
                aria-busy="true"
                aria-label={loadingText ?? 'Loading content'}
                className={cn('flex flex-col gap-4 w-full min-w-0', className)}
            >
                {fallback ?? (
                    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-6 items-stretch">
                        <Skeleton variant="card" lines={3} />
                        <Skeleton variant="card" lines={3} />
                        <Skeleton variant="card" lines={3} />
                    </div>
                )}
            </div>
        );
    }

    return <>{children}</>;
}
