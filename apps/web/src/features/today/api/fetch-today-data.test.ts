import { beforeEach, describe, expect, it, vi } from 'vitest';

// Module-level mock for Supabase client
let mockSupabaseClient: Record<string, unknown> | null = null;
vi.mock('~/lib/supabase', () => ({
    getSupabaseServerClient: vi.fn(() => mockSupabaseClient),
}));

import {
    buildHistoryGroup,
    clearTodayDataCache,
    fetchLatestMarketFeeling,
    fetchTodayData,
} from './fetch-today-data';

beforeEach(() => {
    clearTodayDataCache();
});

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

    it('applies the limit parameter to the heavy feed queries', async () => {
        const appliedLimits: number[] = [];
        const fromSpy = vi.fn().mockImplementation((table) => {
            const chain = {
                select: vi.fn().mockReturnThis(),
                eq: vi.fn().mockReturnThis(),
                gte: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation((l) => {
                    if (
                        ['newsletter_snapshots', 'trades', 'decisions', 'memories'].includes(table)
                    ) {
                        appliedLimits.push(l);
                    }
                    return Promise.resolve({ data: [], error: null });
                }),
                in: vi.fn().mockReturnThis(),
                or: vi.fn().mockReturnThis(),
            };
            return chain;
        });

        mockSupabaseClient = { from: fromSpy };

        // Bypass cache by updating the cache TTL globally or passing a refresh trigger
        await fetchTodayData(5);

        // We expect 5 calls with limit(5): newsletters, trades, decisions, memories, and futureEvents (which also uses the memories table)
        expect(appliedLimits).toEqual([5, 5, 5, 5, 5]);
    });

    it('bypasses the cache when a larger limit is requested than what was cached', async () => {
        const appliedLimits: number[] = [];
        const fromSpy = vi.fn().mockImplementation((table) => {
            const chain = {
                select: vi.fn().mockReturnThis(),
                eq: vi.fn().mockReturnThis(),
                gte: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation((l) => {
                    if (
                        ['newsletter_snapshots', 'trades', 'decisions', 'memories'].includes(table)
                    ) {
                        appliedLimits.push(l);
                    }
                    return Promise.resolve({ data: [], error: null });
                }),
                in: vi.fn().mockReturnThis(),
                or: vi.fn().mockReturnThis(),
            };
            return chain;
        });

        mockSupabaseClient = { from: fromSpy };

        // 1. Fetch with limit 5
        await fetchTodayData(5);
        expect(appliedLimits).toEqual([5, 5, 5, 5, 5]);

        // Clear appliedLimits list to record subsequent queries
        appliedLimits.length = 0;

        // 2. Fetch with limit 50 (should bypass cache since 50 > 5)
        await fetchTodayData(50);
        expect(appliedLimits).toEqual([50, 50, 50, 50, 50]);

        // Clear appliedLimits list again
        appliedLimits.length = 0;

        // 3. Fetch with limit 10 (should hit cache since 10 <= 50)
        await fetchTodayData(10);
        expect(appliedLimits).toEqual([]); // No queries should be made (cache hit)
    });

    it('fetchLatestMarketFeeling queries only market_feeling table with limit 1', async () => {
        const queriedTables: string[] = [];
        const limitValues: number[] = [];
        const fromSpy = vi.fn().mockImplementation((table) => {
            queriedTables.push(table);
            const chain = {
                select: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation((l) => {
                    limitValues.push(l);
                    return Promise.resolve({ data: [{ sentiment_label: 'Bullish' }], error: null });
                }),
            };
            return chain;
        });

        mockSupabaseClient = { from: fromSpy };

        const result = await fetchLatestMarketFeeling();
        expect(queriedTables).toEqual(['market_feeling']);
        expect(limitValues).toEqual([1]);
        expect(result).toEqual({ sentiment_label: 'Bullish' });
    });

    it('queries trades table with joined decisions (*, portfolios(owner_id), decisions(*))', async () => {
        const selectQueries: Record<string, string> = {};
        const fromSpy = vi.fn().mockImplementation((table) => {
            const chain = {
                select: vi.fn().mockImplementation((selectStr) => {
                    selectQueries[table] = selectStr;
                    return chain;
                }),
                eq: vi.fn().mockReturnThis(),
                gte: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation(() => Promise.resolve({ data: [], error: null })),
                in: vi.fn().mockImplementation(() => Promise.resolve({ data: [], error: null })),
                or: vi.fn().mockReturnThis(),
            };
            return chain;
        });

        mockSupabaseClient = { from: fromSpy };

        await fetchTodayData();
        expect(selectQueries.trades).toBe('*, portfolios(owner_id), decisions(*)');
    });

    it('allows tradesLimit to specifically control the trades query limit independently of the general feed limit', async () => {
        const queryLimits: Record<string, number> = {};
        const fromSpy = vi.fn().mockImplementation((table) => {
            const chain = {
                select: vi.fn().mockReturnThis(),
                eq: vi.fn().mockReturnThis(),
                gte: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation((l) => {
                    queryLimits[table] = l;
                    return Promise.resolve({ data: [], error: null });
                }),
                in: vi.fn().mockReturnThis(),
                or: vi.fn().mockReturnThis(),
            };
            return chain;
        });

        mockSupabaseClient = { from: fromSpy };

        // When fetching with general limit 50 and tradesLimit 200:
        await fetchTodayData(50, 200);

        expect(queryLimits.trades).toBe(200);
        expect(queryLimits.newsletter_snapshots).toBe(50);
        expect(queryLimits.decisions).toBe(50);
        expect(queryLimits.memories).toBe(50);
    });

    it('populates macroLastUpdated and macroStats formattedTime from market_data_cache fetched_at', async () => {
        const estToday = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
        const mockCacheRows = [
            {
                ticker: 'SPY',
                price: 520.5,
                today_pct_change: 0.75,
                stdev_pct: 0.5,
                regime_flag: 'Normal',
                market_cap: 500000000,
                fetched_at: `${estToday}T14:45:00Z`,
            },
            {
                ticker: 'QQQ',
                price: 450.0,
                today_pct_change: 1.2,
                stdev_pct: 0.6,
                regime_flag: 'Normal',
                market_cap: 300000000,
                fetched_at: `${estToday}T14:40:00Z`,
            },
        ];

        const fromSpy = vi.fn().mockImplementation((table) => {
            const chain = {
                select: vi.fn().mockReturnThis(),
                eq: vi.fn().mockReturnThis(),
                gte: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation(() => Promise.resolve({ data: [], error: null })),
                in: vi.fn().mockImplementation(() => {
                    if (table === 'market_data_cache') {
                        return Promise.resolve({ data: mockCacheRows, error: null });
                    }
                    return Promise.resolve({ data: [], error: null });
                }),
                or: vi.fn().mockReturnThis(),
            };
            return chain;
        });

        mockSupabaseClient = { from: fromSpy };

        const result = await fetchTodayData();

        expect(result.macroLastUpdated).toBe('10:45 AM ET');
        const spyStat = result.macroStats.find((s) => s.ticker === 'SPY');
        expect(spyStat).toBeDefined();
        expect(spyStat?.fetchedAt).toBe(`${estToday}T14:45:00Z`);
        expect(spyStat?.formattedTime).toBe('10:45 AM ET');
    });

    it('queries intraday_market_news and formats items in TodayData payload', async () => {
        const mockNews = [
            {
                id: 'news-1',
                headline: 'Fed Chair Powell Speaks on Policy',
                summary: 'Discussion on inflation targets.',
                source: 'Benzinga Wire',
                url: 'https://example.com/fed',
                tickers: ['SPY', 'QQQ'],
                event_timestamp: '2026-10-05T14:30:00Z',
                jev_choice: 'MARKET_MOVING',
                jev_confidence: 88.0,
                source_id_hash: 'hash_fed_1',
                created_at: '2026-10-05T14:32:00Z',
            },
        ];

        const fromSpy = vi.fn().mockImplementation((table) => {
            const chain = {
                select: vi.fn().mockReturnThis(),
                eq: vi.fn().mockReturnThis(),
                gte: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation(() => {
                    if (table === 'intraday_market_news') {
                        return Promise.resolve({ data: mockNews, error: null });
                    }
                    return Promise.resolve({ data: [], error: null });
                }),
                in: vi.fn().mockReturnThis(),
                or: vi.fn().mockReturnThis(),
            };
            return chain;
        });

        mockSupabaseClient = { from: fromSpy };

        const result = await fetchTodayData();

        expect(fromSpy).toHaveBeenCalledWith('intraday_market_news');
        expect(result.intradayNews).toHaveLength(1);
        expect(result.intradayNews[0].headline).toBe('Fed Chair Powell Speaks on Policy');
        expect(result.intradayNews[0].jev_choice).toBe('MARKET_MOVING');
        expect(result.intradayNews[0].formattedTime).toBeDefined();
    });

    it('returns previous cached data instead of empty payload when a new fetch fails due to network or database error', async () => {
        const mockNews = [
            {
                id: 'news-1',
                headline: 'Cached News Headline',
                summary: 'Discussion.',
                source: 'Benzinga Wire',
                url: 'https://example.com/cached',
                tickers: ['SPY'],
                event_timestamp: '2026-10-05T14:30:00Z',
                jev_choice: 'MARKET_MOVING',
                jev_confidence: 90.0,
                source_id_hash: 'hash_cached_1',
                created_at: '2026-10-05T14:32:00Z',
            },
        ];

        let shouldFail = false;
        const fromSpy = vi.fn().mockImplementation((table) => {
            const chain = {
                select: vi.fn().mockReturnThis(),
                eq: vi.fn().mockReturnThis(),
                gte: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation(() => {
                    if (shouldFail) {
                        return Promise.reject(new Error('Network error: connection lost'));
                    }
                    if (table === 'intraday_market_news') {
                        return Promise.resolve({ data: mockNews, error: null });
                    }
                    return Promise.resolve({ data: [], error: null });
                }),
                in: vi.fn().mockImplementation(() => {
                    if (shouldFail) {
                        return Promise.reject(new Error('Network error: connection lost'));
                    }
                    return Promise.resolve({ data: [], error: null });
                }),
                or: vi.fn().mockReturnThis(),
            };
            return chain;
        });

        mockSupabaseClient = { from: fromSpy };

        // 1. Prime the cache with initial successful fetch (limit 5)
        const initialResult = await fetchTodayData(5);
        expect(initialResult.intradayNews).toHaveLength(1);
        expect(initialResult.intradayNews[0].headline).toBe('Cached News Headline');

        // 2. Now simulate network disconnection and request limit 50 (bypassing in-memory limit check)
        shouldFail = true;
        const fallbackResult = await fetchTodayData(50);

        // MUST return the cached data from step 1 instead of erasing it with empty array []
        expect(fallbackResult.intradayNews).toHaveLength(1);
        expect(fallbackResult.intradayNews[0].headline).toBe('Cached News Headline');

        // 3. Verify internal cache was NOT overwritten with empty arrays
        const cachedCheck = await fetchTodayData(5);
        expect(cachedCheck.intradayNews).toHaveLength(1);
        expect(cachedCheck.intradayNews[0].headline).toBe('Cached News Headline');
    });

    it('throws an error on cold start failure when no cached data exists', async () => {
        const fromSpy = vi.fn().mockImplementation(() => {
            const chain = {
                select: vi.fn().mockReturnThis(),
                eq: vi.fn().mockReturnThis(),
                gte: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation(() => {
                    return Promise.reject(new Error('Network error: no connection on cold start'));
                }),
                in: vi.fn().mockImplementation(() => {
                    return Promise.reject(new Error('Network error: no connection on cold start'));
                }),
                or: vi.fn().mockReturnThis(),
            };
            return chain;
        });

        mockSupabaseClient = { from: fromSpy };

        // Cold start with no cache: should throw to allow React Query retry loop
        await expect(fetchTodayData(50)).rejects.toThrow(
            'Network error: no connection on cold start',
        );
    });
});
