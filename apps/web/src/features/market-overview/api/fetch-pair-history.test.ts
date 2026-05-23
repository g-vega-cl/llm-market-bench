import { describe, expect, it, vi } from 'vitest';

// Define the interface for mocked supabase chains
interface MockSupabaseChain {
    or: ReturnType<typeof vi.fn>;
    select: ReturnType<typeof vi.fn>;
    from: ReturnType<typeof vi.fn>;
}

let mockSupabaseClient: MockSupabaseChain | null = null;

vi.mock('~/lib/supabase-client', () => ({
    getSupabaseBrowserClient: vi.fn(() => mockSupabaseClient),
}));

import { fetchPairHistory } from './fetch-pair-history';

describe('fetchPairHistory', () => {
    it('queries bidirectionally and aligns returns correctly when DB stores pair in requested order', async () => {
        const mockData = [
            {
                ticker_a: 'BTCUSD',
                ticker_b: 'USO',
                pearson_corr: 0.85,
                spearman_corr: 0.82,
                returns_a_90d: 12.5,
                returns_b_90d: 5.0,
                correlation_runs: { run_date: '2026-05-17T16:00:00Z' },
            },
        ];

        const chain: MockSupabaseChain = {
            or: vi.fn(() => Promise.resolve({ data: mockData, error: null })),
            select: vi.fn(() => chain),
            from: vi.fn(() => chain),
        };
        mockSupabaseClient = chain;

        const results = await fetchPairHistory('BTCUSD', 'USO');

        expect(chain.from).toHaveBeenCalledWith('correlation_data');
        expect(chain.or).toHaveBeenCalledWith(
            'and(ticker_a.eq.BTCUSD,ticker_b.eq.USO),and(ticker_a.eq.USO,ticker_b.eq.BTCUSD)',
        );

        expect(results).toHaveLength(1);
        expect(results[0].returns_a_90d).toBe(12.5); // BTCUSD
        expect(results[0].returns_b_90d).toBe(5.0); // USO
    });

    it('queries bidirectionally and aligns returns correctly when DB stores pair in opposite order', async () => {
        const mockData = [
            {
                ticker_a: 'USO',
                ticker_b: 'BTCUSD',
                pearson_corr: 0.85,
                spearman_corr: 0.82,
                returns_a_90d: 5.0, // USO (returns_a_90d corresponds to ticker_a)
                returns_b_90d: 12.5, // BTCUSD (returns_b_90d corresponds to ticker_b)
                correlation_runs: { run_date: '2026-05-17T16:00:00Z' },
            },
        ];

        const chain: MockSupabaseChain = {
            or: vi.fn(() => Promise.resolve({ data: mockData, error: null })),
            select: vi.fn(() => chain),
            from: vi.fn(() => chain),
        };
        mockSupabaseClient = chain;

        // User requests BTCUSD first, then USO
        const results = await fetchPairHistory('BTCUSD', 'USO');

        expect(results).toHaveLength(1);
        expect(results[0].returns_a_90d).toBe(12.5); // correctly aligned to BTCUSD (user's tickerA)
        expect(results[0].returns_b_90d).toBe(5.0); // correctly aligned to USO (user's tickerB)
    });
});
