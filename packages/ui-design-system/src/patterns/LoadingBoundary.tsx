import type * as React from 'react';
import { cn } from '../lib/cn';
import { LoadingSpinner } from '../primitives/Button';

/**
 * LoadingBoundary pattern.
 *
 * Wraps content and shows a centered spinner when `isLoading` is true.
 * Optionally renders a skeleton instead of a spinner.
 */

export interface LoadingBoundaryProps {
    isLoading: boolean;
    loadingText?: string;
    minHeight?: string;
    children: React.ReactNode;
    className?: string;
}

export function LoadingBoundary({
    isLoading,
    loadingText,
    minHeight = '60vh',
    children,
    className,
}: LoadingBoundaryProps) {
    if (isLoading) {
        return (
            <div
                className={cn('flex flex-col items-center justify-center gap-3', className)}
                style={{ minHeight }}
            >
                <LoadingSpinner size="md" className="text-accent" />
                {loadingText && <p className="text-sm text-zinc-500">{loadingText}</p>}
            </div>
        );
    }

    return <>{children}</>;
}
