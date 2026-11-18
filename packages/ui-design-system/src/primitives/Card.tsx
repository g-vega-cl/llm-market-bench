import * as React from 'react';
import { cn } from '../lib/cn';

/**
 * Card primitive.
 *
 * Composable: Card, CardHeader, CardBody, CardFooter.
 * Variant budget: exactly two variants (`default`, `outlined`).
 */

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: 'default' | 'outlined';
    padding?: 'none' | 'sm' | 'md' | 'lg';
    isHoverable?: boolean;
}

const cardVariants = {
    default: 'voxel-card bg-voxel-surface text-voxel-ink',
    outlined: 'voxel-trough bg-voxel-trough text-voxel-ink',
};

const paddingMap = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
};

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
    (
        { variant = 'default', padding = 'md', isHoverable = false, className, children, ...props },
        ref,
    ) => {
        const variantClasses = cardVariants[variant];

        return (
            <div
                ref={ref}
                className={cn(
                    'group transition-colors duration-150 rounded-none',
                    variantClasses,
                    isHoverable && 'hover:bg-voxel-elevated',
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
