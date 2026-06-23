import { describe, expect, it, vi } from 'vitest';
import { conceptsQueries } from './options';

describe('conceptsQueries options config', () => {
    it('sets staleTime to Infinity for the concepts list query', () => {
        const options = conceptsQueries.list();
        expect(options.staleTime).toBe(Number.POSITIVE_INFINITY);
    });

    it('sets staleTime to Infinity for the concept memories query', () => {
        const options = conceptsQueries.memories('test-concept-id', vi.fn());
        expect(options.staleTime).toBe(Number.POSITIVE_INFINITY);
    });
});
