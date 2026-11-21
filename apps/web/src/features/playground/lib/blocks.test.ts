import { describe, expect, it } from 'vitest';
import { createBlock, createStage, deriveTools, moveBlock, toStrategy } from './blocks';

describe('createStage', () => {
    it('starts with the three editing blocks plus the locked answer block', () => {
        const stage = createStage();
        expect(stage.blocks.map((block) => block.type)).toEqual([
            'prompt',
            'news',
            'technicals',
            'output_format',
        ]);
    });

    it('gives every block a unique id', () => {
        const stage = createStage();
        const ids = stage.blocks.map((block) => block.id);
        expect(new Set(ids).size).toBe(ids.length);
    });
});

describe('deriveTools', () => {
    it('derives the tools a technicals filter needs, without any live-only tool', () => {
        const tools = deriveTools(createStage().blocks);
        expect(tools).toContain('get_technical_indicators');
        expect(tools).toContain('get_key_metrics');
        expect(tools).toContain('get_stock_quote');
        expect(tools).not.toContain('run_stock_screener');
        expect(tools).not.toContain('web_search');
    });

    it('does not ask for indicators when no block needs them', () => {
        const tools = deriveTools([createBlock('prompt'), createBlock('output_format')]);
        expect(tools).not.toContain('get_technical_indicators');
    });
});

describe('moveBlock', () => {
    const stage = createStage();

    it('swaps two content blocks', () => {
        const moved = moveBlock(stage.blocks, 0, 1);
        expect(moved.map((block) => block.type).slice(0, 2)).toEqual(['news', 'prompt']);
    });

    it('refuses to move a block past the terminal block', () => {
        const blocks = stage.blocks;
        const lastContentIndex = blocks.length - 2;
        expect(moveBlock(blocks, lastContentIndex, 1)).toBe(blocks);
    });

    it('returns the same array when the move is out of bounds', () => {
        expect(moveBlock(stage.blocks, 0, -1)).toBe(stage.blocks);
    });
});

describe('toStrategy', () => {
    it('pins cadence, trims the name and keeps the terminal block last', () => {
        const stage = createStage();
        const strategy = toStrategy(stage, '  My bot  ', 'x'.repeat(300));

        expect(strategy.cadence).toBe('3h');
        expect(strategy.name).toBe('My bot');
        expect(strategy.description).toHaveLength(200);
        expect(strategy.stages).toHaveLength(1);
        expect(strategy.stages[0].blocks.at(-1)?.type).toBe('output_format');
    });

    it('falls back to a name rather than an empty one', () => {
        expect(toStrategy(createStage(), '   ', '').name).toBe('My first bot');
    });
});
