import type * as React from 'react';
import { cn } from '../lib/cn';

/**
 * PageLayout primitive.
 *
 * Standard content wrapper with consistent padding and max-width.
 * Pages add their own outer divs for background color, min-h-screen, etc.
 */

export interface PageLayoutProps {
    children: React.ReactNode;
    className?: string;
    maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
    withPadding?: boolean;
    /** Vertical rhythm. `tight` brings the first block under the navbar. */
    paddingY?: 'default' | 'tight';
}

const maxWidthMap = {
    sm: 'max-w-3xl',
    md: 'max-w-5xl',
    lg: 'max-w-7xl',
    xl: 'max-w-[90rem]',
    full: 'max-w-none',
};

const paddingYMap = {
    default: 'py-8 md:py-12',
    tight: 'py-3 md:py-4',
};

export function PageLayout({
    children,
    className,
    maxWidth = 'lg',
    withPadding = true,
    paddingY = 'default',
}: PageLayoutProps) {
    return (
        <div
            className={cn(
                'mx-auto w-full',
                maxWidthMap[maxWidth],
                withPadding && cn('px-6 md:px-12', paddingYMap[paddingY]),
                className,
            )}
        >
            {children}
        </div>
    );
}
