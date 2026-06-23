import { describe, expect, it } from 'vitest';
import { reasoningQueries } from './options';

describe('reasoningQueries options config', () => {
    it('sets staleTime to Infinity for the reasoning detail query', () => {
        const options = reasoningQueries.detail({ id: 'test-reasoning-id' });
        expect(options.staleTime).toBe(Number.POSITIVE_INFINITY);
    });
});
