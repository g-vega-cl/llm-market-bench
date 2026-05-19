import * as React from 'react';
import { cn } from '../lib/cn';

/**
 * Card primitive.
 *
 * Composable: Card, CardHeader, CardBody, CardFooter.
 * Variants: default, outlined, ghost, glass
 * Gradient backgrounds: electric, success, alert, catalyst, ai
 */

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: 'default' | 'outlined' | 'ghost' | 'glass';
    padding?: 'none' | 'sm' | 'md' | 'lg';
    radius?: 'xl' | '2xl' | '3xl' | 'none';
    gradient?: 'electric' | 'success' | 'alert' | 'catalyst' | 'ai';
    isHoverable?: boolean;
}

const cardVariants = {
    default: 'bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm',
    outlined: 'bg-transparent border border-zinc-200 dark:border-zinc-800',
    ghost: 'bg-transparent',
    glass: 'bg-white/10 dark:bg-white/5 backdrop-blur-md border border-white/20 dark:border-white/10 shadow-xl',
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
        const variantClasses = cardVariants[variant];
        const gradientClasses = gradient ? gradientMap[gradient] : '';

        return (
            <div
                ref={ref}
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
