import { Badge } from '@llm-market-bench/ui-design-system';
import { CURATED_TOOLS } from '../types';

interface ToolPickerProps {
    selectedTools: string[];
    onChange: (nextTools: string[]) => void;
}

const CURATED_TOOL_NAME_SET = new Set(CURATED_TOOLS.map((t) => t.name));

export function ToolPicker({ selectedTools, onChange }: ToolPickerProps) {
    const cleanSelected = selectedTools.filter((t) => CURATED_TOOL_NAME_SET.has(t));
    const selectedSet = new Set(cleanSelected);

    const toggleTool = (toolName: string) => {
        if (selectedSet.has(toolName)) {
            onChange(cleanSelected.filter((t) => t !== toolName));
        } else {
            onChange([...cleanSelected, toolName]);
        }
    };

    return (
        <div className="flex flex-col gap-2 border border-voxel-bevel-hi bg-voxel-canvas p-3 rounded-none">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-voxel-ink">Allowed LLM Tools</span>
                    <Badge variant="soft" size="sm">
                        {cleanSelected.length} / {CURATED_TOOLS.length}
                    </Badge>
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
                                    ? 'border-accent bg-voxel-surface'
                                    : 'border-voxel-bevel-hi bg-voxel-canvas'
                            }`}
                        >
                            <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => toggleTool(tool.name)}
                                aria-label={tool.label}
                            />
                            <div className="flex flex-col gap-1 min-w-0">
                                <div className="flex flex-wrap items-center gap-2">
                                    <span className="text-sm font-bold text-voxel-ink">
                                        {tool.label}
                                    </span>
                                    {tool.liveOnly && (
                                        <Badge size="xs" variant="soft" colorScheme="warning">
                                            Live only
                                        </Badge>
                                    )}
                                </div>
                                <span className="text-xs font-normal text-voxel-muted">
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
