import { describe, expect, it, vi } from 'vitest';

let mockSupabaseClient: Record<string, unknown> | null = null;
vi.mock('~/lib/supabase-client', () => ({
    getSupabaseBrowserClient: vi.fn(() => mockSupabaseClient),
}));

import { fetchCauseAndEffect, fetchCauseAndEffectByEventId } from './fetch-cause-and-effect';

describe('fetchCauseAndEffect', () => {
    it('projects explicit scalar columns on event:memories to prevent vector embedding egress', async () => {
        let selectArg = '';
        const fromSpy = vi.fn().mockImplementation(() => ({
            select: vi.fn().mockImplementation((arg) => {
                selectArg = arg;
                return {
                    order: vi.fn().mockReturnValue(Promise.resolve({ data: [], error: null })),
                };
            }),
        }));
        mockSupabaseClient = { from: fromSpy };

        await fetchCauseAndEffect();
        expect(selectArg).not.toContain('event:memories(*)');
        expect(selectArg).toContain('event:memories(id, content, created_at)');
    });

    it('projects explicit scalar columns on event:memories in fetchCauseAndEffectByEventId', async () => {
        let selectArg = '';
        const fromSpy = vi.fn().mockImplementation(() => ({
            select: vi.fn().mockImplementation((arg) => {
                selectArg = arg;
                return {
                    eq: vi.fn().mockReturnThis(),
                    maybeSingle: vi
                        .fn()
                        .mockReturnValue(Promise.resolve({ data: null, error: null })),
                };
            }),
        }));
        mockSupabaseClient = { from: fromSpy };

        await fetchCauseAndEffectByEventId('event-123');
        expect(selectArg).not.toContain('event:memories(*)');
        expect(selectArg).toContain('event:memories(id, content, created_at)');
    });

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
