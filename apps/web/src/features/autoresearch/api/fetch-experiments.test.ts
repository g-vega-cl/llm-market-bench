import { describe, expect, it, vi } from 'vitest';
import { fetchExperiments } from './fetch-experiments';

interface MockSupabaseChain {
    eq: ReturnType<typeof vi.fn>;
    order: ReturnType<typeof vi.fn>;
    select: ReturnType<typeof vi.fn>;
    from: ReturnType<typeof vi.fn>;
}

let mockSupabaseClient: MockSupabaseChain | null = null;

vi.mock('~/lib/supabase', () => ({
    getSupabaseServerClient: vi.fn(() => mockSupabaseClient),
}));

describe('fetchExperiments - Scoping (TDD)', () => {
    it('scopes database query to CORE_ANALYSIS_SYSTEM_PROMPT', async () => {
        const mockData = [{ id: '1', prompt_name: 'CORE_ANALYSIS_SYSTEM_PROMPT' }];
        const chain: MockSupabaseChain = {
            eq: vi.fn(() => chain),
            order: vi.fn(() => Promise.resolve({ data: mockData, error: null })),
            select: vi.fn(() => chain),
            from: vi.fn(() => chain),
        };
        mockSupabaseClient = chain;

        const result = await fetchExperiments();

        expect(chain.from).toHaveBeenCalledWith('prompt_experiments');
        expect(chain.eq).toHaveBeenCalledWith('prompt_name', 'CORE_ANALYSIS_SYSTEM_PROMPT');
        expect(result).toEqual(mockData);
    });
});
