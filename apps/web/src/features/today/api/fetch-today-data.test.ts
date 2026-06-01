import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { __resetTodayCacheForTests, buildHistoryGroup, fetchTodayData } from './fetch-today-data';

let mockSupabaseClient: Record<string, unknown> | null = null;
vi.mock('~/lib/supabase', () => ({
    getSupabaseServerClient: vi.fn(() => mockSupabaseClient),
}));

/**
 * Build a Supabase query-builder chain mock. Terminal calls resolve to `terminal`.
 */
function makeChain(terminal: { data: unknown[]; error: unknown } = { data: [], error: null }) {
    const promise = Promise.resolve(terminal);
    const chain: Record<string, unknown> = {};
    for (const m of ['select', 'eq', 'gte', 'order', 'in', 'or']) {
        chain[m] = vi.fn().mockReturnValue(chain);
    }
    chain.limit = vi.fn().mockImplementation(() => promise);
    chain.single = vi.fn().mockImplementation(() => promise);
    return chain;
}

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
    beforeEach(() => __resetTodayCacheForTests());
    afterEach(() => __resetTodayCacheForTests());

    it('does not load reasoning logs and does not return them in TodayData payload', async () => {
        const fromSpy = vi.fn().mockImplementation((_table) => makeChain());
        const rpcSpy = vi.fn().mockImplementation(() => makeChain());
        mockSupabaseClient = { from: fromSpy, rpc: rpcSpy };

        const result = await fetchTodayData();

        // ASSERT 1: The 'llm_reasoning_logs' table was NEVER queried (Zero-Load)
        expect(fromSpy).not.toHaveBeenCalledWith('llm_reasoning_logs');

        // ASSERT 2: The returned data does not have the 'logs' property
        expect(result).not.toHaveProperty('logs');
    });

    it('consolidates price_history queries into a single RPC call (no raw 5000-row query)', async () => {
        const fromSpy = vi.fn().mockImplementation((_table) => makeChain());
        const rpcSpy = vi.fn().mockImplementation(() => makeChain());
        mockSupabaseClient = { from: fromSpy, rpc: rpcSpy };

        await fetchTodayData();

        // price_history must be fetched via the RPC, not via from('price_history')
        const priceHistoryFromCalls = fromSpy.mock.calls.filter(
            (call) => call[0] === 'price_history',
        );
        expect(priceHistoryFromCalls.length).toBe(0);

        // The RPC must be called once
        expect(rpcSpy).toHaveBeenCalledTimes(1);
        expect(rpcSpy.mock.calls[0][0]).toBe('latest_per_ticker_per_day');
    });
});

describe('fetchTodayData warm in-memory cache', () => {
    beforeEach(() => __resetTodayCacheForTests());
    afterEach(() => __resetTodayCacheForTests());

    it('returns a warm in-memory cache hit on the second call within 60s (zero Supabase calls)', async () => {
        const fromSpy = vi.fn().mockImplementation((_table) => makeChain());
        const rpcSpy = vi.fn().mockImplementation(() => makeChain());
        mockSupabaseClient = { from: fromSpy, rpc: rpcSpy };

        const first = await fetchTodayData();
        const callCountAfterFirst = fromSpy.mock.calls.length + rpcSpy.mock.calls.length;

        const second = await fetchTodayData();
        const callCountAfterSecond = fromSpy.mock.calls.length + rpcSpy.mock.calls.length;

        expect(callCountAfterFirst).toBeGreaterThan(0);
        expect(callCountAfterSecond).toBe(callCountAfterFirst);
        expect(second.todayDateString).toBe(first.todayDateString);
    });
});
