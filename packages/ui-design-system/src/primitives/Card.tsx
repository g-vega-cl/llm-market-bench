import * as React from 'react';
import { cn } from '../lib/cn';

/**
 * Card primitive.
 *
 * Composable: Card, CardHeader, CardBody, CardFooter.
 * Variants: default, outlined, glass
 * Gradient backgrounds: electric, success, alert, catalyst, ai
 */

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: 'default' | 'outlined' | 'glass' | 'glass-warning';
    colorScheme?: 'neutral' | 'success' | 'warning' | 'danger' | 'info';
    padding?: 'none' | 'sm' | 'md' | 'lg';
    radius?: 'xl' | '2xl' | '3xl' | 'none';
    gradient?: 'electric' | 'success' | 'alert' | 'catalyst' | 'ai';
    isHoverable?: boolean;
}

const cardVariants = {
    default: 'bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm',
    outlined: 'bg-transparent border border-zinc-200 dark:border-zinc-800',
    glass: 'bg-glass-dark/50 backdrop-blur-[24px] border border-white/10 shadow-[0_4px_15px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.1)] hover:border-white/20 hover:bg-glass-dark/70',
    'glass-warning':
        'bg-yellow-900/20 backdrop-blur-[24px] border border-yellow-500/40 shadow-[0_0_15px_rgba(234,179,8,0.15),inset_0_1px_1px_rgba(255,255,255,0.2)] hover:border-yellow-500/50 hover:bg-yellow-900/30',
};

const glassColorSchemes = {
    neutral:
        'border-sky-500/35 hover:border-sky-500/45 bg-sky-950/10 hover:bg-sky-950/20 shadow-[0_4px_15px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.10),0_0_18px_rgba(56,189,248,0.18)]',
    success:
        'border-emerald-500/45 hover:border-emerald-500/55 bg-emerald-950/10 hover:bg-emerald-950/20 shadow-[0_4px_15px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.12),0_0_22px_rgba(52,211,153,0.22)]',
    warning:
        'border-yellow-500/40 hover:border-yellow-500/50 bg-yellow-900/20 hover:bg-yellow-900/30 shadow-[0_0_15px_rgba(234,179,8,0.15),inset_0_1px_1px_rgba(255,255,255,0.2),0_0_22px_rgba(245,158,11,0.30)]',
    danger: 'border-red-500/55 hover:border-red-500/65 bg-red-950/10 hover:bg-red-950/20 shadow-[0_4px_15px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.08),0_0_22px_rgba(220,38,38,0.28)]',
    info: 'border-rose-500/45 hover:border-rose-500/55 bg-rose-950/10 hover:bg-rose-950/20 shadow-[0_4px_15px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.10),0_0_22px_rgba(244,63,94,0.22)]',
};

const radiusMap = {
    none: 'rounded-none',
    xl: 'rounded-xl',
    '2xl': 'rounded-2xl',
    '3xl': 'rounded-3xl',
};

const gradientMap: Record<string, string> = {
    electric: 'gradient-electric',
    success: 'gradient-success',
    alert: 'gradient-alert',
    catalyst: 'gradient-catalyst',
    ai: 'gradient-ai',
};

const paddingMap = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
};

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
    (
        {
            variant = 'default',
            colorScheme,
            padding = 'md',
            radius = '3xl',
            gradient,
            isHoverable = false,
            className,
            children,
            ...props
        },
        ref,
    ) => {
        // If colorScheme is specified and variant is glass, override standard glass classes
        const variantClasses =
            variant === 'glass' && colorScheme
                ? cn('backdrop-blur-[24px] border', glassColorSchemes[colorScheme])
                : cardVariants[variant];
        const gradientClasses = gradient ? gradientMap[gradient] : '';

        return (
            <div
                ref={ref}
                data-color-scheme={colorScheme}
                className={cn(
                    'group transition-all duration-300',
                    radiusMap[radius],
                    variantClasses,
                    gradientClasses,
                    isHoverable && 'card-lift',
                    paddingMap[padding],
                    className,
                )}
                {...props}
            >
                {children}
            </div>
        );
    },
);

Card.displayName = 'Card';
