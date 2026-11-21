import { Button } from '@llm-market-bench/ui-design-system';
import type { ReactNode } from 'react';
import type { StrategyBlock } from '~/features/recipes/types';
import { BLOCK_COPY } from '../lib/blocks';

export interface BlockCardProps {
    block: StrategyBlock;
    canMoveUp: boolean;
    canMoveDown: boolean;
    onMoveUp: () => void;
    onMoveDown: () => void;
    onRemove: () => void;
    children: ReactNode;
}

/**
 * Always open, never a summary that expands: the design spec bans collapsibles,
 * so a block is its editor. Reordering is reading order only.
 */
export function BlockCard({
    block,
    canMoveUp,
    canMoveDown,
    onMoveUp,
    onMoveDown,
    onRemove,
    children,
}: BlockCardProps) {
    const copy = BLOCK_COPY[block.type];
    const terminal = block.type === 'output_format';

    return (
        <article
            data-testid={`block-${block.type}`}
            className="flex flex-col gap-2 border border-voxel-bevel-hi bg-voxel-surface p-3 rounded-none min-w-0"
        >
            <header className="flex flex-wrap items-baseline justify-between gap-2">
                <div className="flex flex-col gap-0.5 min-w-0">
                    <h3 className="text-sm font-bold text-voxel-ink">{copy.title}</h3>
                    <p className="text-xs font-normal text-voxel-muted">{copy.subtitle}</p>
                </div>
                {terminal ? (
                    <span className="font-mono text-xs font-normal text-voxel-muted">locked</span>
                ) : (
                    <div className="flex flex-wrap items-center gap-1">
                        <Button
                            size="sm"
                            variant="outline"
                            colorScheme="neutral"
                            aria-label={`Move ${copy.title} up`}
                            disabled={!canMoveUp}
                            onClick={onMoveUp}
                        >
                            ↑
                        </Button>
                        <Button
                            size="sm"
                            variant="outline"
                            colorScheme="neutral"
                            aria-label={`Move ${copy.title} down`}
                            disabled={!canMoveDown}
                            onClick={onMoveDown}
                        >
                            ↓
                        </Button>
                        <Button
                            size="sm"
                            variant="outline"
                            colorScheme="neutral"
                            aria-label={`Remove ${copy.title}`}
                            onClick={onRemove}
                        >
                            Remove
                        </Button>
                    </div>
                )}
            </header>
            {children}
        </article>
    );
}
