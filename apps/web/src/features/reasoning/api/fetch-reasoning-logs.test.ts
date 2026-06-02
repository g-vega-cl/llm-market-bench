import { describe, expect, it, vi } from 'vitest';

let mockSupabaseClient: Record<string, unknown> | null = null;
vi.mock('~/lib/supabase-client', () => ({
    getSupabaseBrowserClient: vi.fn(() => mockSupabaseClient),
}));

import { fetchReasoningLogs } from './fetch-reasoning-logs';

describe('fetchReasoningLogs', () => {
    it('applies the limit parameter to the query + 1 for pagination', async () => {
        let appliedLimit: number | undefined;
        const fromSpy = vi.fn().mockImplementation(() => {
            const chain = {
                select: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                lt: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation((l) => {
                    appliedLimit = l;
                    return Promise.resolve({ data: [], error: null });
                }),
            };
            return chain;
        });

        mockSupabaseClient = { from: fromSpy };

        await fetchReasoningLogs(undefined, 5);

        // Should be 5 + 1 = 6 because of pagination
        expect(appliedLimit).toBe(6);
    });
});
