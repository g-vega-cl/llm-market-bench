import { describe, expect, it } from 'vitest';
import { modelLabel } from './model-label';

describe('modelLabel', () => {
    it('strips a trailing :free tier suffix', () => {
        expect(modelLabel('tencent/hy4-flash:free')).toBe('tencent/hy4-flash');
        expect(modelLabel('inclusionai/ling-3.2-flash:free')).toBe('inclusionai/ling-3.2-flash');
    });

    it('is case-insensitive on the suffix', () => {
        expect(modelLabel('vendor/model:FREE')).toBe('vendor/model');
    });

    it('keeps models that have no tier suffix', () => {
        expect(modelLabel('claude-haiku-5-5')).toBe('claude-haiku-5-5');
        expect(modelLabel('vendor/model:beta')).toBe('vendor/model:beta');
    });

    it('returns null for missing or blank values', () => {
        expect(modelLabel(null)).toBeNull();
        expect(modelLabel(undefined)).toBeNull();
        expect(modelLabel('   ')).toBeNull();
    });

    it('trims surrounding whitespace', () => {
        expect(modelLabel('  vendor/model:free ')).toBe('vendor/model');
    });
});
