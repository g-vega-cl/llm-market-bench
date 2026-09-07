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
});
