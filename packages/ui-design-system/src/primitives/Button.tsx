import * as React from 'react';
import { cn } from '../lib/cn';

/**
 * Button primitive.
 *
 * Variants: solid, outline, ghost, soft, glass
 * Sizes: sm, md, lg
 * Radius: xl (rounded-xl), full (rounded-full)
 * Gradient: applies a gradient background (solid/glass only)
 */

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'solid' | 'outline' | 'ghost' | 'soft' | 'glass';
    size?: 'sm' | 'md' | 'lg';
    colorScheme?: 'accent' | 'success' | 'danger' | 'info' | 'warning' | 'neutral';
    rounded?: 'xl' | 'full';
    gradient?: boolean;
    isLoading?: boolean;
    leftIcon?: React.ReactNode;
    rightIcon?: React.ReactNode;
}

const colorSchemeMap: Record<string, Record<string, string>> = {
    accent: {
        solid: 'bg-accent text-white hover:bg-accent-hover focus:ring-accent/40',
        outline: 'border-2 border-accent text-accent hover:bg-accent/10 focus:ring-accent/40',
        ghost: 'text-accent hover:bg-accent/10 focus:ring-accent/40',
        soft: 'bg-accent-light text-accent-dark hover:bg-accent/20 focus:ring-accent/40',
        glass: 'bg-accent/10 dark:bg-accent/5 backdrop-blur-md border border-accent/20 text-accent hover:bg-accent/20 dark:hover:bg-accent/10 focus:ring-accent/40',
    },
    success: {
        solid: 'bg-success text-white hover:bg-success/80 focus:ring-success/40',
        outline: 'border-2 border-success text-success hover:bg-success/10 focus:ring-success/40',
        ghost: 'text-success hover:bg-success/10 focus:ring-success/40',
        soft: 'bg-success-light text-success-dark hover:bg-success/20 focus:ring-success/40',
        glass: 'bg-success/10 dark:bg-success/5 backdrop-blur-md border border-success/20 text-success hover:bg-success/20 dark:hover:bg-success/10 focus:ring-success/40',
    },
    danger: {
        solid: 'bg-danger text-white hover:bg-danger/80 focus:ring-danger/40',
        outline: 'border-2 border-danger text-danger hover:bg-danger/10 focus:ring-danger/40',
        ghost: 'text-danger hover:bg-danger/10 focus:ring-danger/40',
        soft: 'bg-danger-light text-danger-dark hover:bg-danger/20 focus:ring-danger/40',
        glass: 'bg-danger/10 dark:bg-danger/5 backdrop-blur-md border border-danger/20 text-danger hover:bg-danger/20 dark:hover:bg-danger/10 focus:ring-danger/40',
    },
    info: {
        solid: 'bg-info text-white hover:bg-info/80 focus:ring-info/40',
        outline: 'border-2 border-info text-info hover:bg-info/10 focus:ring-info/40',
        ghost: 'text-info hover:bg-info/10 focus:ring-info/40',
        soft: 'bg-info-light text-info-dark hover:bg-info/20 focus:ring-info/40',
        glass: 'bg-info/10 dark:bg-info/5 backdrop-blur-md border border-info/20 text-info hover:bg-info/20 dark:hover:bg-info/10 focus:ring-info/40',
    },
    warning: {
        solid: 'bg-warning text-white hover:bg-warning/80 focus:ring-warning/40',
        outline: 'border-2 border-warning text-warning hover:bg-warning/10 focus:ring-warning/40',
        ghost: 'text-warning hover:bg-warning/10 focus:ring-warning/40',
        soft: 'bg-warning-light text-warning-dark hover:bg-warning/20 focus:ring-warning/40',
        glass: 'bg-warning/10 dark:bg-warning/5 backdrop-blur-md border border-warning/20 text-warning hover:bg-warning/20 dark:hover:bg-warning/10 focus:ring-warning/40',
    },
    neutral: {
        solid: 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 focus:ring-zinc-500/40',
        outline:
            'border-2 border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 focus:ring-zinc-500/40',
        ghost: 'text-zinc-900 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 focus:ring-zinc-500/40',
        soft: 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 hover:bg-zinc-200 dark:hover:bg-zinc-700 focus:ring-zinc-500/40',
        glass: 'bg-white/10 dark:bg-white/5 backdrop-blur-md border border-white/20 dark:border-white/10 text-zinc-900 dark:text-zinc-100 hover:bg-white/20 dark:hover:bg-white/10 focus:ring-zinc-500/40',
    },
};

const gradientMap: Record<string, string> = {
    accent: 'gradient-electric text-white hover:opacity-90 focus:ring-accent/40',
    success: 'gradient-success text-white hover:opacity-90 focus:ring-success/40',
    danger: 'gradient-alert text-white hover:opacity-90 focus:ring-danger/40',
    info: 'gradient-ai text-white hover:opacity-90 focus:ring-info/40',
    warning: 'gradient-catalyst text-white hover:opacity-90 focus:ring-warning/40',
    neutral:
        'bg-gradient-to-r from-zinc-600 to-zinc-800 text-white hover:opacity-90 focus:ring-zinc-500/40',
};

const sizeMap = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
};

const roundedMap: Record<string, string> = {
    xl: 'rounded-xl',
    full: 'rounded-full',
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    (
        {
            variant = 'solid',
            size = 'md',
            colorScheme = 'accent',
            rounded = 'xl',
            gradient = false,
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
            'inline-flex items-center justify-center gap-2 font-bold transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
        const colorClasses = gradient
            ? (gradientMap[colorScheme] ?? gradientMap.accent)
            : (colorSchemeMap[colorScheme]?.[variant] ?? colorSchemeMap.accent.solid);
        const sizeClasses = sizeMap[size];
        const roundedClasses = roundedMap[rounded];

        return (
            <button
                type="button"
                ref={ref}
                className={cn(base, roundedClasses, colorClasses, sizeClasses, className)}
                disabled={disabled || isLoading}
                {...props}
            >
                {isLoading && <LoadingSpinner size="sm" className="text-current" />}
                {!isLoading && leftIcon}
                {children}
                {!isLoading && rightIcon}
            </button>
        );
    },
);

Button.displayName = 'Button';

/**
 * Loading spinner sub-component used internally.
 * Exported for standalone usage as well.
 */

export interface LoadingSpinnerProps extends React.SVGAttributes<SVGSVGElement> {
    size?: 'xs' | 'sm' | 'md' | 'lg';
}

export function LoadingSpinner({ size = 'md', className, ...props }: LoadingSpinnerProps) {
    const sizeMapSvg = {
        xs: 'w-3 h-3',
        sm: 'w-4 h-4',
        md: 'w-5 h-5',
        lg: 'w-8 h-8',
    };

    return (
        <svg
            className={cn('animate-spin', sizeMapSvg[size], className)}
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            {...props}
        >
            <title>SVG</title>
            <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
            />
            <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
        </svg>
    );
}
