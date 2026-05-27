import { describe, expect, it } from 'vitest';
import { buildHistoryGroup } from './fetch-today-data';

describe('buildHistoryGroup', () => {
    it('returns empty map when historyRows is null or empty', () => {
        const result = buildHistoryGroup(null, '2026-05-27');
        expect(result.size).toBe(0);

        const result2 = buildHistoryGroup([], '2026-05-27');
        expect(result2.size).toBe(0);
    });

    it('filters out records matching the current ET date', () => {
        const rows = [
            { ticker: 'SPY', price: 510, fetched_at: '2026-05-27T14:30:00Z' },
            { ticker: 'SPY', price: 508, fetched_at: '2026-05-26T16:00:00Z' },
        ];
        const result = buildHistoryGroup(rows, '2026-05-27');
        const spyHistory = result.get('SPY') || [];

        expect(spyHistory.length).toBe(1);
        expect(spyHistory[0].price).toBe(508);
        expect(spyHistory[0].fetched_at).toBe('2026-05-26T16:00:00Z');
    });

    it('deduplicates multiple intraday ticks keeping only the latest/most recent row per calendar date', () => {
        const rows = [
            // Today (2026-05-27) is excluded
            { ticker: 'USO', price: 132.0, fetched_at: '2026-05-27T14:30:00Z' },
            // Yesterday (2026-05-26) - multiple ticks
            { ticker: 'USO', price: 130.5, fetched_at: '2026-05-26T16:00:00Z' }, // Keep (latest for 26th)
            { ticker: 'USO', price: 130.2, fetched_at: '2026-05-26T15:30:00Z' }, // Skip
            { ticker: 'USO', price: 129.8, fetched_at: '2026-05-26T15:00:00Z' }, // Skip
            // Day before (2026-05-25) - multiple ticks
            { ticker: 'USO', price: 128.5, fetched_at: '2026-05-25T16:00:00Z' }, // Keep (latest for 25th)
            { ticker: 'USO', price: 128.0, fetched_at: '2026-05-25T14:00:00Z' }, // Skip
        ];

        const result = buildHistoryGroup(rows, '2026-05-27');
        const usoHistory = result.get('USO') || [];

        expect(usoHistory.length).toBe(2);
        expect(usoHistory[0].price).toBe(130.5);
        expect(usoHistory[0].fetched_at).toBe('2026-05-26T16:00:00Z');
        expect(usoHistory[1].price).toBe(128.5);
        expect(usoHistory[1].fetched_at).toBe('2026-05-25T16:00:00Z');
    });

    it('caps the history length at 30 days per ticker', () => {
        const rows: { ticker: string; price: number; fetched_at: string }[] = [];
        for (let i = 1; i <= 40; i++) {
            const dateStr = new Date(2026, 4, i).toISOString().split('T')[0];
            rows.push({
                ticker: 'SPY',
                price: 500 + i,
                fetched_at: `${dateStr}T16:00:00Z`,
            });
        }

        const result = buildHistoryGroup(rows, '2026-05-27');
        const spyHistory = result.get('SPY') || [];

        expect(spyHistory.length).toBe(30);
    });
});
