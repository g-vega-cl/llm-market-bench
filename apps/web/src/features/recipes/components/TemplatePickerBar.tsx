import { Button } from '@llm-market-bench/ui-design-system';
import { TypeCodeGrid, type TypeCodeGridCell } from '~/components/ui/TypeCodeGrid';
import type { PushStrategy } from '../types';

export interface TemplatePickerGrid {
    cells: readonly TypeCodeGridCell[];
    rowHeaders: readonly string[];
    columnHeaders: readonly string[];
    activeCode?: string;
    onSelectCode: (code: string) => void;
    description?: string;
}

/**
 * Starter template picker.
 *
 * The description line is the whole point: the button row alone names the
 * templates, so a first-time visitor only learns what each one demonstrates
 * from this in-flow line (no tooltips or popovers). With sixteen starters the
 * caller passes `grid` so the templates render as the shared 4x4 code grid
 * instead of a four-row wall of full-name buttons.
 */
export function TemplatePickerBar({
    templates,
    activeIndex,
    disabled,
    onSelect,
    grid,
}: {
    templates: readonly PushStrategy[];
    activeIndex: number;
    disabled?: boolean;
    onSelect: (index: number) => void;
    grid?: TemplatePickerGrid;
}) {
    const active = activeIndex >= 0 ? templates[activeIndex] : undefined;

    if (grid) {
        return (
            <div className="flex flex-col gap-2">
                <span className="text-sm font-bold text-voxel-muted">Templates:</span>
                <TypeCodeGrid
                    testId="template-code-grid"
                    cells={grid.cells}
                    activeCode={grid.activeCode}
                    onSelect={grid.onSelectCode}
                    rowHeaders={grid.rowHeaders}
                    columnHeaders={grid.columnHeaders}
                    description={grid.description ?? active?.description}
                />
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-bold text-voxel-muted">Templates:</span>
                {templates.map((template, index) => (
                    <Button
                        key={template.name}
                        size="sm"
                        variant={activeIndex === index ? 'solid' : 'outline'}
                        colorScheme={activeIndex === index ? 'accent' : 'neutral'}
                        onClick={() => onSelect(index)}
                        disabled={disabled}
                    >
                        {template.name}
                    </Button>
                ))}
            </div>
            {active?.description && (
                <p
                    data-testid="template-description"
                    className="text-xs font-normal text-voxel-muted"
                >
                    {active.description}
                </p>
            )}
        </div>
    );
}
