import type { StrategyStage } from '~/features/recipes/types';

export function describeStage(stage: StrategyStage): string {
    const prompt = stage.blocks.find((block) => block.type === 'prompt');
    if (prompt && prompt.type === 'prompt') return prompt.text.trim().slice(0, 200);
    return '';
}
