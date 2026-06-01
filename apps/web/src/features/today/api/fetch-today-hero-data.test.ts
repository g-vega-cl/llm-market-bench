import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { TodayHeroData } from './fetch-today-hero-data';
import { __resetHeroCacheForTests, fetchTodayHeroData } from './fetch-today-hero-data';

let mockSupabaseClient: Record<string, unknown> | null = null;
vi.mock('~/lib/supabase', () => ({
    getSupabaseServerClient: vi.fn(() => mockSupabaseClient),
}));

/**
 * Build a Supabase query-builder chain mock. Terminal calls (`.limit(1)`,
 * `.single()`, etc.) resolve to the provided `terminal` data.
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

describe('fetchTodayHeroData', () => {
    beforeEach(() => {
        __resetHeroCacheForTests();
    });

    afterEach(() => {
        __resetHeroCacheForTests();
        vi.clearAllMocks();
    });

    it('only queries market_feeling (no newsletters, trades, decisions, memories, futureEvents, macroStats, priceUpdates)', async () => {
        const fromSpy = vi.fn().mockImplementation((_table: string) => makeChain());
        mockSupabaseClient = { from: fromSpy };

        await fetchTodayHeroData();

        const queriedTables = fromSpy.mock.calls.map((c) => c[0]);
        expect(queriedTables).toEqual(['market_feeling']);
    });

    it('returns minimal hero data shape with no below-the-fold fields', async () => {
        mockSupabaseClient = {
            from: vi.fn().mockReturnValue(
                makeChain({
                    data: [
                        {
                            id: 'mf-1',
                            sentiment_label: 'Bullish',
                            sentiment_emoji: '🐂',
                            market_direction: 'BULLISH',
                            confidence_score: 80,
                            why_explanation: 'because',
                            primary_concern: 'inflation',
                            created_at: '2026-06-01T14:00:00Z',
                            model_used: 'gpt-5',
                        },
                    ],
                    error: null,
                }),
            ),
        };

        const hero: TodayHeroData = await fetchTodayHeroData();

        expect(hero).toEqual(
            expect.objectContaining({
                marketFeeling: expect.objectContaining({
                    sentiment_label: 'Bullish',
                    formattedTime: expect.any(String),
                }),
                isMarketOpen: expect.any(Boolean),
                isSentimentStale: expect.any(Boolean),
                todayDateString: expect.any(String),
            }),
        );
        expect(hero).not.toHaveProperty('newsletters');
        expect(hero).not.toHaveProperty('trades');
        expect(hero).not.toHaveProperty('decisions');
        expect(hero).not.toHaveProperty('memories');
        expect(hero).not.toHaveProperty('priceUpdates');
        expect(hero).not.toHaveProperty('futureEvents');
        expect(hero).not.toHaveProperty('macroStats');
    });

    it('does not query market_data_cache or price_history or newsletters_snapshots (zero expensive I/O)', async () => {
        const fromSpy = vi.fn().mockImplementation((_table: string) => makeChain());
        mockSupabaseClient = { from: fromSpy };

        await fetchTodayHeroData();

        const queriedTables = fromSpy.mock.calls.map((c) => c[0]);
        expect(queriedTables).not.toContain('market_data_cache');
        expect(queriedTables).not.toContain('price_history');
        expect(queriedTables).not.toContain('newsletter_snapshots');
        expect(queriedTables).not.toContain('trades');
        expect(queriedTables).not.toContain('decisions');
        expect(queriedTables).not.toContain('memories');
    });

    it('returns a warm in-memory cache hit on the second call within 60s (zero Supabase calls)', async () => {
        const fromSpy = vi.fn().mockImplementation((_table: string) =>
            makeChain({
                data: [
                    {
                        id: 'mf-warm',
                        sentiment_label: 'Calm',
                        sentiment_emoji: '😌',
                        market_direction: null,
                        confidence_score: 50,
                        why_explanation: null,
                        primary_concern: null,
                        created_at: new Date().toISOString(),
                        model_used: null,
                    },
                ],
                error: null,
            }),
        );
        mockSupabaseClient = { from: fromSpy };

        const first = await fetchTodayHeroData();
        const callCountAfterFirst = fromSpy.mock.calls.length;

        const second = await fetchTodayHeroData();
        const callCountAfterSecond = fromSpy.mock.calls.length;

        expect(callCountAfterFirst).toBeGreaterThan(0);
        expect(callCountAfterSecond).toBe(callCountAfterFirst);
        expect(second.marketFeeling?.id).toBe(first.marketFeeling?.id);
    });
});
