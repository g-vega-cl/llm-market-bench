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
    default: 'voxel-card bg-boxel-surface text-boxel-ink',
    outlined: 'voxel-trough bg-boxel-trough text-boxel-ink',
    glass: 'voxel-card bg-boxel-surface text-boxel-ink',
    'glass-warning': 'voxel-card bg-boxel-surface border-accent text-boxel-ink',
};

const glassColorSchemes = {
    neutral: 'voxel-card bg-boxel-surface',
    success: 'voxel-card bg-boxel-surface border-t-success/70 border-l-success/70',
    warning: 'voxel-card bg-boxel-surface border-t-warning/70 border-l-warning/70',
    danger: 'voxel-card bg-boxel-surface border-t-danger/70 border-l-danger/70',
    info: 'voxel-card bg-boxel-surface border-t-info/70 border-l-info/70',
};

const radiusMap = {
    none: 'rounded-none',
    xl: 'rounded-none',
    '2xl': 'rounded-none',
    '3xl': 'rounded-none',
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
            radius = 'none',
            gradient,
            isHoverable = false,
            className,
            children,
            ...props
        },
        ref,
    ) => {
        const variantClasses =
            variant === 'glass' && colorScheme
                ? glassColorSchemes[colorScheme]
                : cardVariants[variant];
        const gradientClasses = gradient ? gradientMap[gradient] : '';

        return (
            <div
                ref={ref}
                data-color-scheme={colorScheme}
                className={cn(
                    'group transition-colors duration-150',
                    radiusMap[radius],
                    variantClasses,
                    gradientClasses,
                    isHoverable && 'hover:bg-boxel-elevated',
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
