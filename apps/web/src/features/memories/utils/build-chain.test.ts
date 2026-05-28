import type { Memory } from '@llm-market-bench/database';
import { describe, expect, it } from 'vitest';
import { buildChain } from './build-chain';

describe('buildChain', () => {
    it('should return empty chain if target memory is not found', () => {
        const result = buildChain('missing', []);
        expect(result.chain).toEqual([]);
        expect(result.targetMemory).toBeNull();
    });

    it('should build a full chronological tree chain starting from any node', () => {
        // Create a mock tree:
        // Root (A) -> Child B -> Child C
        //          -> Child D
        const allMemories = [
            { id: 'C', content: 'Leaf C', parent_id: 'B', created_at: '2026-05-03T00:00:00Z' },
            { id: 'B', content: 'Child B', parent_id: 'A', created_at: '2026-05-02T00:00:00Z' },
            { id: 'A', content: 'Root A', parent_id: null, created_at: '2026-05-01T00:00:00Z' },
            { id: 'D', content: 'Child D', parent_id: 'A', created_at: '2026-05-04T00:00:00Z' },
            {
                id: 'Unrelated',
                content: 'Unrelated',
                parent_id: null,
                created_at: '2026-05-05T00:00:00Z',
            },
        ] as Memory[];

        // 1. Select the root node A
        const resultA = buildChain('A', allMemories);
        expect(resultA.targetMemory?.id).toBe('A');
        // The chain should include A, B, C, D sorted by created_at: A -> B -> C -> D
        expect(resultA.chain.map((m) => m.id)).toEqual(['A', 'B', 'C', 'D']);

        // 2. Select a middle node B
        const resultB = buildChain('B', allMemories);
        expect(resultB.targetMemory?.id).toBe('B');
        // Even when selecting B, it should traverse up to A, then collect all descendants
        expect(resultB.chain.map((m) => m.id)).toEqual(['A', 'B', 'C', 'D']);

        // 3. Select a leaf node C
        const resultC = buildChain('C', allMemories);
        expect(resultC.targetMemory?.id).toBe('C');
        // Even when selecting C, it should traverse up to A, then collect all descendants
        expect(resultC.chain.map((m) => m.id)).toEqual(['A', 'B', 'C', 'D']);
    });
});
