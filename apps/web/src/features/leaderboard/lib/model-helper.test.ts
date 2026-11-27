import { describe, expect, it } from 'vitest';
import { formatUpDays, formatWinRate } from './model-helper';

describe('formatUpDays', () => {
    it('renders the raw counts beside the smoothed rate', () => {
        expect(formatUpDays(9, 10, 78.57)).toBe('9/10 · 78.6%');
        expect(formatUpDays(0, 12, 12.5)).toBe('0/12 · 12.5%');
    });

    it('shows 0/0 when no session moved, so the neutral 50% is explainable', () => {
        expect(formatUpDays(0, 0, 50)).toBe('0/0 · 50.0%');
    });

    it('falls back to the bare rate when counts are missing', () => {
        expect(formatUpDays(null, null, 64)).toBe('64.0%');
        expect(formatUpDays(undefined, undefined, 64)).toBe('64.0%');
        expect(formatUpDays(Number.NaN, 4, 64)).toBe('64.0%');
    });
});

describe('formatWinRate', () => {
    it('keeps the em dash for untraded competitors', () => {
        expect(formatWinRate(null)).toBe('—');
        expect(formatWinRate(58.33)).toBe('58.3%');
    });
});
