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
                'overflow-x-auto voxel-trough rounded-none bg-boxel-trough',
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

export interface TableRowProps extends React.HTMLAttributes<HTMLTableRowElement> {
    isHoverable?: boolean;
    isInactive?: boolean;
}

export const TableRow = React.forwardRef<HTMLTableRowElement, TableRowProps>(
    ({ className, isHoverable = true, isInactive = false, ...props }, ref) => (
        <tr
            ref={ref}
            data-inactive={isInactive ? 'true' : undefined}
            className={cn(
                'transition-colors duration-200',
                isHoverable && !isInactive && 'hover:bg-zinc-50/50 dark:hover:bg-zinc-800/30',
                isInactive && 'opacity-60 text-boxel-muted bg-boxel-trough/30',
                className,
            )}
            {...props}
        />
    ),
);
TableRow.displayName = 'TableRow';

export interface TableHeadProps extends React.ThHTMLAttributes<HTMLTableCellElement> {
    align?: 'left' | 'center' | 'right';
    numeric?: boolean;
}

export const TableHead = React.forwardRef<HTMLTableCellElement, TableHeadProps>(
    ({ className, align = 'left', numeric = false, ...props }, ref) => {
        const effectiveAlign = numeric ? 'right' : align;
        return (
            <th
                ref={ref}
                className={cn(
                    'px-4 py-3 text-sm font-bold uppercase tracking-wider text-boxel-muted',
                    effectiveAlign === 'center' && 'text-center',
                    effectiveAlign === 'right' && 'text-right',
                    className,
                )}
                {...props}
            />
        );
    },
);
TableHead.displayName = 'TableHead';

export interface TableCellProps extends React.TdHTMLAttributes<HTMLTableCellElement> {
    align?: 'left' | 'center' | 'right';
    numeric?: boolean;
}

export const TableCell = React.forwardRef<HTMLTableCellElement, TableCellProps>(
    ({ className, align = 'left', numeric = false, ...props }, ref) => {
        const effectiveAlign = numeric ? 'right' : align;
        return (
            <td
                ref={ref}
                className={cn(
                    'px-4 py-3 text-xs font-normal text-boxel-ink transition-colors',
                    effectiveAlign === 'center' && 'text-center',
                    effectiveAlign === 'right' && 'text-right font-mono tabular-nums',
                    className,
                )}
                {...props}
            />
        );
    },
);
TableCell.displayName = 'TableCell';
