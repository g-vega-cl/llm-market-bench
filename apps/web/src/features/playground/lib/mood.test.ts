import { describe, expect, it } from 'vitest';
import { moodAsOf, moodSentence, moodTone, normalizeMood } from './mood';

const NOW = Date.parse('2026-11-20T18:00:00Z');

describe('normalizeMood', () => {
    it('returns a fresh reading with direction and confidence', () => {
        const mood = normalizeMood(
            {
                market_direction: 'BULLISH',
                sentiment_label: 'Risk-on',
                confidence_score: 78,
                created_at: '2026-11-20T17:00:00Z',
            },
            NOW,
        );

        expect(mood).toEqual({
            kind: 'fresh',
            direction: 'BULLISH',
            confidence: 78,
            label: 'Risk-on',
            asOf: '2026-11-20T17:00:00Z',
        });
        expect(moodTone(mood)).toBe('bullish');
    });

    it('treats a reading older than a day and a half as stale, not as fact', () => {
        const mood = normalizeMood(
            { market_direction: 'BEARISH', created_at: '2026-11-18T12:00:00Z' },
            NOW,
        );

        expect(mood.kind).toBe('stale');
        expect(mood.kind === 'stale' ? mood.reason : null).toBe('quiet');
        expect(moodTone(mood)).toBe('neutral');
    });

    it('is unknown without a row, an invalid direction or a timestamp', () => {
        expect(normalizeMood(null, NOW).kind).toBe('unknown');
        expect(normalizeMood({ market_direction: 'MOON' }, NOW).kind).toBe('unknown');
        expect(normalizeMood({ market_direction: 'NEUTRAL' }, NOW).kind).toBe('stale');
    });

    it('defaults confidence to zero when the column is missing', () => {
        const mood = normalizeMood(
            { market_direction: 'NEUTRAL', created_at: '2026-11-20T17:59:00Z' },
            NOW,
        );
        expect(mood.kind === 'fresh' ? mood.confidence : -1).toBe(0);
    });
});

describe('mood copy', () => {
    it('always states the fact in words', () => {
        const fresh = normalizeMood(
            {
                market_direction: 'BEARISH',
                confidence_score: 64,
                created_at: '2026-11-20T17:00:00Z',
            },
            NOW,
        );
        expect(moodSentence(fresh)).toBe('Desk reads bearish, 64% confidence.');
        expect(moodSentence({ kind: 'unknown', reason: 'unavailable' })).toMatch(/unavailable/);
    });

    it('formats the as-of time in Eastern time', () => {
        const mood = normalizeMood(
            { market_direction: 'NEUTRAL', created_at: '2026-11-20T17:00:00Z' },
            NOW,
        );
        expect(moodAsOf(mood)).toMatch(/Nov 20/);
        expect(moodAsOf({ kind: 'unknown', reason: 'unavailable' })).toBeNull();
    });
});
