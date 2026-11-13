import { describe, expect, it } from 'vitest';
import { buildStagePromptPreview } from './prompt-builder';
import type { StrategyStage } from './types';

const emptyStage: StrategyStage = {
    id: 'stage-1',
    title: 'Catalyst & Technical Analysis',
    selected_tools: [],
    blocks: [],
};

describe('buildStagePromptPreview', () => {
    it('shows prompt text as written, without a previous-stage placeholder', () => {
        const stage: StrategyStage = {
            ...emptyStage,
            blocks: [
                { id: 'blk-p', type: 'prompt', text: '  Review {{prev_output}} carefully.  ' },
            ],
        };

        const preview = buildStagePromptPreview(stage);

        expect(preview).toBe('Review {{prev_output}} carefully.');
        expect(preview).not.toContain('Output from Stage');
        expect(preview).not.toContain('Previous Stage Output');
    });

    it('uses hydrated news text in place of the placeholder when live data is loaded', () => {
        const stage: StrategyStage = {
            ...emptyStage,
            blocks: [
                { id: 'blk-n', type: 'news', contains: ['Trump'], recency_hours: 48 },
                { id: 'blk-p', type: 'prompt', text: 'Decide.' },
            ],
        };

        const preview = buildStagePromptPreview(stage, { 'blk-n': '[News (live)]:\n- Headline' });

        expect(preview).toBe('[News (live)]:\n- Headline\n\nDecide.');
    });

    it('shows the empty-stage hint when no blocks are configured', () => {
        expect(buildStagePromptPreview(emptyStage)).toMatch(
            /^\(Empty stage .+ add a block above\)$/,
        );
    });
});
