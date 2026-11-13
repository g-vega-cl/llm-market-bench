import { Badge, Button } from '@llm-market-bench/ui-design-system';
import type {
    MemoriesBlock,
    NewsBlock,
    PromptBlock,
    StrategyBlock,
    StrategyStage,
    TechnicalsBlock,
} from '../types';
import {
    MemoriesBlockEditor,
    NewsBlockEditor,
    PromptBlockEditor,
    TechnicalsBlockEditor,
} from './BlockEditors';
import { ToolPicker } from './ToolPicker';

interface StageBuilderProps {
    stage: StrategyStage;
    stageIndex: number;
    totalStages: number;
    onChange: (updated: StrategyStage) => void;
    onRemoveStage?: () => void;
}

function createBlock(type: StrategyBlock['type']): StrategyBlock {
    const id = `blk-${type}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    if (type === 'prompt') return { id, type: 'prompt', text: '' };
    if (type === 'news') return { id, type: 'news', contains: [], recency_hours: 48 };
    if (type === 'memories') {
        return {
            id,
            type: 'memories',
            contains: [],
            recency_hours: 168,
            category: 'ALL',
            min_importance: 5,
        };
    }
    if (type === 'output_format') {
        return { id, type: 'output_format' };
    }
    return {
        id,
        type: 'technicals',
        rules: [{ id: `rule-${Date.now()}`, metric: 'P/E', operator: '<', target: '35' }],
    };
}

export function StageBuilder({
    stage,
    stageIndex,
    totalStages,
    onChange,
    onRemoveStage,
}: StageBuilderProps) {
    const updateBlock = (blockId: string, updater: (b: StrategyBlock) => StrategyBlock) => {
        onChange({
            ...stage,
            blocks: stage.blocks.map((b) => (b.id === blockId ? updater(b) : b)),
        });
    };

    const removeBlock = (blockId: string) => {
        onChange({
            ...stage,
            blocks: stage.blocks.filter((b) => b.id !== blockId),
        });
    };

    const moveBlock = (index: number, delta: -1 | 1) => {
        const nextIdx = index + delta;
        if (nextIdx < 0 || nextIdx >= stage.blocks.length) return;
        const copy = [...stage.blocks];
        const [item] = copy.splice(index, 1);
        copy.splice(nextIdx, 0, item);
        onChange({ ...stage, blocks: copy });
    };

    return (
        <div className="flex flex-col gap-4 border border-border bg-boxel-surface p-4 rounded-none">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
                <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline" size="sm">
                        LLM Call #{stageIndex + 1}
                    </Badge>
                    <input
                        type="text"
                        aria-label={`Stage ${stageIndex + 1} Title`}
                        value={stage.title}
                        onChange={(e) => onChange({ ...stage, title: e.target.value })}
                        className="border border-border bg-boxel-canvas px-2 py-1 text-sm font-bold text-foreground rounded-none"
                    />
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                            onChange({ ...stage, blocks: [...stage.blocks, createBlock('prompt')] })
                        }
                    >
                        + Prompt
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                            onChange({ ...stage, blocks: [...stage.blocks, createBlock('news')] })
                        }
                    >
                        + News
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                            onChange({
                                ...stage,
                                blocks: [...stage.blocks, createBlock('memories')],
                            })
                        }
                    >
                        + Memories
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                            onChange({
                                ...stage,
                                blocks: [...stage.blocks, createBlock('technicals')],
                            })
                        }
                    >
                        + Technicals
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                            onChange({
                                ...stage,
                                blocks: [...stage.blocks, createBlock('output_format')],
                            })
                        }
                    >
                        + Output Format
                    </Button>
                    {totalStages > 1 && onRemoveStage && (
                        <Button size="sm" variant="outline" onClick={onRemoveStage}>
                            Remove Stage
                        </Button>
                    )}
                </div>
            </div>

            <div className="flex flex-col gap-3">
                {stage.blocks.map((block, bIdx) => (
                    <div
                        key={block.id}
                        className="flex flex-col gap-2 border border-border bg-boxel-canvas p-3 rounded-none"
                    >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <Badge variant="outline" size="sm">
                                {block.type.toUpperCase()} BLOCK
                            </Badge>
                            {block.type === 'output_format' ? null : (
                                <div className="flex items-center gap-2">
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => moveBlock(bIdx, -1)}
                                        disabled={bIdx === 0}
                                    >
                                        ↑
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => moveBlock(bIdx, 1)}
                                        disabled={bIdx === stage.blocks.length - 1}
                                    >
                                        ↓
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => removeBlock(block.id)}
                                    >
                                        Delete
                                    </Button>
                                </div>
                            )}
                        </div>

                        {block.type === 'prompt' && (
                            <PromptBlockEditor
                                block={block}
                                onUpdate={(text) =>
                                    updateBlock(block.id, (b) => ({ ...(b as PromptBlock), text }))
                                }
                            />
                        )}
                        {block.type === 'news' && (
                            <NewsBlockEditor
                                block={block}
                                onUpdate={(patch) =>
                                    updateBlock(block.id, (b) => ({
                                        ...(b as NewsBlock),
                                        ...patch,
                                    }))
                                }
                            />
                        )}
                        {block.type === 'memories' && (
                            <MemoriesBlockEditor
                                block={block}
                                onUpdate={(patch) =>
                                    updateBlock(block.id, (b) => ({
                                        ...(b as MemoriesBlock),
                                        ...patch,
                                    }))
                                }
                            />
                        )}
                        {block.type === 'technicals' && (
                            <TechnicalsBlockEditor
                                block={block}
                                onUpdate={(rules) =>
                                    updateBlock(block.id, (b) => ({
                                        ...(b as TechnicalsBlock),
                                        rules,
                                    }))
                                }
                            />
                        )}
                        {block.type === 'output_format' && (
                            <div className="flex items-center gap-2 text-xs">
                                <Badge variant="outline" size="sm">
                                    IMMUTABLE
                                </Badge>
                                Output format locked to BUY/SELL JSON schema.
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <ToolPicker
                selectedTools={stage.selected_tools}
                onChange={(selected_tools) => onChange({ ...stage, selected_tools })}
            />
        </div>
    );
}
