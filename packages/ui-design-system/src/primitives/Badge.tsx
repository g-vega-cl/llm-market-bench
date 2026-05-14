import * as React from 'react';
import { cn } from '../lib/cn';

/**
 * Badge primitive.
 *
 * Variants: solid, soft, outline
 * Sizes: sm, md
 * Color schemes: accent, success, danger, info, warning, neutral
 * Severity schemes: high, medium (overrides colorScheme)
 * Radius: full (rounded-full), lg (rounded-lg), md (rounded-md)
 */

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    variant?: 'solid' | 'soft' | 'outline';
    size?: 'sm' | 'md';
    colorScheme?: 'accent' | 'success' | 'danger' | 'info' | 'warning' | 'neutral';
    severity?: 'high' | 'medium';
    radius?: 'full' | 'lg' | 'md';
}

const badgeColors: Record<string, Record<string, string>> = {
    accent: {
        solid: 'bg-accent text-white',
        soft: 'bg-accent-light dark:bg-accent/20 text-accent-dark dark:text-accent',
        outline: 'border border-accent/30 dark:border-accent/30 text-accent dark:text-accent',
    },
    success: {
        solid: 'bg-success text-white',
        soft: 'bg-success-light dark:bg-success/20 text-success-dark dark:text-success',
        outline: 'border border-success/30 dark:border-success/30 text-success dark:text-success',
    },
    danger: {
        solid: 'bg-danger text-white',
        soft: 'bg-danger-light dark:bg-danger/20 text-danger-dark dark:text-danger',
        outline: 'border border-danger/30 dark:border-danger/30 text-danger dark:text-danger',
    },
    info: {
        solid: 'bg-info text-white',
        soft: 'bg-info-light dark:bg-info/20 text-info-dark dark:text-info',
        outline: 'border border-info/30 dark:border-info/30 text-info dark:text-info',
    },
    warning: {
        solid: 'bg-warning text-white',
        soft: 'bg-warning-light dark:bg-warning/20 text-warning-dark dark:text-warning',
        outline: 'border border-warning/30 dark:border-warning/30 text-warning dark:text-warning',
    },
    neutral: {
        solid: 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900',
        soft: 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400',
        outline: 'border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400',
    },
    high: {
        solid: 'bg-warning text-black',
        soft: 'bg-warning/10 dark:bg-warning/20 text-warning-dark dark:text-warning',
        outline: 'border border-warning/20 dark:border-warning/30 text-warning dark:text-warning',
    },
    medium: {
        solid: 'bg-info text-white',
        soft: 'bg-info/10 dark:bg-info/20 text-info-dark dark:text-info',
        outline: 'border border-info/20 dark:border-info/30 text-info dark:text-info',
    },
};

const radiusMap: Record<string, string> = {
    full: 'rounded-full',
    lg: 'rounded-lg',
    md: 'rounded-md',
};

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
    (
        {
            variant = 'soft',
            size = 'md',
            colorScheme,
            severity,
            radius = 'full',
            className,
            children,
            ...props
        },
        ref,
    ) => {
        const scheme = severity ?? colorScheme ?? 'neutral';
        const base = 'inline-flex items-center font-medium';
        const sizeClasses =
            size === 'sm'
                ? 'px-2 py-0.5 text-[10px] uppercase tracking-wider'
                : 'px-2.5 py-1 text-xs';
        const colorClasses = badgeColors[scheme]?.[variant] ?? badgeColors.neutral.soft;
        const radiusClasses = radiusMap[radius];

        return (
            <span
                ref={ref}
                className={cn(base, radiusClasses, sizeClasses, colorClasses, className)}
                {...props}
            >
                {children}
            </span>
        );
    },
);

Badge.displayName = 'Badge';
