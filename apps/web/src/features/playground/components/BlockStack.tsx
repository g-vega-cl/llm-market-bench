import { Button } from '@llm-market-bench/ui-design-system';
import {
    MemoriesBlockEditor,
    NewsBlockEditor,
    PromptBlockEditor,
    TechnicalsBlockEditor,
} from '~/features/recipes/components/BlockEditors';
import type {
    MemoriesBlock,
    NewsBlock,
    PromptBlock,
    StrategyBlock,
    StrategyStage,
    TechnicalsBlock,
} from '~/features/recipes/types';
import { CONTENT_TYPES, type ContentBlockType, createBlock, deriveTools } from '../lib/blocks';
import { BlockCard } from './BlockCard';

export interface BlockStackProps {
    stage: StrategyStage;
    onChange: (stage: StrategyStage) => void;
}

/** Block type → the one field the card always shows. Reduced, not collapsed (N1). */
function editorFor(block: StrategyBlock, update: (next: StrategyBlock) => void) {
    if (block.type === 'prompt') {
        return (
            <PromptBlockEditor
                block={block as PromptBlock}
                onUpdate={(text) => update({ ...(block as PromptBlock), text })}
            />
        );
    }
    if (block.type === 'news') {
        return (
            <NewsBlockEditor
                block={block as NewsBlock}
                onUpdate={(patch) => update({ ...(block as NewsBlock), ...patch })}
            />
        );
    }
    if (block.type === 'memories') {
        return (
            <MemoriesBlockEditor
                block={block as MemoriesBlock}
                onUpdate={(patch) => update({ ...(block as MemoriesBlock), ...patch })}
            />
        );
    }
    if (block.type === 'technicals') {
        return (
            <TechnicalsBlockEditor
                block={block as TechnicalsBlock}
                onUpdate={(rules) => update({ ...(block as TechnicalsBlock), rules })}
            />
        );
    }
    return (
        <p className="text-xs font-normal text-voxel-muted">
            Every run must end with a JSON list of <span className="font-mono">action</span> and{' '}
            <span className="font-mono">ticker</span>. This block is not editable.
        </p>
    );
}

export function BlockStack({ stage, onChange }: BlockStackProps) {
    // Union, not replace: a scenario ships tools deriveTools cannot infer.
    const commit = (blocks: StrategyBlock[]) =>
        onChange({
            ...stage,
            blocks,
            selected_tools: [...new Set([...stage.selected_tools, ...deriveTools(blocks)])],
        });

    const update = (blockId: string, next: StrategyBlock) =>
        commit(stage.blocks.map((block) => (block.id === blockId ? next : block)));

    const move = (index: number, delta: -1 | 1) => {
        const target = index + delta;
        if (target < 0 || target >= stage.blocks.length) return;
        const moving = stage.blocks[index];
        const neighbour = stage.blocks[target];
        if (moving.type === 'output_format' || neighbour.type === 'output_format') return;
        const blocks = [...stage.blocks];
        const [item] = blocks.splice(index, 1);
        blocks.splice(target, 0, item);
        commit(blocks);
    };

    const missing = CONTENT_TYPES.filter(
        (type) => !stage.blocks.some((block) => block.type === type),
    );

    return (
        <div className="flex flex-col gap-2 min-w-0">
            {stage.blocks.map((block, index) => (
                <BlockCard
                    key={block.id}
                    block={block}
                    canMoveUp={index > 0 && stage.blocks[index - 1].type !== 'output_format'}
                    canMoveDown={
                        index < stage.blocks.length - 2 &&
                        stage.blocks[index + 1].type !== 'output_format'
                    }
                    onMoveUp={() => move(index, -1)}
                    onMoveDown={() => move(index, 1)}
                    onRemove={() =>
                        commit(stage.blocks.filter((candidate) => candidate.id !== block.id))
                    }
                >
                    {editorFor(block, (next) => update(block.id, next))}
                </BlockCard>
            ))}

            {missing.length > 0 ? (
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-normal text-voxel-muted">Add a block:</span>
                    {missing.map((type: ContentBlockType) => (
                        <Button
                            key={type}
                            size="sm"
                            variant="outline"
                            colorScheme="neutral"
                            onClick={() =>
                                commit([
                                    ...stage.blocks.filter(
                                        (block) => block.type !== 'output_format',
                                    ),
                                    createBlock(type),
                                    ...stage.blocks.filter(
                                        (block) => block.type === 'output_format',
                                    ),
                                ])
                            }
                        >
                            + {type}
                        </Button>
                    ))}
                </div>
            ) : null}
        </div>
    );
}
