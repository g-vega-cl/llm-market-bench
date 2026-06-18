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

import { fetchMemoryById, fetchMemoryChain, fetchReferencedNewsletters } from './fetch-memories';

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
