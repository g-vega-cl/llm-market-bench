import { describe, expect, it, vi } from 'vitest';

let mockSupabaseClient: Record<string, unknown> | null = null;
vi.mock('~/lib/supabase-client', () => ({
    getSupabaseBrowserClient: vi.fn(() => mockSupabaseClient),
}));

import { fetchCauseAndEffect } from './fetch-cause-and-effect';

describe('fetchCauseAndEffect', () => {
    it('applies the limit parameter to the query when provided', async () => {
        let appliedLimit: number | undefined;
        const fromSpy = vi.fn().mockImplementation(() => {
            const chain = {
                select: vi.fn().mockReturnThis(),
                order: vi.fn().mockReturnThis(),
                limit: vi.fn().mockImplementation((l) => {
                    appliedLimit = l;
                    return Promise.resolve({ data: [], error: null });
                }),
            };
            // Mock await behavior
            return chain;
        });

        mockSupabaseClient = { from: fromSpy };

        await fetchCauseAndEffect(5);

        expect(appliedLimit).toBe(5);
    });
});
