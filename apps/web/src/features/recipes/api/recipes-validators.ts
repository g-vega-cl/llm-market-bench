import type { StrategyStage } from '../types';

const PREV_OUTPUT_PLACEHOLDER = '{{prev_output}}';

export function assertSingleLlmStage(recipe: { stages: readonly StrategyStage[] }): void {
    if (!Array.isArray(recipe.stages) || recipe.stages.length !== 1) {
        throw new Error('Invalid strategy: must contain exactly one LLM stage');
    }
}

export function assertNoPrevOutputPlaceholder(recipe: { stages: readonly StrategyStage[] }): void {
    for (const stage of recipe.stages ?? []) {
        for (const block of stage.blocks ?? []) {
            if (block.type === 'prompt' && block.text.includes(PREV_OUTPUT_PLACEHOLDER)) {
                throw new Error(
                    'Invalid strategy: prev_output is not available in a single-stage strategy',
                );
            }
        }
    }
}
