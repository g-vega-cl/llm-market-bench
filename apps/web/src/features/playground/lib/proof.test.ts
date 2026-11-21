import { describe, expect, it } from 'vitest';
import { formatPct, pickProof } from './proof';

describe('pickProof', () => {
    it('publishes the worst row beside the winner, with one as-of date', () => {
        const proof = pickProof({
            rows: [
                {
                    portfolioId: 'a',
                    label: 'Alpha',
                    returnPct: 4.2,
                    observations: 10,
                    series: [
                        { date: '2026-11-01', value: 100 },
                        { date: '2026-11-19', value: 104.2 },
                    ],
                },
            ],
            worst: {
                portfolioId: 'z',
                label: 'Zulu',
                returnPct: -6.4,
                observations: 10,
                series: [],
            },
            spy: [{ date: '2026-11-20', value: 100 }],
            medianReturnPct: -0.5,
            trackedCount: 9,
            windowDays: 30,
            degraded: false,
            spyUnavailable: false,
        });

        expect(proof.winner).toEqual({ label: 'Alpha', returnPct: 4.2 });
        expect(proof.worst).toEqual({ label: 'Zulu', returnPct: -6.4 });
        expect(proof.asOf).toBe('2026-11-19');
        expect(proof.trackedCount).toBe(9);
    });

    it('falls back to the benchmark date when no portfolio series exists', () => {
        const proof = pickProof({
            rows: [],
            worst: null,
            spy: [{ date: '2026-11-20', value: 100 }],
            medianReturnPct: null,
            trackedCount: null,
            windowDays: 30,
            degraded: false,
            spyUnavailable: false,
        });

        expect(proof.winner).toBeNull();
        expect(proof.asOf).toBe('2026-11-20');
    });

    it('survives a missing payload instead of throwing', () => {
        expect(pickProof(undefined).degraded).toBe(false);
        expect(pickProof({ degraded: true } as never).degraded).toBe(true);
    });
});

describe('formatPct', () => {
    it('signs positives and never prints NaN', () => {
        expect(formatPct(1.234)).toBe('+1.23%');
        expect(formatPct(-0.5)).toBe('-0.50%');
        expect(formatPct(null)).toBe('—');
    });
});
