import { describe, expect, it, vi } from 'vitest';

interface MockSupabaseChain {
    eq: ReturnType<typeof vi.fn>;
    not: ReturnType<typeof vi.fn>;
    is: ReturnType<typeof vi.fn>;
    or: ReturnType<typeof vi.fn>;
    order: ReturnType<typeof vi.fn>;
    limit: ReturnType<typeof vi.fn>;
    lt: ReturnType<typeof vi.fn>;
    select: ReturnType<typeof vi.fn>;
    from: ReturnType<typeof vi.fn>;
}

let mockSupabaseClient: MockSupabaseChain | null = null;

vi.mock('~/lib/supabase-client', () => ({
    getSupabaseBrowserClient: vi.fn(() => mockSupabaseClient),
}));

import { fetchMemories } from './fetch-memories';

describe('fetchMemories - Category Filtering (TDD)', () => {
    it('queries academic_paper category using text-extraction operator (->>)', async () => {
        const mockData: unknown[] = [];
        const chain: MockSupabaseChain = {
            eq: vi.fn(() => chain),
            not: vi.fn(() => chain),
            is: vi.fn(() => chain),
            or: vi.fn(() => chain),
            order: vi.fn(() => chain),
            limit: vi.fn(() => chain),
            lt: vi.fn(() => chain),
            select: vi.fn(() => chain),
            from: vi.fn(() => chain),
        };
        chain.limit.mockImplementationOnce(() => Promise.resolve({ data: mockData, error: null }));
        mockSupabaseClient = chain;

        await fetchMemories(undefined, 50, 'academic_paper');

        expect(chain.from).toHaveBeenCalledWith('memories');
        expect(chain.eq).toHaveBeenCalledWith('memory_type', 'LESSON_LEARNED');
        expect(chain.eq).toHaveBeenCalledWith('metadata->>source_type', 'academic_paper');
    });

    it('queries post_mortem category using text-extraction operator (->>)', async () => {
        const mockData: unknown[] = [];
        const chain: MockSupabaseChain = {
            eq: vi.fn(() => chain),
            not: vi.fn(() => chain),
            is: vi.fn(() => chain),
            or: vi.fn(() => chain),
            order: vi.fn(() => chain),
            limit: vi.fn(() => chain),
            lt: vi.fn(() => chain),
            select: vi.fn(() => chain),
            from: vi.fn(() => chain),
        };
        chain.limit.mockImplementationOnce(() => Promise.resolve({ data: mockData, error: null }));
        mockSupabaseClient = chain;

        await fetchMemories(undefined, 50, 'post_mortem');

        expect(chain.from).toHaveBeenCalledWith('memories');
        expect(chain.not).toHaveBeenCalledWith('metadata->>analysis_window', 'is', null);
    });

    it('queries lesson_learned category using text-extraction operator (->>)', async () => {
        const mockData: unknown[] = [];
        const chain: MockSupabaseChain = {
            eq: vi.fn(() => chain),
            not: vi.fn(() => chain),
            is: vi.fn(() => chain),
            or: vi.fn(() => chain),
            order: vi.fn(() => chain),
            limit: vi.fn(() => chain),
            lt: vi.fn(() => chain),
            select: vi.fn(() => chain),
            from: vi.fn(() => chain),
        };
        chain.limit.mockImplementationOnce(() => Promise.resolve({ data: mockData, error: null }));
        mockSupabaseClient = chain;

        await fetchMemories(undefined, 50, 'lesson_learned');

        expect(chain.from).toHaveBeenCalledWith('memories');
        expect(chain.eq).toHaveBeenCalledWith('memory_type', 'LESSON_LEARNED');
        expect(chain.is).toHaveBeenCalledWith('metadata->>analysis_window', null);
        expect(chain.or).toHaveBeenCalledWith(
            'metadata->>source_type.is.null,metadata->>source_type.neq.academic_paper',
        );
    });
});
