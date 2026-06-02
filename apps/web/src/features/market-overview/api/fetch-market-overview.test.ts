import { describe, expect, it, vi } from 'vitest';

let mockSupabaseClient: Record<string, unknown> | null = null;
vi.mock('~/lib/supabase-client', () => ({
    getSupabaseBrowserClient: vi.fn(() => mockSupabaseClient),
}));

import { fetchMarketOverviewData } from './fetch-market-overview';

describe('fetchMarketOverviewData', () => {
    it('applies the limit parameter to the query when provided', async () => {
        let appliedLimit: number | undefined;
        const fromSpy = vi.fn().mockImplementation((table) => {
            if (table === 'correlation_runs') {
                return {
                    select: vi.fn().mockReturnThis(),
                    order: vi.fn().mockReturnThis(),
                    limit: vi.fn().mockResolvedValue({
                        data: [{ id: 'run-id-1', tickers: ['SPY'] }],
                        error: null,
                    }),
                };
            }
            if (table === 'correlation_data') {
                return {
                    select: vi.fn().mockReturnThis(),
                    eq: vi.fn().mockReturnThis(),
                    limit: vi.fn().mockImplementation((l) => {
                        appliedLimit = l;
                        return Promise.resolve({ data: [], error: null });
                    }),
                };
            }
            // For market_feeling
            return {
                select: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockResolvedValue({
                    data: [],
                    error: null,
                }),
            };
        });

        mockSupabaseClient = { from: fromSpy };

        await fetchMarketOverviewData(5);

        expect(appliedLimit).toBe(5);
    });
});
