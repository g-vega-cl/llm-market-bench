import type { StrategyBlock } from '../types';

function ensureUniqueBlockId(candidate: string, used: Set<string>): string {
    let id = candidate;
    let suffix = 2;
    while (used.has(id)) {
        id = `${candidate}-${suffix}`;
        suffix += 1;
    }
    used.add(id);
    return id;
}

function partitionStageBlocks(blocks: readonly StrategyBlock[]): {
    promptBlocks: Array<Extract<StrategyBlock, { type: 'prompt' }>>;
    middleBlocks: StrategyBlock[];
    formatBlock: Extract<StrategyBlock, { type: 'output_format' }> | undefined;
} {
    const promptBlocks = blocks.filter(
        (block): block is Extract<StrategyBlock, { type: 'prompt' }> => block.type === 'prompt',
    );
    const middleBlocks = blocks.filter(
        (block) => block.type !== 'prompt' && block.type !== 'output_format',
    );
    const formatBlock = blocks.find(
        (block): block is Extract<StrategyBlock, { type: 'output_format' }> =>
            block.type === 'output_format',
    );
    return { promptBlocks, middleBlocks, formatBlock };
}

/**
 * Structural stage ordering for live editing (`StageBuilder`) and prompt
 * rendering (`PromptVisualizer`): keeps exactly one `prompt` block at index 0
 * and one `output_format` block last WITHOUT trimming whitespace or newlines
 * inside the user's active prompt text.
 */
export function pinStageBlocks(
    blocks: readonly StrategyBlock[],
    fallbackPromptText = '',
): StrategyBlock[] {
    const { promptBlocks, middleBlocks, formatBlock } = partitionStageBlocks(blocks);
    const usedIds = new Set<string>();

    const primaryText =
        promptBlocks.length === 1
            ? promptBlocks[0].text.slice(0, 4000)
            : promptBlocks.length > 1
              ? promptBlocks
                    .map((block) => block.text)
                    .filter((text) => text.length > 0)
                    .join('\n\n')
                    .slice(0, 4000)
              : fallbackPromptText.slice(0, 4000);

    const primaryPrompt: StrategyBlock = {
        id: ensureUniqueBlockId(promptBlocks[0]?.id || 'b-prompt-1', usedIds),
        type: 'prompt',
        text: primaryText,
    };

    const normalizedMiddle = middleBlocks.map((block) => ({
        ...block,
        id: ensureUniqueBlockId(block.id, usedIds),
    }));

    const primaryFormat: StrategyBlock = {
        id: ensureUniqueBlockId(formatBlock?.id || 'b-format-1', usedIds),
        type: 'output_format',
    };

    return [primaryPrompt, ...normalizedMiddle, primaryFormat];
}

/**
 * Compiler-boundary coercion: trims and merges model-emitted `prompt` blocks,
 * synthesizing one from `fallbackPromptText` if the model omitted it or left
 * it blank, then pins `prompt` first and `output_format` last.
 */
export function coerceStageBlocks(
    blocks: readonly StrategyBlock[],
    fallbackPromptText: string,
): StrategyBlock[] {
    const { promptBlocks, middleBlocks, formatBlock } = partitionStageBlocks(blocks);
    const usedIds = new Set<string>();

    const combinedText = promptBlocks
        .map((block) => block.text.trim())
        .filter(Boolean)
        .join('\n\n')
        .slice(0, 4000);

    const primaryPrompt: StrategyBlock = {
        id: ensureUniqueBlockId(promptBlocks[0]?.id || 'b-prompt-1', usedIds),
        type: 'prompt',
        text: combinedText || fallbackPromptText.trim().slice(0, 4000),
    };

    const normalizedMiddle = middleBlocks.map((block) => ({
        ...block,
        id: ensureUniqueBlockId(block.id, usedIds),
    }));

    const primaryFormat: StrategyBlock = {
        id: ensureUniqueBlockId(formatBlock?.id || 'b-format-1', usedIds),
        type: 'output_format',
    };

    return [primaryPrompt, ...normalizedMiddle, primaryFormat];
}
