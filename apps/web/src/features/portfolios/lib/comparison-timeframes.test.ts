import { describe, expect, it } from 'vitest';
import type { ComparisonPayload } from '../api/fetch-portfolios';
import { computeTimeframeSlice, precomputeAllTimeframes } from './comparison-timeframes';

describe('comparison-timeframes', () => {
    const now = new Date('2026-11-13T12:00:00Z');
    const mockPayload: ComparisonPayload = {
        startDate: '2026-07-01',
        endDate: '2026-11-13',
        portfolios: [
            {
                portfolioId: 'p-1',
                ownerId: 'agent-alpha',
                performance: [
                    { date: '2026-07-01', totalEquity: 80000, value: 0 },
                    { date: '2026-11-10', totalEquity: 100000, value: 25 },
                    { date: '2026-11-13', totalEquity: 105000, value: 31.25 },
                ],
            },
            {
                portfolioId: 'p-2',
                ownerId: 'agent-beta',
                performance: [
                    { date: '2026-07-01', totalEquity: 100000, value: 0 },
                    { date: '2026-11-10', totalEquity: 90000, value: -10 },
                    { date: '2026-11-13', totalEquity: 108000, value: 8 },
                ],
            },
        ],
        benchmarkData: {
            SPY: [
                { date: '2026-07-01', price: 500 },
                { date: '2026-11-10', price: 540 },
                { date: '2026-11-13', price: 550 },
            ],
        },
    };

    it('returns empty slices when comparisonData is undefined', () => {
        expect(computeTimeframeSlice(undefined, '90d', now)).toEqual({
            portfolios: [],
            benchmarkData: {},
        });
    });

    it('precomputes all 4 timeframes and ranks portfolios by window return descending', () => {
        const slices = precomputeAllTimeframes(mockPayload, now);

        // Over 7d (since 2026-11-06), agent-beta went 90k -> 108k (+20%) vs agent-alpha 100k -> 105k (+5%)
        expect(slices['7d'].portfolios[0].portfolioId).toBe('p-2');
        expect(slices['7d'].portfolios[0].performance[1].value).toBeCloseTo(20, 2);
        expect(slices['7d'].benchmarkData.SPY).toHaveLength(2);

        // Over all time (since 2026-07-01), agent-alpha went 80k -> 105k (+31.25%) vs agent-beta 100k -> 108k (+8%)
        expect(slices.all.portfolios[0].portfolioId).toBe('p-1');
        expect(slices.all.portfolios[0].performance[2].value).toBeCloseTo(31.25, 2);
        expect(slices.all.benchmarkData.SPY).toHaveLength(3);
    });

    it('derives cutoffDate deterministically from comparisonData.endDate when now is omitted', () => {
        const slices = precomputeAllTimeframes(mockPayload);
        expect(slices['7d'].portfolios[0].portfolioId).toBe('p-2');
        expect(slices['7d'].portfolios[0].performance).toHaveLength(2);
    });
});
