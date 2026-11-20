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
                'overflow-x-auto voxel-trough rounded-none bg-voxel-trough',
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
        className={cn('bg-voxel-surface border-b border-voxel-bevel-hi', className)}
        {...props}
    />
));
TableHeader.displayName = 'TableHeader';

export const TableBody = React.forwardRef<
    HTMLTableSectionElement,
    React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
    <tbody ref={ref} className={cn('divide-y divide-voxel-bevel-hi/40', className)} {...props} />
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
                isHoverable && !isInactive && 'hover:bg-voxel-elevated',
                isInactive && 'opacity-60 text-voxel-muted bg-voxel-trough/30',
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
                    'px-4 py-3 text-sm font-bold uppercase tracking-wider text-voxel-muted',
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
    /**
     * Semantic text colour. The set is closed on purpose: `cn()` is plain clsx,
     * so a `text-success` / `text-danger` class passed through `className` loses
     * to the cell's own `text-voxel-ink` in the emitted stylesheet order.
     * An explicit tone also overrides the muted colour an `isInactive` row sets,
     * so a vivid cell inside a de-emphasised row must be avoided by the caller.
     */
    tone?: TableCellTone;
}

export const TABLE_CELL_TONES = ['positive', 'negative', 'muted'] as const;

export type TableCellTone = (typeof TABLE_CELL_TONES)[number];

const TONE_CLASSES: Record<TableCellTone, string> = {
    positive: 'text-success',
    negative: 'text-danger',
    muted: 'text-voxel-muted',
};

export const TableCell = React.forwardRef<HTMLTableCellElement, TableCellProps>(
    ({ className, align = 'left', numeric = false, tone, ...props }, ref) => {
        const effectiveAlign = numeric ? 'right' : align;
        return (
            <td
                ref={ref}
                className={cn(
                    'px-4 py-3 text-xs transition-colors',
                    tone ? TONE_CLASSES[tone] : 'text-voxel-ink',
                    'font-normal',
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
