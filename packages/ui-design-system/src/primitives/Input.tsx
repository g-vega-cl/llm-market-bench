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
                    'flex items-center gap-2 w-full rounded-xl border bg-white dark:bg-zinc-900 px-3 py-2 transition-colors focus-within:ring-2 focus-within:ring-accent/40',
                    isError
                        ? 'border-danger focus-within:ring-danger/40'
                        : 'border-zinc-200 dark:border-zinc-800',
                )}
            >
                {leftAddon}
                <input
                    ref={ref}
                    className={cn(
                        'flex-1 bg-transparent text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none',
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
            <label
                ref={ref}
                className={cn(
                    'block text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-1',
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

export interface ErrorMessageProps extends React.HTMLAttributes<HTMLSpanElement> {}

export const ErrorMessage = React.forwardRef<HTMLSpanElement, ErrorMessageProps>(
    ({ className, children, ...props }, ref) => {
        return (
            <span ref={ref} className={cn('block text-xs text-danger mt-1', className)} {...props}>
                {children}
            </span>
        );
    },
);
ErrorMessage.displayName = 'ErrorMessage';
