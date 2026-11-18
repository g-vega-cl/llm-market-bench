import * as React from 'react';
import { cn } from '../lib/cn';

/**
 * Button primitive.
 *
 * Variant budget: exactly two variants (`solid`, `outline`).
 * Sizes: `sm`, `md`.
 * Color schemes are semantic, not stylistic variants.
 */

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'solid' | 'outline';
    size?: 'sm' | 'md';
    colorScheme?: 'accent' | 'success' | 'danger' | 'info' | 'warning' | 'neutral';
    isLoading?: boolean;
    leftIcon?: React.ReactNode;
    rightIcon?: React.ReactNode;
}

const colorSchemeMap: Record<string, Record<string, string>> = {
    accent: {
        solid: 'bg-accent text-voxel-trough hover:bg-accent-hover',
        outline: 'border border-accent text-accent hover:bg-accent/10',
    },
    success: {
        solid: 'bg-success text-voxel-trough hover:bg-success/80',
        outline: 'border border-success text-success hover:bg-success/10',
    },
    danger: {
        solid: 'bg-danger text-voxel-trough hover:bg-danger/80',
        outline: 'border border-danger text-danger hover:bg-danger/10',
    },
    info: {
        solid: 'bg-info text-voxel-trough hover:bg-info/80',
        outline: 'border border-info text-info hover:bg-info/10',
    },
    warning: {
        solid: 'bg-warning text-voxel-trough hover:bg-warning/80',
        outline: 'border border-warning text-warning hover:bg-warning/10',
    },
    neutral: {
        solid: 'bg-voxel-elevated text-voxel-ink hover:bg-voxel-surface',
        outline: 'border border-voxel-bevel-hi text-voxel-ink hover:bg-voxel-surface',
    },
};

const sizeMap = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    (
        {
            variant = 'solid',
            size = 'md',
            colorScheme = 'accent',
            isLoading = false,
            leftIcon,
            rightIcon,
            className,
            children,
            disabled,
            ...props
        },
        ref,
    ) => {
        const base =
            'voxel-btn inline-flex items-center justify-center gap-2 font-bold focus:outline-none focus:ring-2 focus:ring-accent/40 disabled:opacity-50 disabled:cursor-not-allowed';
        const colorClasses = colorSchemeMap[colorScheme]?.[variant] ?? colorSchemeMap.accent.solid;
        const sizeClasses = sizeMap[size];

        return (
            <button
                type="button"
                ref={ref}
                className={cn(base, colorClasses, sizeClasses, className)}
                disabled={disabled || isLoading}
                aria-busy={isLoading || undefined}
                {...props}
            >
                {isLoading && (
                    <span
                        aria-hidden="true"
                        data-slot="button-pending-dot"
                        className="inline-block w-2 h-2 rounded-none bg-current animate-pulse motion-reduce:animate-none"
                    />
                )}
                {!isLoading && leftIcon}
                {children}
                {!isLoading && rightIcon}
            </button>
        );
    },
);

Button.displayName = 'Button';
