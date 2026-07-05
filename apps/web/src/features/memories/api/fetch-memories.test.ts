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
    getGeminiEmbedding,
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

describe('getGeminiEmbedding', () => {
    it('sends POST request to gemini embedding API and returns values', async () => {
        const mockValues = [0.1, 0.2, 0.3];
        const mockResponse = {
            ok: true,
            status: 200,
            json: async () => ({ embedding: { values: mockValues } }),
        };
        const originalFetch = global.fetch;
        global.fetch = vi.fn().mockResolvedValue(mockResponse);

        process.env.GEMINI_API_KEY = 'test-api-key';

        const result = await getGeminiEmbedding('test query');
        expect(global.fetch).toHaveBeenCalled();
        expect(result).toEqual(mockValues);

        global.fetch = originalFetch;
    });
});

describe('searchMemories', () => {
    it('embeds query, runs match_memories RPC, fetches full memories, sorts by similarity', async () => {
        const mockValues = [0.1, 0.2, 0.3];
        const originalFetch = global.fetch;
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            json: async () => ({ embedding: { values: mockValues } }),
        });

        // Mock Supabase calls
        const mockMatchedRows = [
            { id: 'id-2', similarity: 0.8 },
            { id: 'id-1', similarity: 0.9 },
        ];
        const mockFullMemories = [
            { id: 'id-1', content: 'content 1', created_at: '2026-07-04' },
            { id: 'id-2', content: 'content 2', created_at: '2026-07-05' },
        ];

        // Create a chain that handles RPC and select.in
        // biome-ignore lint/suspicious/noExplicitAny: recursive mock chain for supabase test helper
        const chain: any = {
            rpc: vi.fn().mockResolvedValue({ data: mockMatchedRows, error: null }),
            from: vi.fn(() => chain),
            select: vi.fn(() => chain),
            in: vi.fn().mockResolvedValue({ data: mockFullMemories, error: null }),
        };
        mockSupabaseClient = chain;

        const results = await searchMemories('nuclear energy', 50, 0.4);

        // Check searchMemories logic
        expect(chain.rpc).toHaveBeenCalledWith('match_memories', {
            query_embedding: mockValues,
            match_threshold: 0.4,
            match_count: 50,
        });

        expect(chain.from).toHaveBeenCalledWith('memories');
        expect(chain.in).toHaveBeenCalledWith('id', ['id-2', 'id-1']);

        // Check that result list is sorted by similarity descending
        expect(results).toHaveLength(2);
        expect(results[0].id).toBe('id-1');
        expect(results[0].similarity).toBe(0.9);
        expect(results[1].id).toBe('id-2');
        expect(results[1].similarity).toBe(0.8);

        global.fetch = originalFetch;
    });
});
