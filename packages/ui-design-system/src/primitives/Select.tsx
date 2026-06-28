import * as React from 'react';
import { cn } from '../lib/cn';

export interface SelectOption {
    label: string;
    value: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
    options: (string | SelectOption)[];
    isError?: boolean;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
    ({ options, isError, className, children, ...props }, ref) => {
        return (
            <div
                className={cn(
                    'relative flex items-center w-full rounded-xl border bg-white dark:bg-zinc-900 px-3 py-2 transition-colors focus-within:ring-2 focus-within:ring-accent/40',
                    isError
                        ? 'border-danger focus-within:ring-danger/40'
                        : 'border-zinc-200 dark:border-zinc-800',
                )}
            >
                <select
                    ref={ref}
                    className={cn(
                        'w-full bg-transparent text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none cursor-pointer pr-4',
                        className,
                    )}
                    {...props}
                >
                    {children}
                    {options.map((opt) => {
                        const value = typeof opt === 'string' ? opt : opt.value;
                        const label = typeof opt === 'string' ? opt : opt.label;
                        return (
                            <option
                                key={value}
                                value={value}
                                className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100"
                            >
                                {label}
                            </option>
                        );
                    })}
                </select>
            </div>
        );
    },
);

Select.displayName = 'Select';
