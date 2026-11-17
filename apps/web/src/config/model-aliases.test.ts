import { describe, expect, it } from 'vitest';
import { isLegacyModelId, legacyModelLabel } from './model-aliases';

describe('model-aliases', () => {
    it('maps every retired id to the label of the model that actually ran', () => {
        expect(legacyModelLabel('gpt-5.6-luna')).toBe('GPT-5.6 Luna');
        expect(legacyModelLabel('deepseek-v4-flash')).toBe('DeepSeek Flash');
        expect(legacyModelLabel('MiniMax-M3')).toBe('MiniMax M3');
    });

    it('is case and whitespace tolerant', () => {
        expect(legacyModelLabel('  MiniMax-M3 ')).toBe('MiniMax M3');
        expect(legacyModelLabel('GPT-5.6-LUNA')).toBe('GPT-5.6 Luna');
    });

    it('does not treat a live model id as retired', () => {
        expect(legacyModelLabel('MiniMax-M3.1-Flash')).toBeUndefined();
        expect(legacyModelLabel('gpt-6-luna')).toBeUndefined();
        expect(legacyModelLabel('deepseek-flash')).toBeUndefined();
        expect(legacyModelLabel(null)).toBeUndefined();
        expect(legacyModelLabel(undefined)).toBeUndefined();
        expect(legacyModelLabel('')).toBeUndefined();
    });

    it('reports legacy membership', () => {
        expect(isLegacyModelId('gpt-5.6-luna')).toBe(true);
        expect(isLegacyModelId('gpt-6-luna')).toBe(false);
    });
});
