import { Button } from '@llm-market-bench/ui-design-system';
import { Fragment } from 'react';

export interface TypeCodeGridCell {
    code: string;
    /** Human title, used for the accessible name. */
    label: string;
    disabled?: boolean;
}

export interface TypeCodeGridProps {
    /** Row-major cells: `rowHeaders.length * columnHeaders.length` entries. */
    cells: readonly TypeCodeGridCell[];
    activeCode?: string;
    onSelect: (code: string) => void;
    rowHeaders: readonly string[];
    columnHeaders: readonly string[];
    /** In-flow description of the active cell. Never a tooltip or popover. */
    description?: string;
    testId?: string;
}

/**
 * Fixed 4x4 type-code grid shared by the personality result panel and the recipe
 * studio template picker. Sixteen codes wrap into a wall of buttons otherwise.
 *
 * Layout is CSS Grid with intrinsic tracks (no viewport breakpoints, no fixed
 * pixel widths), the active cell is a solid accent button with `aria-pressed`,
 * and the active cell's description renders in flow beneath the grid.
 */
export function TypeCodeGrid({
    cells,
    activeCode,
    onSelect,
    rowHeaders,
    columnHeaders,
    description,
    testId,
}: TypeCodeGridProps) {
    const columns = columnHeaders.length;

    return (
        <div data-testid={testId} className="flex w-full min-w-0 flex-col gap-2">
            <div className="grid min-w-0 grid-cols-[auto_repeat(4,minmax(0,1fr))] items-center gap-2">
                <span aria-hidden="true" />
                {columnHeaders.map((header) => (
                    <span
                        key={`col-${header}`}
                        className="text-center text-xs font-normal text-voxel-muted"
                    >
                        {header}
                    </span>
                ))}

                {rowHeaders.map((header, rowIndex) => {
                    const rowCells = cells.slice(rowIndex * columns, (rowIndex + 1) * columns);
                    return (
                        <Fragment key={`row-${header}`}>
                            <span className="text-xs font-normal text-voxel-muted">{header}</span>
                            {rowCells.map((cell) => {
                                const active = cell.code === activeCode;
                                return (
                                    <Button
                                        key={cell.code}
                                        type="button"
                                        size="sm"
                                        variant={active ? 'solid' : 'outline'}
                                        colorScheme={active ? 'accent' : 'neutral'}
                                        aria-pressed={active}
                                        aria-label={`${cell.code} ${cell.label}`}
                                        disabled={cell.disabled}
                                        onClick={() => onSelect(cell.code)}
                                        className="w-full justify-center px-2"
                                    >
                                        {cell.code}
                                    </Button>
                                );
                            })}
                        </Fragment>
                    );
                })}
            </div>

            {description ? (
                <p
                    data-testid={testId ? `${testId}-description` : undefined}
                    className="min-w-0 break-words text-xs font-normal text-voxel-muted"
                >
                    {description}
                </p>
            ) : null}
        </div>
    );
}
