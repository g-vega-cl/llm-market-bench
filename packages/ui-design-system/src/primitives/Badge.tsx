import * as React from 'react';
import { cn } from '../lib/cn';

/**
 * Badge primitive.
 *
 * Variant budget: exactly two variants (`solid`, `soft`).
 * Sizes: `xs`, `sm`, `md`.
 * Color schemes are semantic, not stylistic variants.
 */

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    variant?: 'solid' | 'soft';
    size?: 'xs' | 'sm' | 'md';
    colorScheme?: 'accent' | 'success' | 'danger' | 'info' | 'warning' | 'neutral';
    showDot?: boolean;
}

const badgeColors: Record<string, Record<string, string>> = {
    accent: {
        solid: 'bg-accent text-voxel-trough',
        soft: 'bg-accent/20 text-accent',
    },
    success: {
        solid: 'bg-success text-voxel-trough',
        soft: 'bg-success/20 text-success',
    },
    danger: {
        solid: 'bg-danger text-voxel-trough',
        soft: 'bg-danger/20 text-danger',
    },
    info: {
        solid: 'bg-info text-voxel-trough',
        soft: 'bg-info/20 text-info',
    },
    warning: {
        solid: 'bg-warning text-voxel-trough',
        soft: 'bg-warning/20 text-warning',
    },
    neutral: {
        solid: 'bg-voxel-elevated text-voxel-ink',
        soft: 'bg-voxel-surface text-voxel-muted',
    },
};

const dotColors: Record<string, string> = {
    accent: 'bg-accent',
    success: 'bg-success',
    danger: 'bg-danger',
    info: 'bg-info',
    warning: 'bg-warning',
    neutral: 'bg-voxel-muted',
};

const solidDotColors: Record<string, string> = {
    accent: 'bg-voxel-trough',
    success: 'bg-voxel-trough',
    danger: 'bg-voxel-trough',
    info: 'bg-voxel-trough',
    warning: 'bg-voxel-trough',
    neutral: 'bg-voxel-muted',
};

const sizeMap = {
    xs: 'px-1.5 py-0.5 text-sm',
    sm: 'px-2 py-0.5 text-sm',
    md: 'px-2.5 py-1 text-sm',
};

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
    (
        {
            variant = 'soft',
            size = 'md',
            colorScheme = 'neutral',
            showDot = false,
            className,
            children,
            ...props
        },
        ref,
    ) => {
        const base =
            'voxel-badge inline-flex items-center gap-1.5 font-bold uppercase tracking-wider rounded-none';
        const colorClasses = badgeColors[colorScheme]?.[variant] ?? badgeColors.neutral.soft;
        const dotColorClass =
            variant === 'solid'
                ? (solidDotColors[colorScheme] ?? 'bg-voxel-muted')
                : (dotColors[colorScheme] ?? dotColors.neutral);

        return (
            <span
                ref={ref}
                data-color-scheme={colorScheme}
                className={cn(base, sizeMap[size], colorClasses, className)}
                {...props}
            >
                {showDot && (
                    <span className={cn('h-1.5 w-1.5 shrink-0 rounded-none', dotColorClass)} />
                )}
                {children}
            </span>
        );
    },
);

Badge.displayName = 'Badge';
