import * as React from 'react';
import { cn } from '../lib/cn';

/**
 * Table primitive.
 *
 * Composable components for building data tables.
 * Includes: Table, TableHeader, TableBody, TableRow, TableHead, TableCell.
 */

export interface TableProps extends React.HTMLAttributes<HTMLTableElement> {
    containerClassName?: string;
}

export const Table = React.forwardRef<HTMLTableElement, TableProps>(
    ({ className, containerClassName, children, ...props }, ref) => (
        <div
            className={cn(
                'overflow-x-auto border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 shadow-sm',
                containerClassName,
            )}
        >
            <table
                ref={ref}
                className={cn('w-full text-left border-collapse', className)}
                {...props}
            >
                {children}
            </table>
        </div>
    ),
);
Table.displayName = 'Table';

export const TableHeader = React.forwardRef<
    HTMLTableSectionElement,
    React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
    <thead
        ref={ref}
        className={cn(
            'bg-zinc-50 dark:bg-zinc-950/50 border-b border-zinc-200 dark:border-zinc-800',
            className,
        )}
        {...props}
    />
));
TableHeader.displayName = 'TableHeader';

export const TableBody = React.forwardRef<
    HTMLTableSectionElement,
    React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
    <tbody
        ref={ref}
        className={cn('divide-y divide-zinc-100 dark:divide-zinc-800', className)}
        {...props}
    />
));
TableBody.displayName = 'TableBody';

export const TableRow = React.forwardRef<
    HTMLTableRowElement,
    React.HTMLAttributes<HTMLTableRowElement> & { isHoverable?: boolean }
>(({ className, isHoverable = true, ...props }, ref) => (
    <tr
        ref={ref}
        className={cn(
            'transition-colors duration-200',
            isHoverable && 'hover:bg-zinc-50/50 dark:hover:bg-zinc-800/30',
            className,
        )}
        {...props}
    />
));
TableRow.displayName = 'TableRow';

export interface TableHeadProps extends React.ThHTMLAttributes<HTMLTableCellElement> {
    align?: 'left' | 'center' | 'right';
}

export const TableHead = React.forwardRef<HTMLTableCellElement, TableHeadProps>(
    ({ className, align = 'left', ...props }, ref) => (
        <th
            ref={ref}
            className={cn(
                'px-4 sm:px-6 py-3 sm:py-4 text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400',
                align === 'center' && 'text-center',
                align === 'right' && 'text-right',
                className,
            )}
            {...props}
        />
    ),
);
TableHead.displayName = 'TableHead';

export interface TableCellProps extends React.TdHTMLAttributes<HTMLTableCellElement> {
    align?: 'left' | 'center' | 'right';
}

export const TableCell = React.forwardRef<HTMLTableCellElement, TableCellProps>(
    ({ className, align = 'left', ...props }, ref) => (
        <td
            ref={ref}
            className={cn(
                'px-4 sm:px-6 py-3 sm:py-4 transition-colors',
                align === 'center' && 'text-center',
                align === 'right' && 'text-right',
                className,
            )}
            {...props}
        />
    ),
);
TableCell.displayName = 'TableCell';
