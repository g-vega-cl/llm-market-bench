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
                    'voxel-trough rounded-none relative flex items-center w-full bg-voxel-trough px-3 py-2 transition-colors focus-within:ring-2 focus-within:ring-accent/40',
                    isError ? 'border-danger focus-within:ring-danger/40' : 'border-voxel-bevel-hi',
                )}
            >
                <select
                    ref={ref}
                    className={cn(
                        'w-full bg-transparent text-sm font-bold text-voxel-ink placeholder:text-voxel-muted focus:outline-none cursor-pointer pr-4',
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
                                className="bg-voxel-surface text-voxel-ink text-sm font-bold"
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
