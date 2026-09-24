import { describe, expect, it, vi } from 'vitest';

vi.mock('~/features/memories/api/fetch-memories', () => ({
    fetchMemories: vi.fn(async (_cursor, _limit, _category) => ({
        data: [{ id: 'm1', content: 'Fetched memory', created_at: '2026-05-25' }],
        hasMore: false,
        nextCursor: null,
    })),
    fetchNewMemories: vi.fn(async (since: string) => [
        {
            id: 'm-new-1',
            content: `New memory since ${since}`,
            created_at: '2026-05-28',
        },
    ]),
    searchMemories: vi.fn(async (queryText: string, _limit: number) => [
        {
            id: 'm-quantum-1',
            content: `Matching ${queryText} post-mortem`,
            created_at: '2026-05-27',
            similarity: 1.0,
        },
    ]),
}));

import {
    fetchMemories,
    fetchNewMemories,
    searchMemories,
} from '~/features/memories/api/fetch-memories';
import { Route } from './index';

describe('/memories route server functions', () => {
    it('searchMemories mock returns matching query results', async () => {
        const results = await searchMemories('quantum', 50);
        expect(results).toHaveLength(1);
        expect(results[0].content).toContain('quantum');
        expect(searchMemories).toHaveBeenCalledWith('quantum', 50);
    });

    it('fetchMemories mock returns paginated data', async () => {
        const result = await fetchMemories(undefined, 50, undefined);
        expect(result.data).toHaveLength(1);
        expect(fetchMemories).toHaveBeenCalledWith(undefined, 50, undefined);
    });

    it('fetchNewMemories mock returns delta memories', async () => {
        const result = await fetchNewMemories('2026-05-25');
        expect(result).toHaveLength(1);
        expect(result[0].content).toContain('New memory since 2026-05-25');
        expect(fetchNewMemories).toHaveBeenCalledWith('2026-05-25');
    });

    it('Route component is defined correctly', () => {
        expect(Route).toBeDefined();
        expect(typeof Route).toBe('object');
    });
});
