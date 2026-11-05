import { describe, expect, it } from 'vitest';
import {
    CONVICTION_NEUTRAL_SCORE,
    meanConvictionPoints,
    normalizeConvictionPoints,
    resolveConvictionScore,
} from './conviction';

describe('conviction helpers', () => {
    it('maps a coin flip to neutral 50', () => {
        expect(normalizeConvictionPoints(0)).toBeCloseTo(CONVICTION_NEUTRAL_SCORE, 6);
    });

    it('keeps positive and negative scores symmetric around 50', () => {
        expect(normalizeConvictionPoints(25) + normalizeConvictionPoints(-25)).toBeCloseTo(100, 6);
    });

    it('stays inside the 0-100 band for extreme inputs', () => {
        expect(normalizeConvictionPoints(10_000)).toBeGreaterThan(50);
        expect(normalizeConvictionPoints(10_000)).toBeLessThanOrEqual(100);
        expect(normalizeConvictionPoints(-10_000)).toBeLessThan(50);
        expect(normalizeConvictionPoints(-10_000)).toBeGreaterThanOrEqual(0);
    });

    it('falls back to neutral for non-finite input', () => {
        expect(normalizeConvictionPoints(Number.NaN)).toBe(CONVICTION_NEUTRAL_SCORE);
    });

    it('averages only scored rows', () => {
        const predictions = [
            { conviction_score: 40.5 },
            { conviction_score: null },
            { conviction_score: -40.5 },
            {},
        ];
        expect(meanConvictionPoints(predictions)).toBeCloseTo(0, 6);
    });

    it('returns null when nothing has been scored', () => {
        expect(meanConvictionPoints([{ conviction_score: null }, {}])).toBeNull();
        expect(meanConvictionPoints([])).toBeNull();
    });

    it('resolves an unscored set to neutral rather than zero', () => {
        expect(resolveConvictionScore([{ conviction_score: null }])).toBe(CONVICTION_NEUTRAL_SCORE);
    });

    it('scores an honest 60% model above neutral', () => {
        const score = resolveConvictionScore(
            Array.from({ length: 20 }, (_, index) => ({
                conviction_score: index < 12 ? 18.2322 : -22.3144,
            })),
        );
        expect(score).toBeGreaterThan(50);
        expect(score).toBeLessThan(55);
    });
});
