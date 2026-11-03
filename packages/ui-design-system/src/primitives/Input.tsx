import * as React from 'react';
import { cn } from '../lib/cn';

/**
 * Input primitive.
 *
 * Includes Label and ErrorMessage sub-components for accessibility.
 */

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    isError?: boolean;
    leftAddon?: React.ReactNode;
    rightAddon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
    ({ isError, leftAddon, rightAddon, className, ...props }, ref) => {
        return (
            <div
                className={cn(
                    'voxel-trough rounded-none flex items-center gap-2 w-full bg-boxel-trough px-3 py-2 transition-colors focus-within:ring-2 focus-within:ring-accent/40',
                    isError ? 'border-danger focus-within:ring-danger/40' : 'border-boxel-bevel-hi',
                )}
            >
                {leftAddon}
                <input
                    ref={ref}
                    className={cn(
                        'flex-1 bg-transparent text-sm font-bold text-boxel-ink placeholder:text-boxel-muted focus:outline-none',
                        className,
                    )}
                    {...props}
                />
                {rightAddon}
            </div>
        );
    },
);

Input.displayName = 'Input';

export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {}

export const Label = React.forwardRef<HTMLLabelElement, LabelProps>(
    ({ className, children, ...props }, ref) => {
        return (
            // biome-ignore lint/a11y/noLabelWithoutControl: Generic label wrapper component
            <label
                ref={ref}
                className={cn(
                    'block text-sm font-bold text-boxel-ink uppercase tracking-wider',
                    className,
                )}
                {...props}
            >
                {children}
            </label>
        );
    },
);
Label.displayName = 'Label';
