import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { CURATED_TOOLS } from '../types';

interface ToolPickerProps {
    selectedTools: string[];
    onChange: (nextTools: string[]) => void;
}

export function ToolPicker({ selectedTools, onChange }: ToolPickerProps) {
    const selectedSet = new Set(selectedTools);

    const toggleTool = (toolName: string) => {
        if (selectedSet.has(toolName)) {
            onChange(selectedTools.filter((t) => t !== toolName));
        } else {
            onChange([...selectedTools, toolName]);
        }
    };

    return (
        <div className="flex flex-col gap-2 border border-border bg-boxel-canvas p-3 rounded-none">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-foreground">Allowed LLM Tools</span>
                    <Badge variant="outline" size="sm">
                        {selectedTools.length} / {CURATED_TOOLS.length}
                    </Badge>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onChange(CURATED_TOOLS.map((t) => t.name))}
                    >
                        Select All
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => onChange([])}>
                        Clear
                    </Button>
                </div>
            </div>

            <div className="flex flex-wrap gap-2">
                {CURATED_TOOLS.map((tool) => {
                    const checked = selectedSet.has(tool.name);
                    return (
                        <label
                            key={tool.name}
                            className={`flex flex-1 basis-56 min-w-0 cursor-pointer items-start gap-2 border p-2 rounded-none ${
                                checked
                                    ? 'border-primary bg-boxel-surface'
                                    : 'border-border bg-boxel-canvas'
                            }`}
                        >
                            <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => toggleTool(tool.name)}
                                aria-label={tool.label}
                            />
                            <div className="flex flex-col gap-1 min-w-0">
                                <span className="text-xs font-bold text-foreground">
                                    {tool.label}
                                </span>
                                <span className="text-xs font-normal text-muted-foreground">
                                    {tool.description}
                                </span>
                            </div>
                        </label>
                    );
                })}
            </div>
        </div>
    );
}
