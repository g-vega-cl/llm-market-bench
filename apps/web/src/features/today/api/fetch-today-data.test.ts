import { describe, expect, it, vi } from 'vitest';

// Module-level mock for Supabase client
let mockSupabaseClient: Record<string, unknown> | null = null;
vi.mock('~/lib/supabase', () => ({
    getSupabaseServerClient: vi.fn(() => mockSupabaseClient),
}));

import { buildHistoryGroup, fetchTodayData } from './fetch-today-data';

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

describe('fetchTodayData zero-load TDD checks', () => {
    it('does not load reasoning logs and does not return them in TodayData payload', async () => {
        const fromSpy = vi.fn().mockImplementation((_table) => {
            const chain = {
                select: vi.fn().mockReturnThis(),
                eq: vi.fn().mockReturnThis(),
                gte: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation(() => Promise.resolve({ data: [], error: null })),
                in: vi.fn().mockReturnThis(),
                or: vi.fn().mockReturnThis(),
            };
            return chain;
        });

        mockSupabaseClient = {
            from: fromSpy,
        };

        const result = await fetchTodayData();

        // ASSERT 1: The 'llm_reasoning_logs' table was NEVER queried (Zero-Load)
        expect(fromSpy).not.toHaveBeenCalledWith('llm_reasoning_logs');

        // ASSERT 2: The returned data does not have the 'logs' property
        expect(result).not.toHaveProperty('logs');
    });

    it('fully eliminates price_history queries from the web app client entirely', async () => {
        const fromSpy = vi.fn().mockImplementation((_table) => {
            const chain = {
                select: vi.fn().mockReturnThis(),
                eq: vi.fn().mockReturnThis(),
                gte: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation(() => Promise.resolve({ data: [], error: null })),
                in: vi.fn().mockReturnThis(),
                or: vi.fn().mockReturnThis(),
            };
            return chain;
        });

        mockSupabaseClient = {
            from: fromSpy,
        };

        await fetchTodayData();

        // Count how many times 'price_history' was queried
        const priceHistoryQueries = fromSpy.mock.calls.filter(
            (call) => call[0] === 'price_history',
        );

        // ASSERT: price_history queries should be exactly 0 (fully database-driven pre-calculation)
        expect(priceHistoryQueries.length).toBe(0);
    });

    it('maps pre-calculated macro volatility fields correctly from market_data_cache rows', async () => {
        const mockCacheRows = [
            {
                ticker: 'SPY',
                price: 512.5,
                market_cap: 0,
                fetched_at: '2026-06-01T15:00:00Z',
                today_pct_change: 1.25,
                stdev_pct: 0.85,
                regime_flag: 'Normal',
            },
        ];

        const fromSpy = vi.fn().mockImplementation((table) => {
            const chain = {
                select: vi.fn().mockReturnThis(),
                eq: vi.fn().mockReturnThis(),
                gte: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation(() => {
                    return Promise.resolve({ data: [], error: null });
                }),
                in: vi.fn().mockImplementation((_col, list) => {
                    if (table === 'market_data_cache' && list.includes('SPY')) {
                        return Promise.resolve({ data: mockCacheRows, error: null });
                    }
                    return chain;
                }),
                or: vi.fn().mockReturnThis(),
            };
            return chain;
        });

        mockSupabaseClient = {
            from: fromSpy,
        };

        // Bypass cache by updating the cache TTL globally or passing a refresh trigger
        const result = await fetchTodayData();
        const spyStat = result.macroStats.find((s) => s.ticker === 'SPY');

        expect(spyStat).toBeDefined();
        expect(spyStat?.price).toBe(512.5);
        expect(spyStat?.todayPctChange).toBe(1.25);
        expect(spyStat?.stdevPct).toBe(0.85);
        expect(spyStat?.regimeFlag).toBe('Normal');
    });
});
