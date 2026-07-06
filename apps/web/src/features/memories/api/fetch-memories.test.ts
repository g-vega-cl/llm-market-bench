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
    it('queries academic_paper category using direct memory_type column', async () => {
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
        expect(chain.eq).toHaveBeenCalledWith('memory_type', 'ACADEMIC_PAPER');
    });

    it('queries post_mortem category using direct memory_type column', async () => {
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
        expect(chain.eq).toHaveBeenCalledWith('memory_type', 'POST_MORTEM');
    });

    it('queries lesson_learned category using direct memory_type column', async () => {
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
    });

    it('applies the limit parameter + 1 for pagination', async () => {
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

        await fetchMemories(undefined, 5, 'all');

        expect(chain.limit).toHaveBeenCalledWith(6);
    });
});

import {
    fetchMemoryById,
    fetchMemoryChain,
    fetchReferencedNewsletters,
    searchMemories,
} from './fetch-memories';

describe('fetchMemoryById', () => {
    it('queries memories table by id', async () => {
        const mockData = { id: 'test-memory-id', content: 'test content' };
        const chain: MockSupabaseChain = {
            eq: vi.fn(() => chain),
            single: vi.fn(() => Promise.resolve({ data: mockData, error: null })),
            select: vi.fn(() => chain),
            from: vi.fn(() => chain),
        } as unknown as MockSupabaseChain;
        mockSupabaseClient = chain;

        const result = await fetchMemoryById('test-memory-id');

        expect(chain.from).toHaveBeenCalledWith('memories');
        expect(chain.eq).toHaveBeenCalledWith('id', 'test-memory-id');
        expect(result).toEqual(mockData);
    });

    it('returns null on PGRST116 single not found error code', async () => {
        const chain: MockSupabaseChain = {
            eq: vi.fn(() => chain),
            single: vi.fn(() => Promise.resolve({ data: null, error: { code: 'PGRST116' } })),
            select: vi.fn(() => chain),
            from: vi.fn(() => chain),
        } as unknown as MockSupabaseChain;
        mockSupabaseClient = chain;

        const result = await fetchMemoryById('nonexistent-id');
        expect(result).toBeNull();
    });
});

describe('fetchMemoryChain', () => {
    it('calls get_memory_chain RPC with target_id', async () => {
        const mockRpc = vi.fn().mockResolvedValue({ data: [], error: null });
        mockSupabaseClient = {
            rpc: mockRpc,
        } as unknown as MockSupabaseChain;

        const memoryId = 'test-memory-id';
        await fetchMemoryChain(memoryId);

        expect(mockRpc).toHaveBeenCalledWith('get_memory_chain', { target_id: memoryId });
    });
});

describe('fetchReferencedNewsletters', () => {
    it('returns empty array when sourceIds is empty', async () => {
        const result = await fetchReferencedNewsletters([]);
        expect(result).toEqual([]);
    });

    it('calls get_referenced_newsletter_snapshots RPC with target_source_ids', async () => {
        const mockRpc = vi
            .fn()
            .mockResolvedValue({ data: [{ source_id: 'src-1', content: 'test' }], error: null });
        mockSupabaseClient = {
            rpc: mockRpc,
        } as unknown as MockSupabaseChain;

        const sourceIds = ['src-1'];
        const result = await fetchReferencedNewsletters(sourceIds);

        expect(mockRpc).toHaveBeenCalledWith('get_referenced_newsletter_snapshots', {
            target_source_ids: sourceIds,
        });
        expect(result).toEqual([{ source_id: 'src-1', content: 'test' }]);
    });
});

describe('searchMemories (Fuzzy Levenshtein Search)', () => {
    it('fetches all memories and computes similarity score client-side', async () => {
        const mockData = [
            {
                id: 'id-1',
                content: 'Huge energy deal signed by Trump today',
                created_at: '2026-07-05',
            },
            { id: 'id-2', content: 'S&P 500 drop concerns investors', created_at: '2026-07-04' },
        ];

        // Mock Supabase to return the memories
        const mockOrder = vi.fn().mockResolvedValue({ data: mockData, error: null });
        const mockSelect = vi.fn(() => ({ order: mockOrder }));
        const chain = {
            from: vi.fn(() => ({ select: mockSelect })),
        };
        mockSupabaseClient = chain as unknown as MockSupabaseChain;

        const results = await searchMemories('energy trmp', 50);

        expect(chain.from).toHaveBeenCalledWith('memories');
        expect(mockSelect).toHaveBeenCalledWith('*, parent_id, status, relationship_type');

        // Check that results contain calculated similarity
        // "energy trmp" vs "Huge energy deal signed by Trump today"
        // "energy" matches "energy" (score 1.0)
        // "trmp" matches "Trump" (Levenshtein distance 1, length 5, score 1 - 1/5 = 0.8)
        // Avg = 0.9
        expect(results).toHaveLength(1); // id-2 should be excluded because similarity is 0
        expect(results[0].id).toBe('id-1');
        expect(results[0].similarity).toBeCloseTo(0.9, 2);
    });

    it('returns empty array when no memories match above threshold', async () => {
        const mockData = [
            { id: 'id-2', content: 'S&P 500 drop concerns investors', created_at: '2026-07-04' },
        ];

        const mockOrder = vi.fn().mockResolvedValue({ data: mockData, error: null });
        const mockSelect = vi.fn(() => ({ order: mockOrder }));
        const chain = {
            from: vi.fn(() => ({ select: mockSelect })),
        };
        mockSupabaseClient = chain as unknown as MockSupabaseChain;

        const results = await searchMemories('nuclear energy', 50);
        expect(results).toEqual([]);
    });
});
