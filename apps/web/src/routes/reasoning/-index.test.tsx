import { describe, expect, it, vi } from 'vitest';
import { fetchReasoningLogs } from '~/features/reasoning/api/fetch-reasoning-logs';
import { Route } from './index';

vi.mock('~/features/reasoning/api/fetch-reasoning-logs', () => ({
    fetchReasoningLogs: vi.fn().mockResolvedValue({
        data: [],
        hasMore: false,
        nextCursor: null,
    }),
    fetchAllReasoningLogs: vi.fn().mockResolvedValue([]),
}));

describe('Reasoning Route Loader', () => {
    it('loads 12 events up front', async () => {
        const loader = Route.options.loader;
        if (typeof loader !== 'function') {
            throw new Error('Loader is not a function');
        }

        // Call the loader
        await (loader as () => Promise<unknown>)();

        // Assert it was called with limit 12
        expect(fetchReasoningLogs).toHaveBeenCalledWith(undefined, 12);
    });
});
