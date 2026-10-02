import { describe, expect, it, vi } from 'vitest';
import { memoriesQueries } from './options';

describe('memoriesQueries options config', () => {
    it('sets staleTime to Infinity for the memory detail query', () => {
        const options = memoriesQueries.detail({ id: 'test-memory-id' });
        expect(options.staleTime).toBe(Number.POSITIVE_INFINITY);
    });

    it('sets staleTime to Infinity for the memory sources query', () => {
        const options = memoriesQueries.sources({ id: 'test-memory-id', sourceIds: ['src-1'] });
        expect(options.staleTime).toBe(Number.POSITIVE_INFINITY);
    });

    it('sets staleTime to Infinity for the resolution child query', () => {
        const options = memoriesQueries.resolutionChild({ parentId: 'test-parent-id' });
        expect(options.staleTime).toBe(Number.POSITIVE_INFINITY);
    });

    it('sets staleTime to Infinity for the cause and effect query', () => {
        const options = memoriesQueries.causeAndEffect({ eventId: 'test-event-id' });
        expect(options.staleTime).toBe(Number.POSITIVE_INFINITY);
    });

    it('sets staleTime to 4 hours for the memory list query', () => {
        const options = memoriesQueries.list({ fetchFn: vi.fn() });
        expect(options.staleTime).toBe(1000 * 60 * 60 * 4);
    });

    it('configures search query with 5 minute staleTime and proper queryKey', async () => {
        const mockFetchFn = vi.fn().mockResolvedValue([{ id: 'm1', content: 'test' }]);
        const options = memoriesQueries.search({
            query: 'energy',
            limit: 50,
            fetchFn: mockFetchFn,
        });

        expect(options.queryKey).toEqual(['benchify', 'memories', 'search', 'energy']);
        expect(options.staleTime).toBe(1000 * 60 * 5);

        // biome-ignore lint/suspicious/noExplicitAny: testing queryFn execution
        const result = await (options as any).queryFn();
        expect(mockFetchFn).toHaveBeenCalledWith('energy', 50);
        expect(result).toEqual([{ id: 'm1', content: 'test' }]);
    });
});
