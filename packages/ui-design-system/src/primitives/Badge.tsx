import * as React from 'react';
import { cn } from '../lib/cn';

/**
 * Badge primitive.
 *
 * Variants: solid, soft, outline, dot
 * Sizes: xs, sm, md
 * Color schemes: accent, success, danger, info, warning, neutral
 * Severity schemes: high, medium (overrides colorScheme)
 * Radius: full (rounded-full), lg (rounded-lg), md (rounded-md)
 */

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    variant?: 'solid' | 'soft' | 'outline' | 'dot';
    size?: 'xs' | 'sm' | 'md';
    colorScheme?: 'accent' | 'success' | 'danger' | 'info' | 'warning' | 'neutral';
    severity?: 'high' | 'medium';
    radius?: 'full' | 'lg' | 'md';
}

const badgeColors: Record<string, Record<string, string>> = {
    accent: {
        solid: 'bg-accent text-white',
        soft: 'bg-accent/20 text-accent',
        outline: 'border border-accent/30 text-accent',
        dot: 'text-zinc-450',
    },
    success: {
        solid: 'bg-success text-zinc-950',
        soft: 'bg-success/20 text-success',
        outline: 'border border-success/30 text-success',
        dot: 'text-zinc-450',
    },
    danger: {
        solid: 'bg-danger text-white',
        soft: 'bg-danger/20 text-danger',
        outline: 'border border-danger/30 text-danger',
        dot: 'text-zinc-450',
    },
    info: {
        solid: 'bg-info text-white',
        soft: 'bg-info/20 text-info',
        outline: 'border border-info/30 text-info',
        dot: 'text-zinc-450',
    },
    warning: {
        solid: 'bg-warning text-zinc-950',
        soft: 'bg-warning/20 text-warning',
        outline: 'border border-warning/30 text-warning',
        dot: 'text-zinc-450',
    },
    neutral: {
        solid: 'bg-zinc-800 dark:bg-zinc-100 text-white dark:text-zinc-950',
        soft: 'bg-zinc-100 dark:bg-zinc-800/40 text-zinc-600 dark:text-zinc-400',
        outline: 'border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400',
        dot: 'text-zinc-500',
    },
    high: {
        solid: 'bg-warning text-zinc-950',
        soft: 'bg-warning/20 text-warning',
        outline: 'border border-warning/30 text-warning',
        dot: 'text-zinc-450',
    },
    medium: {
        solid: 'bg-info text-white',
        soft: 'bg-info/20 text-info',
        outline: 'border border-info/30 text-info',
        dot: 'text-zinc-450',
    },
};

const dotColors: Record<string, string> = {
    accent: 'bg-accent',
    success: 'bg-success',
    danger: 'bg-danger',
    info: 'bg-info',
    warning: 'bg-warning',
    neutral: 'bg-zinc-400',
    high: 'bg-warning',
    medium: 'bg-info',
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
        const base = 'inline-flex items-center font-black uppercase tracking-widest';
        const sizeClasses = {
            xs: 'px-1.5 py-0.5 text-[9px]',
            sm: 'px-2 py-0.5 text-[10px]',
            md: 'px-2.5 py-1 text-xs',
        }[size];
        const colorClasses = badgeColors[scheme]?.[variant] ?? badgeColors.neutral.soft;
        const radiusClasses = radiusMap[radius];

        return (
            <span
                ref={ref}
                className={cn(base, radiusClasses, sizeClasses, colorClasses, className)}
                {...props}
            >
                {variant === 'dot' && (
                    <span
                        className={cn(
                            'mr-1.5 h-1.5 w-1.5 rounded-full',
                            dotColors[scheme] ?? dotColors.neutral,
                        )}
                    />
                )}
                {children}
            </span>
        );
    },
);

Badge.displayName = 'Badge';
