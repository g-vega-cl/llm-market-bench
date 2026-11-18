import { Button } from '@llm-market-bench/ui-design-system';
import type { PushStrategy } from '../types';

/**
 * Starter template picker.
 *
 * The description line is the whole point: the button row alone names the
 * templates, so a first-time visitor only learns what each one demonstrates
 * from this in-flow line (no tooltips or popovers).
 */
export function TemplatePickerBar({
    templates,
    activeIndex,
    disabled,
    onSelect,
}: {
    templates: readonly PushStrategy[];
    activeIndex: number;
    disabled?: boolean;
    onSelect: (index: number) => void;
}) {
    const active = activeIndex >= 0 ? templates[activeIndex] : undefined;

    return (
        <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-bold text-muted-foreground">Templates:</span>
                {templates.map((template, index) => (
                    <Button
                        key={template.name}
                        size="sm"
                        variant={activeIndex === index ? 'solid' : 'outline'}
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
                    className="text-xs font-normal text-muted-foreground"
                >
                    {active.description}
                </p>
            )}
        </div>
    );
}
