import { Badge, Button } from '@llm-market-bench/ui-design-system';
import type {
    MemoriesBlock,
    NewsBlock,
    PromptBlock,
    StrategyBlock,
    StrategyStage,
    TechnicalsBlock,
} from '../types';
import { pinStageBlocks } from '../utils/stage-blocks';
import {
    MemoriesBlockEditor,
    NewsBlockEditor,
    PromptBlockEditor,
    TechnicalsBlockEditor,
} from './BlockEditors';
import { ToolPicker } from './ToolPicker';

interface StageBuilderProps {
    stage: StrategyStage;
    onChange: (updated: StrategyStage) => void;
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

export function StageBuilder({ stage, onChange }: StageBuilderProps) {
    const blocks = pinStageBlocks(stage.blocks);
    const hasPrompt = blocks.some((block) => block.type === 'prompt');
    const hasOutputFormat = blocks.some((block) => block.type === 'output_format');

    const emitBlocks = (nextBlocks: StrategyBlock[]) => {
        onChange({
            ...stage,
            blocks: pinStageBlocks(nextBlocks),
        });
    };

    const updateBlock = (blockId: string, updater: (b: StrategyBlock) => StrategyBlock) => {
        emitBlocks(blocks.map((b) => (b.id === blockId ? updater(b) : b)));
    };

    const removeBlock = (blockId: string) => {
        emitBlocks(blocks.filter((b) => b.id !== blockId));
    };

    return (
        <div className="flex flex-col gap-4 border border-voxel-bevel-hi bg-voxel-surface p-4 rounded-none">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-voxel-bevel-hi pb-3">
                <Badge variant="soft" size="sm">
                    LLM Call
                </Badge>
                <div className="flex flex-wrap items-center gap-2">
                    <Button
                        size="sm"
                        variant="outline"
                        colorScheme="neutral"
                        disabled={hasPrompt}
                        onClick={() => emitBlocks([...blocks, createBlock('prompt')])}
                    >
                        + Prompt
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        colorScheme="neutral"
                        onClick={() => emitBlocks([...blocks, createBlock('news')])}
                    >
                        + News
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        colorScheme="neutral"
                        onClick={() => emitBlocks([...blocks, createBlock('memories')])}
                    >
                        + Memories
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        colorScheme="neutral"
                        onClick={() => emitBlocks([...blocks, createBlock('technicals')])}
                    >
                        + Technicals
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        colorScheme="neutral"
                        disabled={hasOutputFormat}
                        onClick={() => emitBlocks([...blocks, createBlock('output_format')])}
                    >
                        + Output Format
                    </Button>
                </div>
            </div>

            <div className="flex flex-col gap-3">
                {blocks.map((block) => (
                    <div
                        key={block.id}
                        className="flex flex-col gap-2 border border-voxel-bevel-hi bg-voxel-canvas p-3 rounded-none"
                    >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex flex-wrap items-center gap-2">
                                <Badge variant="soft" size="sm">
                                    {block.type.toUpperCase()} BLOCK
                                </Badge>
                                {block.type === 'prompt' ? (
                                    <Badge variant="soft" size="sm" colorScheme="accent">
                                        PINNED FIRST
                                    </Badge>
                                ) : null}
                            </div>
                            {block.type === 'output_format' || block.type === 'prompt' ? null : (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    colorScheme="neutral"
                                    onClick={() => removeBlock(block.id)}
                                >
                                    Delete
                                </Button>
                            )}
                        </div>

                        {block.type === 'prompt' && (
                            <>
                                <PromptBlockEditor
                                    block={block}
                                    onUpdate={(text) =>
                                        updateBlock(block.id, (b) => ({
                                            ...(b as PromptBlock),
                                            text,
                                        }))
                                    }
                                />
                                {!block.text.trim() ? (
                                    <p className="text-xs font-normal text-danger">
                                        Prompt block cannot be empty — write clear instructions for
                                        what this bot should trade.
                                    </p>
                                ) : null}
                            </>
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
                                <Badge variant="soft" size="sm">
                                    IMMUTABLE
                                </Badge>
                                Output format locked to Long-Only BUY/EXIT JSON schema.
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
